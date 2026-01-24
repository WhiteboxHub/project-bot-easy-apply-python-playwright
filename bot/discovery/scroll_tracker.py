from bot.utils.logger import logger

class ScrollTracker:
    def __init__(self, page, max_stuck_attempts=5):
        self.page = page
        self.max_stuck_attempts = max_stuck_attempts
        self.previous_height = 0
        self.same_height_count = 0
        self.processed_job_ids = set()
    
    def update_scroll(self, new_height):
        """
        Updates scroll state. Returns True if progress made (height changed), False if stuck.
        """
        if new_height == self.previous_height:
            self.same_height_count += 1
            logger.debug(f"Scroll stuck at {new_height} for {self.same_height_count} attempts", step="scroll", event="stuck")
            return False
        else:
            self.previous_height = new_height
            self.same_height_count = 0
            logger.debug(f"Scroll progressed to {new_height}", step="scroll", event="progress")
            return True

    def should_stop(self):
        """
        Checks if the scroll loop should be terminated due to being stuck.
        """
        if self.same_height_count >= self.max_stuck_attempts:
            logger.warning("Scroll tracker hard stop: stuck too long", step="scroll", event="hard_stop")
            return True
        return False

    def add_job(self, job_id):
        self.processed_job_ids.add(job_id)

    def is_processed(self, job_id):
        return job_id in self.processed_job_ids
