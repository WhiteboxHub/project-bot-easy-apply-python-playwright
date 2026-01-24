import time
import functools
from bot.utils.logger import logger
from bot.utils.exceptions import RetryException

def retry(max_attempts=3, delay=1, exceptions=(Exception,)):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            job_id = kwargs.get('job_id') 
            # If job_id isn't in kwargs, try to find it in args if possible, 
            # but usually we rely on kwargs or logging context inside the function.
            # However, the wrapper might not have access to 'self' context easily for logging 
            # if we don't pass it explicitly. 
            # For simplicity, we'll try to extract job_id from kwargs if present for logging.
            
            attempt = 1
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(f"Final failure in {func.__name__}: {e}", 
                                     job_id=job_id, step=func.__name__, event="retry_failed_final", exception=e)
                        raise RetryException(f"Failed {func.__name__} after {max_attempts} attempts") from e
                    
                    logger.warning(f"Attempt {attempt} failed in {func.__name__}: {e}", 
                                   job_id=job_id, step=func.__name__, event=f"retry_attempt_{attempt}", exception_type=type(e).__name__)
                    time.sleep(delay)
                    attempt += 1
        return wrapper
    return decorator
