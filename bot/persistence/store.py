import duckdb
import pandas as pd
from datetime import datetime, timedelta
import logging
from pathlib import Path
import os
import re

log = logging.getLogger(__name__)

class Store:
    def __init__(self, db_file='data/bot_data.duckdb'):
        self.db_file = db_file
        # Ensure data directory exists
        Path(self.db_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database schema and migrate (one-time setup)
        self._init_db()
        self._migrate_legacy_data()
    
    def _get_connection(self):
        """Get a fresh database connection for each operation"""
        return duckdb.connect(self.db_file)

    def _init_db(self):
        """Initialize database schema (if not exists)"""
        con = self._get_connection()
        try:
            con.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    timestamp TIMESTAMP,
                    job_id VARCHAR,
                    job VARCHAR,
                    company VARCHAR,
                    attempted BOOLEAN,
                    result BOOLEAN,
                    candidate_id VARCHAR DEFAULT 'default',
                    proxy_used VARCHAR DEFAULT NULL
                )
            """)
            
            con.execute("""
                CREATE TABLE IF NOT EXISTS candidates (
                    candidate_id VARCHAR PRIMARY KEY,
                    name VARCHAR,
                    email VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            con.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id VARCHAR PRIMARY KEY,
                    candidate_id VARCHAR,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    applications_submitted INTEGER DEFAULT 0,
                    applications_failed INTEGER DEFAULT 0,
                    proxy_used VARCHAR,
                    system_id VARCHAR DEFAULT 'local'
                )
            """)
            
            con.execute("""
                CREATE TABLE IF NOT EXISTS qa (
                    question VARCHAR UNIQUE,
                    answer VARCHAR
                )
            """)
        finally:
            con.close()

    def _migrate_legacy_data(self):
        # Migrate CSVs if they exist and haven't been migrated
        # We check if tables are empty to decide (simplification, but safe for first run)
        
        con = self._get_connection()
        try:
            # QA Migration
            count_qa = con.execute("SELECT count(*) FROM qa").fetchone()[0]
            qa_csv = Path("data/qa.csv")
            if count_qa == 0 and qa_csv.exists():
                log.info("Migrating QA CSV to DuckDB...")
                try:
                    # DuckDB can read CSV directly. 
                    # Handling potential schema mismatch robustly:
                    con.execute(f"INSERT OR IGNORE INTO qa SELECT Question, Answer FROM read_csv_auto('{qa_csv}')")
                    qa_csv.rename("data/qa.csv.bak") # Rename after successful migration
                except Exception as e:
                    log.warning(f"QA migration failed: {e}")

            # Applications Migration
            count_apps = con.execute("SELECT count(*) FROM applications").fetchone()[0]
            out_csv = Path("data/out.csv")
            if count_apps == 0 and out_csv.exists():
                log.info("Migrating Applications CSV to DuckDB...")
                try:
                    # The CSV had no headers usually, or we need to be careful.
                    # Previous code read it with names=['timestamp', 'jobID', 'job', 'company', 'attempted', 'result']
                    # read_csv_auto might infer headers if they exist or columns.
                    # Let's specify columns to be safe if it was headerless. 
                    # Actually legacy writer didn't write headers if file existed, but might have created them?
                    # The old code: df.read_csv(header=None) implies no headers.
                    
                    con.execute(f"""
                        INSERT INTO applications (timestamp, job_id, job, company, attempted, result)
                        SELECT column0, column1, column2, column3, column4, column5 
                        FROM read_csv('{out_csv}', header=False, columns={{'column0': 'TIMESTAMP', 'column1': 'VARCHAR', 'column2': 'VARCHAR', 'column3': 'VARCHAR', 'column4': 'BOOLEAN', 'column5': 'BOOLEAN'}})
                    """)
                    out_csv.rename("data/out.csv.bak")
                except Exception as e:
                    log.warning(f"Applications migration failed: {e}")
        finally:
            con.close()



    def get_appliedIDs(self) -> list | None:
        con = self._get_connection()
        try:
            # Get successful applications from last 2 days? Or attempts? 
            # Original code: df = df[df['timestamp'] > (datetime.now() - timedelta(days=2))]
            # jobIDs = list(df.jobID)
            
            two_days_ago = datetime.now() - timedelta(days=2)
            results = con.execute("SELECT job_id FROM applications WHERE timestamp > ?", [two_days_ago]).fetchall()
            jobIDs = [row[0] for row in results]
            log.info(f"{len(jobIDs)} jobIDs found (last 48h)")
            return jobIDs
        except Exception as e:
            log.error(f"Failed to fetch jobIDs: {e}")
            return []
        finally:
            con.close()

    def write_to_file(self, button, jobID, browserTitle, result, candidate_id='default', proxy_used=None) -> None:
        def re_extract(text, pattern):
            target = re.search(pattern, text)
            if target:
                target = target.group(1)
            return target
            
        timestamp = datetime.now()
        attempted = True if button else False # Logic copied from old code: False if button==False else True
        
        job = re_extract(browserTitle.split(' | ')[0], r"\(?\d?\)?\s?(\w.*)")
        company = re_extract(browserTitle.split(' | ')[1], r"(\w.*)")
        
        con = self._get_connection()
        try:
            con.execute("INSERT INTO applications VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                             [timestamp, jobID, job, company, attempted, result, candidate_id, proxy_used])
        except Exception as e:
            log.error(f"Failed to write application to DB: {e}")
        finally:
            con.close()

    def save_answer(self, question, answer):
        con = self._get_connection()
        try:
            con.execute("INSERT OR REPLACE INTO qa VALUES (?, ?)", [question, answer])
            log.info(f"Saved answer for: '{question}'")
        except Exception as e:
             log.error(f"Failed to save QA: {e}")
        finally:
            con.close()

    def get_answer(self, question):
        con = self._get_connection()
        try:
            res = con.execute("SELECT answer FROM qa WHERE question = ?", [question]).fetchone()
            return res[0] if res else None
        except Exception as e:
            log.error(f"Failed to get answer: {e}")
            return None
        finally:
            con.close()
