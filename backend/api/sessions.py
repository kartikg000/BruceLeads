
from fastapi import APIRouter
from pydantic import BaseModel

from scrapers.session_manager import (
    get_all_session_statuses,
    get_session_status,
    get_session_browser,
    login_to_platform,
    clear_session,
)

router = APIRouter()


@router.get("/status")
def all_platform_statuses():
    """Return login status for every supported platform."""
    statuses = get_all_session_statuses()
    # Also include browser type for logged-in platforms
    result = {}
    for platform, status in statuses.items():
        entry = {"status": status}
        if status == "logged_in":
            entry["browser"] = get_session_browser(platform)
        result[platform] = entry
    return result


class LoginRequest(BaseModel):
    platform: str
    browser: str = "chrome"


_VALID_PLATFORMS = {"linkedin", "twitter", "reddit", "instagram", "facebook"}
_VALID_BROWSERS = {"chrome", "msedge", "chromium"}


@router.post("/login")
def platform_login(request: LoginRequest):
    """
    Launch a visible browser for manual login.
    Blocks until the user finishes (up to 5 min timeout).
    """
    platform = request.platform.lower()
    browser = request.browser.lower()
    
    # Validate inputs to prevent injection
    if platform not in _VALID_PLATFORMS:
        return {"success": False, "message": f"Invalid platform: {request.platform}"}
    if browser not in _VALID_BROWSERS:
        return {"success": False, "message": f"Invalid browser: {request.browser}"}
    
    result = login_to_platform(platform, browser)
    return result


class LogoutRequest(BaseModel):
    platform: str


@router.post("/logout")
def platform_logout(request: LogoutRequest):
    """Remove saved browser profile for a platform."""
    success = clear_session(request.platform.lower())
    return {
        "success": success,
        "message": f"Logged out of {request.platform.title()}" if success else "Failed to clear session",
    }
