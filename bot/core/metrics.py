import duckdb
from bot.utils.logger import logger

class Metrics:
    def __init__(self, db_path='data/bot_data.duckdb'):
        self.attempted = 0
        self.submitted = 0
        self.skipped = 0
        self.failed = 0
        self.retry_count = 0
        self.step_failures = {} # Track failures by step name
        self.db_path = db_path

    def increment(self, metric_name):
        if hasattr(self, metric_name):
            setattr(self, metric_name, getattr(self, metric_name) + 1)
        else:
            logger.warning(f"Unknown metric: {metric_name}", step="metrics", event="increment_error")

    def log_step_failure(self, step_name, reason):
        """Track failure reason for a specific step"""
        if step_name not in self.step_failures:
            self.step_failures[step_name] = []
        self.step_failures[step_name].append(str(reason))
        self.failed += 1

    def print_summary(self):
        logger.info("=" * 20 + " SESSION SUMMARY " + "=" * 20, step="metrics")
        logger.info(f"🚀 Attempted:  {self.attempted}", step="metrics")
        logger.info(f"✅ Submitted:  {self.submitted}", step="metrics")
        logger.info(f"⏭️  Skipped:    {self.skipped}", step="metrics")
        logger.info(f"❌ Failed:     {self.failed}", step="metrics")
        logger.info(f"🔄 Retries:    {self.retry_count}", step="metrics")
        
        if self.step_failures:
            logger.info("-" * 15 + " FAILURE REASONS " + "-" * 15, step="metrics")
            for step, reasons in self.step_failures.items():
                unique_reasons = set(reasons)
                logger.info(f"📍 {step}: {len(reasons)} failures ({', '.join(list(unique_reasons)[:3])})", step="metrics")

        # Try to show Global Summary from DuckDB
        try:
            con = duckdb.connect(self.db_path, read_only=True)
            total = con.execute("SELECT count(*) FROM applications WHERE result = true").fetchone()[0]
            con.close()
            logger.info(f"📊 LIFETIME SUCCESSES (DuckDB): {total}", step="metrics")
        except:
            pass
            
        logger.info("=" * 57, step="metrics")
