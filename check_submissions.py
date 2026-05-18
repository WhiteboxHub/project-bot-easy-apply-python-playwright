# Quick check: How many applications submitted by each candidate
import duckdb
con = duckdb.connect('data/bot_data.duckdb', read_only=True)
result = con.execute("""
    SELECT 
        candidate_id as Name,
        SUM(CASE WHEN user_submitted THEN 1 ELSE 0 END) as Submitted
    FROM applications
    GROUP BY candidate_id
    ORDER BY Submitted DESC
""").fetchdf()
print(result.to_string(index=False)) 
