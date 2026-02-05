"""
Advanced Proxy management with rotation, health checks, and provider support
"""
import random
import logging
import time
import requests
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

@dataclass
class ProxyConfig:
    """Configuration for a single proxy element from a pool"""
    name: str
    server: str  # Format: host:port
    username: Optional[str] = None
    password: Optional[str] = None
    type: str = "residential"
    country: str = "US"
    enabled: bool = True
    
    @property
    def playwright_server(self):
        """Format server for Playwright (ensuring http prefix)"""
        if not self.server.startswith(('http://', 'https://', 'socks5://')):
            return f"http://{self.server}"
        return self.server

    def to_playwright_dict(self):
        """Convert to Playwright proxy configuration format"""
        config = {'server': self.playwright_server}
        if self.username and self.password:
            config['username'] = self.username
            config['password'] = self.password
        return config

    def check_health(self, test_url: str = "https://lumtest.com/myip.json", timeout: int = 10) -> bool:
        """Verify proxy is working and returns an IP"""
        proxies = {
            "http": f"http://{self.username}:{self.password}@{self.server}" if self.username else f"http://{self.server}",
            "https": f"http://{self.username}:{self.password}@{self.server}" if self.username else f"http://{self.server}"
        }
        try:
            response = requests.get(test_url, proxies=proxies, timeout=timeout)
            if response.status_code == 200:
                log.info(f"✅ Proxy {self.name} is healthy. IP Info: {response.text.strip()[:50]}...")
                return True
            return False
        except Exception as e:
            log.warning(f"❌ Proxy {self.name} health check failed: {e}")
            return False

class ProxyRotator:
    """
    Manages pools and executes rotation strategies
    """
    def __init__(self, config_dict: Dict[str, Any]):
        self.config = config_dict
        self.enabled = config_dict.get('enabled', False)
        self.strategy = config_dict.get('rotation', {}).get('strategy', 'per_session')
        self.pool: List[ProxyConfig] = []
        self._load_pools()
        
        self.current_index = 0
        self.failure_counts = {}
        
    def _load_pools(self):
        """Convert pool definitions into ProxyConfig objects"""
        pools_data = self.config.get('pools', [])
        for p in pools_data:
            if not p.get('enabled', True):
                continue
                
            # Construct server string
            host = p.get('host')
            port = p.get('port')
            if not host or not port: continue
            
            # Resolve credentials (supporting env var placeholders or direct values)
            username = p.get('username', '')
            password = p.get('password', '')
            
            # Basic placeholder resolution (real env vars should be handled in loader)
            import os
            if "{your_password}" in password or not password:
                # Check for provider specific env vars
                env_key = f"PROXY_{self.config.get('provider', 'custom').upper()}_PASSWORD"
                password = os.getenv(env_key, password)

            self.pool.append(ProxyConfig(
                name=p.get('name', 'pool_proxy'),
                server=f"{host}:{port}",
                username=username,
                password=password,
                type=p.get('type', 'residential'),
                country=p.get('country', 'US')
            ))

    def get_proxy(self, candidate_id: Optional[str] = None) -> Optional[ProxyConfig]:
        """Get proxy based on strategy"""
        if not self.enabled or not self.pool:
            return None

        # Strategy: per_candidate
        if self.strategy == 'per_candidate' and candidate_id:
            # Use deterministic selection based on ID hash
            idx = sum(ord(c) for c in candidate_id) % len(self.pool)
            proxy = self.pool[idx]
        
        # Strategy: random or round_robin (shuffled)
        else:
            proxy = random.choice(self.pool)

        # Health Check
        health_cfg = self.config.get('health_check', {})
        if health_cfg.get('enabled', True):
            if not proxy.check_health(
                test_url=health_cfg.get('url', "https://lumtest.com/myip.json"),
                timeout=health_cfg.get('timeout', 10)
            ):
                # Retry once with another proxy if this one is dead
                log.warning("Selected proxy failed health check, trying one fallback...")
                proxy = random.choice([p for p in self.pool if p != proxy])
                if not proxy.check_health(): return None
        
        return proxy

def load_advanced_proxy_config(yaml_data: Dict) -> Optional[ProxyRotator]:
    """Helper to initialize ProxyRotator from YAML data"""
    proxy_section = yaml_data.get('proxy')
    if not proxy_section or not proxy_section.get('enabled', False):
        return None
    return ProxyRotator(proxy_section)
