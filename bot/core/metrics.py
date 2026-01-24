from bot.utils.logger import logger

class Metrics:
    def __init__(self):
        self.attempted = 0
        self.submitted = 0
        self.skipped = 0
        self.failed = 0

    def increment(self, metric_name):
        if hasattr(self, metric_name):
            setattr(self, metric_name, getattr(self, metric_name) + 1)
        else:
            logger.warning(f"Unknown metric: {metric_name}", step="metrics", event="increment_error")

    def print_summary(self):
        logger.info("================ SESSION SUMMARY ================", step="metrics", event="summary_start")
        logger.info(f"Attempted:  {self.attempted}", step="metrics", event="summary_attempted")
        logger.info(f"Submitted:  {self.submitted}", step="metrics", event="summary_submitted")
        logger.info(f"Skipped:    {self.skipped}", step="metrics", event="summary_skipped")
        logger.info(f"Failed:     {self.failed}", step="metrics", event="summary_failed")
        logger.info("=================================================", step="metrics", event="summary_end")
