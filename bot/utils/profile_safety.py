"""
Profile safety utilities to prevent Chrome profile conflicts
"""
import psutil
import os
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def is_chrome_running_with_profile(profile_path):
    """
    Check if Chrome is already running with the specified profile
    
    Args:
        profile_path: Path to Chrome user data directory
        
    Returns:
        bool: True if Chrome is using this profile, False otherwise
    """
    if not profile_path or not os.path.exists(profile_path):
        return False
    
    # Normalize path for comparison
    profile_path = os.path.abspath(profile_path)
    
    try:
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                # Check if process is Chrome/Chromium
                if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline:
                        # Check if this Chrome instance is using our profile
                        cmdline_str = ' '.join(cmdline)
                        if profile_path in cmdline_str or profile_path.replace('\\', '/') in cmdline_str:
                            log.warning(f"Chrome is already running with profile: {profile_path}")
                            log.warning(f"Process: {proc.info['name']} (PID: {proc.pid})")
                            return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception as e:
        log.error(f"Error checking Chrome processes: {e}")
        return False
    
    return False


def check_profile_lock_file(profile_path):
    """
    Check if profile lock file exists (indicates profile is in use)
    
    Args:
        profile_path: Path to Chrome user data directory
        
    Returns:
        bool: True if lock file exists, False otherwise
    """
    if not profile_path or not os.path.exists(profile_path):
        return False
    
    lock_files = [
        'SingletonLock',
        'lockfile',
        'Singleton',
    ]
    
    for lock_file in lock_files:
        lock_path = os.path.join(profile_path, lock_file)
        if os.path.exists(lock_path):
            log.warning(f"Profile lock file found: {lock_path}")
            return True
    
    return False


def validate_profile_safety(profile_path):
    """
    Comprehensive profile safety validation
    
    Args:
        profile_path: Path to Chrome user data directory
        
    Returns:
        tuple: (is_safe: bool, reason: str)
    """
    if not profile_path:
        return True, "No profile specified (using guest mode)"
    
    if not os.path.exists(profile_path):
        return True, f"Profile path does not exist yet: {profile_path}"
    
    # Check if Chrome is running with this profile
    if is_chrome_running_with_profile(profile_path):
        return False, "Chrome is already running with this profile. Please close Chrome and try again."
    
    # Check for lock files
    if check_profile_lock_file(profile_path):
        return False, "Profile lock file detected. Another Chrome instance may be using this profile."
    
    return True, "Profile is safe to use"


def get_chrome_processes():
    """
    Get list of all running Chrome processes
    
    Returns:
        list: List of Chrome process info dicts
    """
    chrome_processes = []
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                    chrome_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': ' '.join(proc.info.get('cmdline', []))
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        log.error(f"Error getting Chrome processes: {e}")
    
    return chrome_processes
