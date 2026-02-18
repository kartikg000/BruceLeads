"""
Session Manager for Social Media Platforms
Manages persistent Playwright browser profiles so users can log in once
and reuse their sessions for future searches (avoiding CAPTCHAs).
"""

import sys
import json
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config
from utils import get_python_executable


# Platform login URLs
PLATFORM_LOGIN_URLS = {
    "linkedin": "https://www.linkedin.com/login",
    "twitter": "https://x.com/i/flow/login",
    "reddit": "https://www.reddit.com/login/",
    "instagram": "https://www.instagram.com/accounts/login/",
    "facebook": "https://www.facebook.com/login/"
}

# URLs that indicate successful login (URL contains these after login)
PLATFORM_LOGGED_IN_INDICATORS = {
    "linkedin": ["linkedin.com/feed", "linkedin.com/mynetwork", "linkedin.com/in/", "linkedin.com/jobs"],
    "twitter": ["x.com/home", "x.com/notifications", "x.com/explore", "twitter.com/home"],
    "reddit": ["reddit.com/?feed=", "reddit.com/r/", "reddit.com/best", "reddit.com/hot"],
    "instagram": ["instagram.com/accounts/onetap", "instagram.com/explore", "instagram.com/direct"],
    "facebook": ["facebook.com/home.php", "facebook.com/?sk=", "facebook.com/profile.php"]
}


def get_profile_path(platform: str) -> Path:
    """Get the browser profile directory path for a platform."""
    return config.BROWSER_PROFILES_DIR / platform.lower()


def get_session_status(platform: str) -> str:
    """
    Check if a platform has a confirmed login session.
    
    Returns:
        'logged_in' if login_success.json marker exists, 'not_logged_in' otherwise
    """
    profile_path = get_profile_path(platform)
    marker_file = profile_path / "login_success.json"
    
    return "logged_in" if marker_file.exists() else "not_logged_in"


def get_session_browser(platform: str) -> str:
    """
    Get the browser type that was used to log in to a platform.
    
    Returns:
        Browser type string ('chrome', 'msedge', 'chromium') or 'chromium' as default
    """
    profile_path = get_profile_path(platform)
    marker_file = profile_path / "login_success.json"
    
    if marker_file.exists():
        try:
            data = json.loads(marker_file.read_text())
            return data.get("browser", "chromium")
        except Exception:
            pass
    
    return "chromium"


def get_all_session_statuses() -> dict:
    """Get login status for all supported platforms."""
    return {
        platform: get_session_status(platform)
        for platform in PLATFORM_LOGIN_URLS.keys()
    }


def clear_session(platform: str) -> bool:
    """
    Remove saved browser profile for a platform.
    
    Returns:
        True if successfully cleared
    """
    profile_path = get_profile_path(platform)
    
    if profile_path.exists():
        try:
            shutil.rmtree(profile_path)
            return True
        except Exception:
            return False
    return True


def login_to_platform(platform: str, browser_type: str = "chrome") -> dict:
    """
    Launch a visible browser for the user to log in to a platform.
    Uses a subprocess to run the login worker to avoid event loop conflicts.
    
    Args:
        platform: Platform name (linkedin, twitter, reddit, etc.)
    
    Returns:
        dict with 'success' and 'message' keys
    """
    platform = platform.lower()
    
    if platform not in PLATFORM_LOGIN_URLS:
        return {"success": False, "message": f"Unknown platform: {platform}"}
    
    login_url = PLATFORM_LOGIN_URLS[platform]
    profile_path = get_profile_path(platform)
    
    # Ensure profile directory exists
    profile_path.mkdir(parents=True, exist_ok=True)
    
    # Run login in subprocess (visible browser)
    worker_path = Path(__file__).parent / "login_worker.py"
    
    cmd = get_python_executable() + [
        str(worker_path),
        platform,
        login_url,
        str(profile_path),
        '--browser',
        browser_type
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout for login
            cwd=str(Path(__file__).parent.parent)
        )
        
        stdout_lines = result.stdout.strip().split('\n')
        if stdout_lines:
            try:
                data = json.loads(stdout_lines[-1])
                return data
            except json.JSONDecodeError:
                pass
        
        if result.returncode == 0:
            return {"success": True, "message": f"Logged in to {platform.title()}"}
        else:
            error_msg = result.stderr[:200] if result.stderr else "Unknown error"
            return {"success": False, "message": f"Login failed: {error_msg}"}
            
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "Login timed out (5 min limit)"}
    except Exception as e:
        return {"success": False, "message": str(e)}
