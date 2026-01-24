import os
import logging
import platform
import random
from playwright.sync_api import sync_playwright, Browser as PlaywrightBrowser, BrowserContext, Page

log = logging.getLogger(__name__)

class Browser:
    def __init__(self, profile_path=None, proxy_config=None, headless=False):
        self.profile_path = profile_path
        self.proxy_config = proxy_config
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._setup_browser()

    def _setup_browser(self):
        """
        Initialize Playwright browser with stealth and anti-detection features
        """
        self.playwright = sync_playwright().start()
        
        # Browser launch arguments for stealth
        launch_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ]
        
        # Launch browser
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=launch_args,
            chromium_sandbox=False
        )
        
        # Context options for anti-detection
        context_options = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': self._get_random_user_agent(),
            'locale': 'en-US',
            'timezone_id': 'America/New_York',
            'permissions': ['geolocation', 'notifications'],
            'color_scheme': 'light',
            'extra_http_headers': {
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        }
        
        # Add proxy if configured
        if self.proxy_config:
            proxy_string = self.proxy_config.get_chrome_proxy_string()
            context_options['proxy'] = {
                'server': proxy_string
            }
            if self.proxy_config.username and self.proxy_config.password:
                context_options['proxy']['username'] = self.proxy_config.username
                context_options['proxy']['password'] = self.proxy_config.password
            log.info(f"Using proxy: {self.proxy_config.name}")
        
        # Use persistent context if profile path provided
        if self.profile_path:
            log.info(f"Using profile path: {self.profile_path}")
            self.context = self.browser.new_context(
                storage_state=self.profile_path if os.path.exists(self.profile_path) else None,
                **context_options
            )
        else:
            log.info("Using guest mode (no profile persistence)")
            self.context = self.browser.new_context(**context_options)
        
        # Add stealth scripts to bypass detection
        self.context.add_init_script("""
            // Overwrite the `plugins` property to use a custom getter
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Overwrite the `plugins` property to use a custom getter
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Overwrite the `languages` property to use a custom getter
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Overwrite chrome property
            window.chrome = {
                runtime: {}
            };
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        # Create initial page
        self.page = self.context.new_page()
        
        log.info("Playwright browser initialized with stealth features")
    
    def _get_random_user_agent(self):
        """
        Generate a random but realistic user agent
        """
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        ]
        return random.choice(user_agents)
    
    def get_page(self) -> Page:
        """
        Get the current page object
        """
        return self.page
    
    def close(self):
        """
        Clean up browser resources
        """
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        log.info("Browser closed")
