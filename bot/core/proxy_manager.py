"""
Proxy rotation and management for distributed requests
"""
import random
import logging
from typing import List, Optional, Dict
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class ProxyConfig:
    """Configuration for a single proxy"""
    name: str
    server: str  # Format: http://host:port or socks5://host:port
    username: Optional[str] = None
    password: Optional[str] = None
    
    def get_chrome_proxy_string(self):
        """Get proxy string in Chrome format"""
        return self.server
    
    def to_playwright_dict(self):
        """Convert to Playwright proxy configuration"""
        config = {'server': self.server}
        if self.username and self.password:
            config['username'] = self.username
            config['password'] = self.password
        return config


class ProxyRotator:
    """
    Manages a pool of proxies and rotates between them
    """
    
    def __init__(self, proxies: List[ProxyConfig] = None, strategy='round_robin'):
        """
        Initialize proxy rotator
        
        Args:
            proxies: List of ProxyConfig objects
            strategy: Rotation strategy ('round_robin', 'random', 'weighted')
        """
        self.proxies = proxies or []
        self.strategy = strategy
        self.current_index = 0
        self.usage_count = {proxy.name: 0 for proxy in self.proxies}
        self.failure_count = {proxy.name: 0 for proxy in self.proxies}
        
        if self.proxies:
            log.info(f"Initialized ProxyRotator with {len(self.proxies)} proxies, strategy: {strategy}")
        else:
            log.warning("ProxyRotator initialized with no proxies")
    
    def add_proxy(self, proxy: ProxyConfig):
        """Add a proxy to the pool"""
        self.proxies.append(proxy)
        self.usage_count[proxy.name] = 0
        self.failure_count[proxy.name] = 0
        log.info(f"Added proxy: {proxy.name}")
    
    def remove_proxy(self, proxy_name: str):
        """Remove a proxy from the pool"""
        self.proxies = [p for p in self.proxies if p.name != proxy_name]
        self.usage_count.pop(proxy_name, None)
        self.failure_count.pop(proxy_name, None)
        log.info(f"Removed proxy: {proxy_name}")
    
    def get_next_proxy(self) -> Optional[ProxyConfig]:
        """
        Get the next proxy based on rotation strategy
        
        Returns:
            ProxyConfig or None if no proxies available
        """
        if not self.proxies:
            log.warning("No proxies available")
            return None
        
        if self.strategy == 'round_robin':
            proxy = self._round_robin()
        elif self.strategy == 'random':
            proxy = self._random()
        elif self.strategy == 'weighted':
            proxy = self._weighted()
        else:
            log.warning(f"Unknown strategy: {self.strategy}, using round_robin")
            proxy = self._round_robin()
        
        if proxy:
            self.usage_count[proxy.name] += 1
            log.debug(f"Selected proxy: {proxy.name} (used {self.usage_count[proxy.name]} times)")
        
        return proxy
    
    def _round_robin(self) -> ProxyConfig:
        """Round-robin selection"""
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy
    
    def _random(self) -> ProxyConfig:
        """Random selection"""
        return random.choice(self.proxies)
    
    def _weighted(self) -> ProxyConfig:
        """
        Weighted selection - prefer proxies with fewer failures
        """
        if not self.proxies:
            return None
        
        # Calculate weights (inverse of failure count)
        weights = []
        for proxy in self.proxies:
            failures = self.failure_count.get(proxy.name, 0)
            # Weight is inversely proportional to failures
            weight = 1.0 / (failures + 1)
            weights.append(weight)
        
        # Weighted random choice
        return random.choices(self.proxies, weights=weights, k=1)[0]
    
    def report_failure(self, proxy_name: str):
        """Report a proxy failure"""
        if proxy_name in self.failure_count:
            self.failure_count[proxy_name] += 1
            log.warning(f"Proxy failure reported: {proxy_name} (total failures: {self.failure_count[proxy_name]})")
    
    def report_success(self, proxy_name: str):
        """Report a proxy success (optional, for future enhancements)"""
        log.debug(f"Proxy success: {proxy_name}")
    
    def get_stats(self) -> Dict:
        """Get proxy usage statistics"""
        return {
            'total_proxies': len(self.proxies),
            'usage_count': dict(self.usage_count),
            'failure_count': dict(self.failure_count),
            'strategy': self.strategy
        }
    
    def print_stats(self):
        """Print proxy statistics"""
        log.info("=" * 60)
        log.info("PROXY STATISTICS")
        log.info("=" * 60)
        log.info(f"Total Proxies: {len(self.proxies)}")
        log.info(f"Strategy: {self.strategy}")
        log.info("-" * 60)
        
        for proxy in self.proxies:
            usage = self.usage_count.get(proxy.name, 0)
            failures = self.failure_count.get(proxy.name, 0)
            success_rate = ((usage - failures) / usage * 100) if usage > 0 else 0
            log.info(f"  {proxy.name:20s} | Used: {usage:3d} | Failed: {failures:3d} | Success: {success_rate:5.1f}%")
        
        log.info("=" * 60)


def load_proxies_from_config(config: Dict) -> List[ProxyConfig]:
    """
    Load proxies from configuration dictionary
    
    Args:
        config: Configuration dict with 'proxies' key
        
    Returns:
        List of ProxyConfig objects
    """
    proxies = []
    proxy_list = config.get('proxies', [])
    
    for proxy_data in proxy_list:
        proxy = ProxyConfig(
            name=proxy_data.get('name', f'proxy_{len(proxies)}'),
            server=proxy_data['server'],
            username=proxy_data.get('username'),
            password=proxy_data.get('password')
        )
        proxies.append(proxy)
        log.info(f"Loaded proxy: {proxy.name} -> {proxy.server}")
    
    return proxies
