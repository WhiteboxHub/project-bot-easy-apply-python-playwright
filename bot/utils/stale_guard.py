from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import time
from bot.utils.logger import logger
from bot.utils.exceptions import NavigationException

def safe_action(action_func, locator_func, max_retries=3):
    """
    Executes action_func(element). 
    Playwright has built-in auto-waiting and element re-querying, 
    so stale element issues are much less common.
    This function is kept for compatibility but simplified.
    """
    attempt = 1
    while attempt <= max_retries:
        try:
            element = locator_func()
            return action_func(element)
        except PlaywrightTimeoutError:
            logger.warning(f"Timeout encountered, retrying...", step="safe_action", event="timeout_retry", attempt=attempt)
            time.sleep(1)
            attempt += 1
        except Exception as e:
            # Let other exceptions propagate
            raise e
            
    logger.error("Failed to complete action after retries", step="safe_action", event="action_abort")
    raise NavigationException("Failed to complete action after retries")
