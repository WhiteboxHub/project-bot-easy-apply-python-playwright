"""
Validation script for LinkedIn EasyApply Bot (Playwright Version)
Tests all components and validates the setup
"""

import sys
import os

# Add bot directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported"""
    print("=" * 60)
    print("TESTING IMPORTS")
    print("=" * 60)
    
    try:
        from bot.core.browser import Browser
        print("✅ bot.core.browser")
    except Exception as e:
        print(f"❌ bot.core.browser: {e}")
        return False
    
    try:
        from bot.core.session import Session
        print("✅ bot.core.session")
    except Exception as e:
        print(f"❌ bot.core.session: {e}")
        return False
    
    try:
        from bot.application.workflow import Workflow
        print("✅ bot.application.workflow")
    except Exception as e:
        print(f"❌ bot.application.workflow: {e}")
        return False
    
    try:
        from bot.application.form_filler import FormFiller
        print("✅ bot.application.form_filler")
    except Exception as e:
        print(f"❌ bot.application.form_filler: {e}")
        return False
    
    try:
        from bot.discovery.search import Search
        print("✅ bot.discovery.search")
    except Exception as e:
        print(f"❌ bot.discovery.search: {e}")
        return False
    
    try:
        from bot.persistence.store import Store
        print("✅ bot.persistence.store")
    except Exception as e:
        print(f"❌ bot.persistence.store: {e}")
        return False
    
    try:
        from bot.utils.selectors import LOCATORS, get_locator
        print("✅ bot.utils.selectors")
    except Exception as e:
        print(f"❌ bot.utils.selectors: {e}")
        return False
    
    try:
        from bot.utils.human_interaction import HumanInteraction
        print("✅ bot.utils.human_interaction")
    except Exception as e:
        print(f"❌ bot.utils.human_interaction: {e}")
        return False
    
    try:
        from bot.utils.logger import logger
        print("✅ bot.utils.logger")
    except Exception as e:
        print(f"❌ bot.utils.logger: {e}")
        return False
    
    try:
        from bot.core.execution_guard import ExecutionGuard
        print("✅ bot.core.execution_guard")
    except Exception as e:
        print(f"❌ bot.core.execution_guard: {e}")
        return False
    
    try:
        from bot.core.dry_run import DryRun
        print("✅ bot.core.dry_run")
    except Exception as e:
        print(f"❌ bot.core.dry_run: {e}")
        return False
    
    try:
        from bot.core.metrics import Metrics
        print("✅ bot.core.metrics")
    except Exception as e:
        print(f"❌ bot.core.metrics: {e}")
        return False
    
    print("\n✅ All imports successful!\n")
    return True


def test_selectors():
    """Test selector definitions"""
    print("=" * 60)
    print("TESTING SELECTORS")
    print("=" * 60)
    
    from bot.utils.selectors import LOCATORS, get_locator
    
    critical_selectors = [
        'easy_apply_button',
        'next',
        'submit',
        'error',
        'upload_resume',
        'search',
        'links',
    ]
    
    all_ok = True
    for selector_key in critical_selectors:
        selector = get_locator(selector_key)
        if selector:
            print(f"✅ {selector_key:20s} -> {selector}")
        else:
            print(f"❌ {selector_key:20s} -> NOT DEFINED")
            all_ok = False
    
    if all_ok:
        print("\n✅ All critical selectors defined!\n")
    else:
        print("\n❌ Some selectors are missing!\n")
    
    return all_ok


def test_dependencies():
    """Test that all required dependencies are installed"""
    print("=" * 60)
    print("TESTING DEPENDENCIES")
    print("=" * 60)
    
    dependencies = [
        ('playwright', 'Playwright'),
        ('dotenv', 'python-dotenv'),
        ('duckdb', 'DuckDB'),
        ('yaml', 'PyYAML'),
        ('requests', 'Requests'),
        ('bs4', 'BeautifulSoup4'),
        ('lxml', 'lxml'),
        ('psutil', 'psutil'),
    ]
    
    all_ok = True
    for module_name, package_name in dependencies:
        try:
            __import__(module_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name} - NOT INSTALLED")
            all_ok = False
    
    if all_ok:
        print("\n✅ All dependencies installed!\n")
    else:
        print("\n❌ Some dependencies are missing! Run: pip install -r requirements.txt\n")
    
    return all_ok


