# Playwright locator strings
# Playwright uses unified selector syntax - CSS, XPath, text, etc.

LOCATORS = {
    "next": {
        "primary": "button[aria-label='Continue to next step']",
        "fallback": "//button[contains(text(), 'Next') or contains(text(), 'Continue')]"
    },
    
    "review": {
        "primary": "button[aria-label='Review your application']",
        "fallback": "//button[contains(text(), 'Review')]"
    },
    
    "submit": {
        "primary": "button[aria-label='Submit application']",
        "fallback": "//button[contains(text(), 'Submit')]"
    },
    
    "error": {
        "primary": ".artdeco-inline-feedback__message",
        "fallback": ".artdeco-inline-feedback"
    },
    
    "upload_resume": {
        "primary": "input[type='file'][id*='resume']",
        "fallback": "input[type='file'][id*='upload-resume']"
    },
    
    "upload_cv": {
        "primary": "input[type='file'][id*='cover']",
        "fallback": "input[type='file'][id*='upload-cover-letter']"
    },
    
    "follow": {
        "primary": "label[for='follow-company-checkbox']",
        "fallback": "//label[contains(text(), 'Follow')]"
    },
    
    "upload": {
        "primary": "input[name='file']",
        "fallback": "input[type='file']"
    },
    
    "search": {
        "primary": ".jobs-search-results-list",
        "fallback": ".jobs-search-results__list"
    },
    
    "links": {
        "primary": "div[data-job-id]",
        "fallback": "div.job-card-container"
    },
    
    "fields": {
        "primary": ".jobs-easy-apply-form-section__grouping",
        "fallback": ".jobs-easy-apply-form-element"
    },
    
    "radio_select": {
        "primary": "input[type='radio']",
        "fallback": "//input[@type='radio']"
    },
    
    "multi_select": {
        "primary": "[id*='text-entity-list-form-component']",
        "fallback": "[id*='text-entity-list']"
    },
    
    "text_select": {
        "primary": ".artdeco-text-input--input",
        "fallback": "input[type='text']"
    },
    
    "2fa_oneClick": {
        "primary": "#reset-password-submit-button",
        "fallback": "button[type='submit']"
    },
    
    "easy_apply_button": {
        "primary": "button.jobs-apply-button",
        "fallback": "button[aria-label*='Easy Apply']"
    }
}


def get_locator(key: str, use_fallback: bool = False):
    """
    Get a locator by key, optionally returning the fallback.
    
    Args:
        key: The selector key
        use_fallback: If True, return fallback locator if available
    
    Returns:
        String selector for Playwright or the original value if not dict
    """
    locator = LOCATORS.get(key)
    
    if not locator:
        return None
    
    # If it's a dict with primary/fallback
    if isinstance(locator, dict):
        if use_fallback and "fallback" in locator:
            return locator["fallback"]
        return locator.get("primary", locator.get("fallback"))
    
    # Legacy format (direct string)
    return locator


def has_fallback(key: str) -> bool:
    """Check if a selector has a fallback defined"""
    locator = LOCATORS.get(key)
    return isinstance(locator, dict) and "fallback" in locator
