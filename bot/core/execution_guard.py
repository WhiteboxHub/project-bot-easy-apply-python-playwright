import time
from bot.utils.logger import logger

class ExecutionGuard:
    def __init__(self, max_apps=10, cooldown=90):
        self.max_apps = max_apps
        self.cooldown = cooldown
        self.applications_count = 0

    def can_apply(self):
        """
        Checks if the application limit has been reached.
        """
        if self.applications_count >= self.max_apps:
            logger.warning(f"Application limit reached ({self.max_apps}). Stopping.", step="execution_guard", event="limit_reached")
            return False
        return True

    def on_success(self):
        """
        Increments the application counter and sleeps for the cooldown period.
        """
        self.applications_count += 1
        logger.info(f"Application successful. Count: {self.applications_count}/{self.max_apps}", step="execution_guard", event="count_increment")
        
        if self.applications_count < self.max_apps:
            logger.info(f"Cooling down for {self.cooldown} seconds...", step="execution_guard", event="cooldown_start")
            time.sleep(self.cooldown)