def test_config():
    """Test configuration file"""
    print("=" * 60)
    print("TESTING CONFIGURATION")
    print("=" * 60)
    
    import yaml
    
    try:
        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        
        # Check required fields
        if 'positions' in config and len(config['positions']) > 0:
            print(f"✅ Positions configured: {len(config['positions'])} positions")
        else:
            print("❌ No positions configured")
            return False
        
        if 'locations' in config and len(config['locations']) > 0:
            print(f"✅ Locations configured: {len(config['locations'])} locations")
        else:
            print("❌ No locations configured")
            return False
        
        if 'execution' in config:
            print(f"✅ Execution settings configured")
            print(f"   - Max applications: {config['execution'].get('max_applications_per_run', 'N/A')}")
            print(f"   - Cooldown: {config['execution'].get('cooldown_seconds', 'N/A')}s")
            print(f"   - Dry run: {config['execution'].get('dry_run', 'N/A')}")
        else:
            print("⚠️  No execution settings (will use defaults)")
        
        print("\n✅ Configuration file valid!\n")
        return True
        
    except FileNotFoundError:
        print("❌ config.yaml not found")
        return False
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return False


def test_env():
    """Test environment variables"""
    print("=" * 60)
    print("TESTING ENVIRONMENT")
    print("=" * 60)
    
    from dotenv import load_dotenv
    load_dotenv()
    
    username = os.getenv('LINKEDIN_USERNAME')
    password = os.getenv('LINKEDIN_PASSWORD')
    phone = os.getenv('PHONE_NUMBER')
    
    if username and username != 'your_email@example.com':
        print(f"✅ LINKEDIN_USERNAME configured")
    else:
        print("⚠️  LINKEDIN_USERNAME not configured (using config.yaml)")
    
    if password and password != 'your_password':
        print(f"✅ LINKEDIN_PASSWORD configured")
    else:
        print("⚠️  LINKEDIN_PASSWORD not configured (using config.yaml)")
    
    if phone and phone != 'your_phone_number':
        print(f"✅ PHONE_NUMBER configured")
    else:
        print("⚠️  PHONE_NUMBER not configured (using config.yaml)")
    
    print("\n✅ Environment check complete!\n")
    return True


def test_browser_init():
    """Test browser initialization"""
    print("=" * 60)
    print("TESTING BROWSER INITIALIZATION")
    print("=" * 60)
    
    try:
        from bot.core.browser import Browser
        
        print("Initializing browser...")
        browser = Browser(headless=True)
        print("✅ Browser initialized successfully")
        
        page = browser.get_page()
        print("✅ Page object retrieved")
        
        # Test navigation
        print("Testing navigation to example.com...")
        page.goto("https://example.com", wait_until="domcontentloaded")
        print("✅ Navigation successful")
        
        # Clean up
        browser.close()
        print("✅ Browser closed successfully")
        
        print("\n✅ Browser test passed!\n")
        return True
        
    except Exception as e:
        print(f"❌ Browser test failed: {e}")
        print("\nMake sure Playwright browsers are installed:")
        print("  playwright install chromium")
        return False


def test_store():
    """Test database store"""
    print("=" * 60)
    print("TESTING DATABASE STORE")
    print("=" * 60)
    
    try:
        from bot.persistence.store import Store
        
        store = Store()
        print("✅ Store initialized")
        
        # Test saving answer
        store.save_answer("test_question", "test_answer")
        print("✅ Answer saved")
        
        # Test retrieving answer
        answer = store.get_answer("test_question")
        if answer == "test_answer":
            print("✅ Answer retrieved correctly")
        else:
            print(f"❌ Answer mismatch: expected 'test_answer', got '{answer}'")
            return False
        
        print("\n✅ Store test passed!\n")
        return True
        
    except Exception as e:
        print(f"❌ Store test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("LINKEDIN EASYAPPLY BOT - VALIDATION SCRIPT")
    print("Playwright Version")
    print("=" * 60 + "\n")
    
    results = {
        "Dependencies": test_dependencies(),
        "Imports": test_imports(),
        "Selectors": test_selectors(),
        "Configuration": test_config(),
        "Environment": test_env(),
        "Store": test_store(),
        "Browser": test_browser_init(),
    }
    
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20s} {status}")
    
    all_passed = all(results.values())
    
    print("=" * 60)
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Bot is ready to use.")
        print("\nTo run the bot:")
        print("  python main.py")
        print("\nMake sure to:")
        print("  1. Configure your credentials in .env")
        print("  2. Set dry_run: false in config.yaml when ready to apply")
        print("  3. Review the selectors if LinkedIn UI has changed")
    else:
        print("\n⚠️  SOME TESTS FAILED! Please fix the issues above.")
        print("\nCommon fixes:")
        print("  - Install dependencies: pip install -r requirements.txt")
        print("  - Install Playwright browsers: playwright install chromium")
        print("  - Configure credentials in .env file")
        print("  - Configure job search in config.yaml")
    
    print("\n")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
