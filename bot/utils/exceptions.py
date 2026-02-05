class NavigationException(Exception):
    """Raised when navigation fails after retries."""
    pass

class RetryException(Exception):
    """Raised when a retried action fails ultimately."""
    pass
