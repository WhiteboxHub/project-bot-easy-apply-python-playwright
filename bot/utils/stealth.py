"""
Advanced anti-detection and stealth techniques for Playwright
Bypasses common bot detection methods used by LinkedIn and similar platforms
"""

import random
import time

class StealthConfig:
    """
    Configuration for advanced stealth features
    """
    
    # Realistic user agents (recent Chrome versions)
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    ]
    
    # Viewport sizes (common resolutions)
    VIEWPORTS = [
        {'width': 1920, 'height': 1080},
        {'width': 1366, 'height': 768},
        {'width': 1536, 'height': 864},
        {'width': 1440, 'height': 900},
        {'width': 2560, 'height': 1440},
    ]
    
    # Timezone IDs
    TIMEZONES = [
        'America/New_York',
        'America/Chicago',
        'America/Los_Angeles',
        'America/Denver',
        'Europe/London',
    ]
    
    # Locales
    LOCALES = [
        'en-US',
        'en-GB',
        'en-CA',
    ]
    
    @staticmethod
    def get_random_user_agent():
        return random.choice(StealthConfig.USER_AGENTS)
    
    @staticmethod
    def get_random_viewport():
        return random.choice(StealthConfig.VIEWPORTS)
    
    @staticmethod
    def get_random_timezone():
        return random.choice(StealthConfig.TIMEZONES)
    
    @staticmethod
    def get_random_locale():
        return random.choice(StealthConfig.LOCALES)


# Advanced stealth JavaScript to inject into pages
STEALTH_JS = """
// ==== NAVIGATOR OVERRIDES ====

// Remove webdriver property
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true
});

// Override plugins to appear realistic
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        return [
            {
                0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                description: "Portable Document Format",
                filename: "internal-pdf-viewer",
                length: 1,
                name: "Chrome PDF Plugin"
            },
            {
                0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
                description: "Portable Document Format", 
                filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                length: 1,
                name: "Chrome PDF Viewer"
            },
            {
                0: {type: "application/x-nacl", suffixes: "", description: "Native Client Executable"},
                1: {type: "application/x-pnacl", suffixes: "", description: "Portable Native Client Executable"},
                description: "Native Client",
                filename: "internal-nacl-plugin",
                length: 2,
                name: "Native Client"
            }
        ];
    },
    configurable: true
});

// Override languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
    configurable: true
});

// Override platform
Object.defineProperty(navigator, 'platform', {
    get: () => 'Win32',
    configurable: true
});

// Override hardwareConcurrency to realistic value
Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => 8,
    configurable: true
});

// Override deviceMemory
Object.defineProperty(navigator, 'deviceMemory', {
    get: () => 8,
    configurable: true
});

// ==== CHROME OBJECT ====

// Add chrome object (missing in automation)
if (!window.chrome) {
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {}
    };
}

// ==== PERMISSIONS ====

// Mock permissions API
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);

// ==== WEBGL FINGERPRINT RANDOMIZATION ====

const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    // Randomize UNMASKED_VENDOR_WEBGL
    if (parameter === 37445) {
        return 'Intel Inc.';
    }
    // Randomize UNMASKED_RENDERER_WEBGL  
    if (parameter === 37446) {
        return 'Intel Iris OpenGL Engine';
    }
    return getParameter.apply(this, arguments);
};

// ==== CANVAS FINGERPRINT RANDOMIZATION ====

const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function() {
    // Add slight noise to canvas to prevent fingerprinting
    const context = this.getContext('2d');
    const imageData = context.getImageData(0, 0, this.width, this.height);
    for (let i = 0; i < imageData.data.length; i += 4) {
        imageData.data[i] += Math.floor(Math.random() * 3) - 1;
        imageData.data[i + 1] += Math.floor(Math.random() * 3) - 1;
        imageData.data[i + 2] += Math.floor(Math.random() * 3) - 1;
    }
    context.putImageData(imageData, 0, 0);
    return originalToDataURL.apply(this, arguments);
};

// ==== AUDIO CONTEXT FINGERPRINT ====

const AudioContext = window.AudioContext || window.webkitAudioContext;
if (AudioContext) {
    const originalCreateOscillator = AudioContext.prototype.createOscillator;
    AudioContext.prototype.createOscillator = function() {
        const oscillator = originalCreateOscillator.apply(this, arguments);
        const originalStart = oscillator.start;
        oscillator.start = function() {
            // Add slight randomization
            arguments[0] = arguments[0] + Math.random() * 0.0001;
            return originalStart.apply(this, arguments);
        };
        return oscillator;
    };
}

// ==== SCREEN PROPERTIES ====

// Make screen properties consistent with viewport
Object.defineProperty(screen, 'availWidth', {
    get: () => window.innerWidth,
    configurable: true
});

Object.defineProperty(screen, 'availHeight', {
    get: () => window.innerHeight,
    configurable: true
});

// ==== BATTERY API ====

// Remove battery API (often used for fingerprinting)
if (navigator.getBattery) {
    navigator.getBattery = undefined;
}

// ==== MEDIA DEVICES ====

// Mock realistic media devices
if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
    const originalEnumerateDevices = navigator.mediaDevices.enumerateDevices;
    navigator.mediaDevices.enumerateDevices = async function() {
        const devices = await originalEnumerateDevices.apply(this, arguments);
        return devices.map((device, index) => ({
            ...device,
            deviceId: `device-${index}-${Math.random().toString(36).substr(2, 9)}`,
            groupId: `group-${Math.random().toString(36).substr(2, 9)}`
        }));
    };
}

// ==== IFRAME DETECTION ====

// Hide iframe detection
Object.defineProperty(window, 'top', {
    get: () => window,
    configurable: true
});

Object.defineProperty(window, 'frameElement', {
    get: () => null,
    configurable: true
});

// ==== MOUSE MOVEMENT TRACKING ====

// Add realistic mouse movement variance
let lastMouseMove = Date.now();
document.addEventListener('mousemove', () => {
    lastMouseMove = Date.now();
}, true);

// ==== TIMING ATTACKS PREVENTION ====

// Add slight randomization to performance.now()
const originalPerformanceNow = performance.now;
const randomOffset = Math.random() * 10;
performance.now = function() {
    return originalPerformanceNow.apply(this, arguments) + randomOffset;
};

// ==== CONSOLE DETECTION ====

// Prevent console detection
const originalLog = console.log;
console.log = function() {
    return originalLog.apply(this, arguments);
};

console.debug('Stealth mode activated');
"""


def get_stealth_js():
    """
    Returns the stealth JavaScript to inject
    """
    return STEALTH_JS


def add_random_delays():
    """
    Add random human-like delays
    """
    time.sleep(random.uniform(0.5, 2.0))


def get_realistic_headers():
    """
    Returns realistic HTTP headers
    """
    return {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'DNT': '1',
        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
    }
