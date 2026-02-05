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
            # Explicit visibility check before action
            if hasattr(element, "wait_for"):
                element.wait_for(state="visible", timeout=5000)
            return action_func(element)
        except PlaywrightTimeoutError:
            logger.warning(f"Timeout (attempt {attempt}/{max_retries}), retrying...", step="safe_action")
            time.sleep(attempt * 1) # Exponential backoff
            attempt += 1
        except Exception as e:
            # Handle potential stale element by waiting and retrying once
            if "stale" in str(e).lower() or "detached" in str(e).lower() or "hidden" in str(e).lower():
                logger.warning(f"DOM changed (attempt {attempt}), re-locating...", step="safe_action")
                time.sleep(0.5)
                attempt += 1
                continue
            logger.warning(f"Action failed: {e}", step="safe_action_error")
            raise e
            
    logger.error("Failed to complete action after retries", step="safe_action", event="action_abort")
    raise NavigationException("Failed to complete action after retries")
