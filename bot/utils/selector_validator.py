"""
Selector validation utilities to ensure critical selectors exist
"""
import logging
from bot.utils.selectors import LOCATORS, get_locator

log = logging.getLogger(__name__)


# Critical selectors that MUST exist for bot to function
CRITICAL_SELECTORS = [
    'easy_apply_button',
    'next',
    'submit',
    'error',
    'upload_resume',
]


def validate_selectors_on_page(page, test_url="https://www.linkedin.com/jobs/search/?f_LF=f_AL"):
    """
    Validate that critical selectors exist on a test page
    
    Args:
        page: Playwright page object
        test_url: URL to test selectors on (default: LinkedIn jobs search)
        
    Returns:
        tuple: (all_valid: bool, results: dict)
    """
    log.info(f"Validating selectors on: {test_url}")
    
    try:
        # Navigate to test page
        page.goto(test_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)  # Wait for dynamic content
    except Exception as e:
        log.error(f"Failed to navigate to test page: {e}")
        return False, {"error": f"Navigation failed: {e}"}
    
    results = {}
    all_valid = True
    
    # Test each critical selector
    for selector_key in CRITICAL_SELECTORS:
        selector = get_locator(selector_key)
        if not selector:
            results[selector_key] = {
                'status': 'MISSING',
                'selector': None,
                'found': False
            }
            all_valid = False
            log.error(f"❌ Selector '{selector_key}' not defined in LOCATORS")
            continue
        
        try:
            # Check if selector exists on page
            count = page.locator(selector).count()
            found = count > 0
            
            results[selector_key] = {
                'status': 'OK' if found else 'NOT_FOUND',
                'selector': selector,
                'found': found,
                'count': count
            }
            
            if found:
                log.info(f"✅ Selector '{selector_key}' found ({count} elements)")
            else:
                log.warning(f"⚠️ Selector '{selector_key}' not found on test page (may appear later)")
                # Note: Some selectors only appear in specific contexts (e.g., submit button in modal)
                # So we don't fail validation for these
        except Exception as e:
            results[selector_key] = {
                'status': 'ERROR',
                'selector': selector,
                'found': False,
                'error': str(e)
            }
            log.error(f"❌ Error testing selector '{selector_key}': {e}")
            all_valid = False
    
    return all_valid, results


def validate_selector_definitions():
    """
    Validate that all critical selectors are defined in LOCATORS
    
    Returns:
        tuple: (all_defined: bool, missing: list)
    """
    missing = []
    
    for selector_key in CRITICAL_SELECTORS:
        selector = get_locator(selector_key)
        if not selector:
            missing.append(selector_key)
            log.error(f"❌ Critical selector '{selector_key}' is not defined")
    
    if missing:
        log.error(f"Missing {len(missing)} critical selectors: {missing}")
        return False, missing
    
    log.info(f"✅ All {len(CRITICAL_SELECTORS)} critical selectors are defined")
    return True, []


def print_validation_report(results):
    """
    Print a formatted validation report
    
    Args:
        results: Validation results dict
    """
    log.info("=" * 60)
    log.info("SELECTOR VALIDATION REPORT")
    log.info("=" * 60)
    
    for selector_key, result in results.items():
        status = result['status']
        selector = result.get('selector', 'N/A')
        
        if status == 'OK':
            log.info(f"✅ {selector_key:20s} | {selector}")
        elif status == 'NOT_FOUND':
            log.warning(f"⚠️  {selector_key:20s} | {selector} (not on test page)")
        elif status == 'MISSING':
            log.error(f"❌ {selector_key:20s} | NOT DEFINED")
        elif status == 'ERROR':
            log.error(f"❌ {selector_key:20s} | ERROR: {result.get('error', 'Unknown')}")
    
    log.info("=" * 60)
