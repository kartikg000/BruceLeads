"""
BruceLeads Configuration Module

Hybrid configuration system:
 1. Environment variables / .env file   (read at startup)
 2. data/settings.json                  (user-editable at runtime via UI)

Runtime settings override env-var defaults. All user-provided secrets
(API keys, SMTP credentials) are stored in settings.json so the app
works out-of-the-box without a .env file — ideal for EXE distribution.
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# =============================================================================
# App Version  (bump this on each release)
# =============================================================================
APP_VERSION = "2.3.1"
GITHUB_REPO = "kartikg000/BruceLeads"

# =============================================================================
# Paths  (never change at runtime)
# =============================================================================
if getattr(sys, 'frozen', False):
    # Frozen EXE: use the directory containing the EXE for mutable data,
    # and _MEIPASS (internal) for bundled source modules.
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

# Load .env only from BASE_DIR (not arbitrary CWD)
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
CREDENTIALS_DIR = BASE_DIR / "credentials"
BROWSER_PROFILES_DIR = DATA_DIR / "browser_profiles"
SETTINGS_FILE = DATA_DIR / "settings.json"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
CREDENTIALS_DIR.mkdir(exist_ok=True)
BROWSER_PROFILES_DIR.mkdir(exist_ok=True)


# =============================================================================
# Runtime Settings Store
# =============================================================================
_settings_cache: dict = {}


def _load_settings() -> dict:
    """Load settings.json into memory."""
    global _settings_cache
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                _settings_cache = json.load(f)
        except (json.JSONDecodeError, OSError):
            _settings_cache = {}
    else:
        _settings_cache = {}
    return _settings_cache


def _save_settings(data: dict):
    """Persist settings to disk and refresh cache."""
    global _settings_cache
    _settings_cache = data
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    # Restrict file permissions (owner-only on POSIX, no-op on Windows)
    try:
        import stat
        SETTINGS_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except (OSError, AttributeError):
        pass


def get_setting(key: str, default=None):
    """Read a single setting (settings.json takes priority over env)."""
    if not _settings_cache:
        _load_settings()
    return _settings_cache.get(key, default)


def update_settings(updates: dict):
    """Merge *updates* into settings.json and persist."""
    if not _settings_cache:
        _load_settings()
    _settings_cache.update(updates)
    _save_settings(_settings_cache)


def get_all_settings() -> dict:
    """Return full settings dict (shallow copy)."""
    if not _settings_cache:
        _load_settings()
    return dict(_settings_cache)


# Load settings at module import time
_load_settings()


# =============================================================================
# Helper: resolve from settings.json → env var → default
# =============================================================================
def _resolve(settings_key: str, env_key: str, default=""):
    """Return value from settings first, then env, then default."""
    val = get_setting(settings_key)
    if val not in (None, ""):
        return val
    return os.getenv(env_key, default)


# =============================================================================
# API Keys  (runtime-updatable)
# =============================================================================

# Module-level accessors that always reflect the latest runtime value
class _Cfg:
    """Thin descriptor so other modules can do ``import config; config.GEMINI_API_KEY``."""
    @staticmethod
    def gemini_api_key():
        return _resolve("gemini_api_key", "GEMINI_API_KEY", "")

    @staticmethod
    def gmail_user():
        return _resolve("gmail_user", "GMAIL_USER", "")

    @staticmethod
    def gmail_app_password():
        return _resolve("gmail_app_password", "GMAIL_APP_PASSWORD", "")

    @staticmethod
    def gmail_client_id():
        return _resolve("gmail_client_id", "GMAIL_CLIENT_ID", "")

    @staticmethod
    def gmail_client_secret():
        return _resolve("gmail_client_secret", "GMAIL_CLIENT_SECRET", "")

    @staticmethod
    def gmail_refresh_token():
        return _resolve("gmail_refresh_token", "GMAIL_REFRESH_TOKEN", "")


# For backwards-compat: expose as module-level names via __getattr__
_DYNAMIC_KEYS = {
    "GEMINI_API_KEY":      _Cfg.gemini_api_key,
    "GMAIL_USER":          _Cfg.gmail_user,
    "GMAIL_APP_PASSWORD":  _Cfg.gmail_app_password,
    "GMAIL_CLIENT_ID":     _Cfg.gmail_client_id,
    "GMAIL_CLIENT_SECRET": _Cfg.gmail_client_secret,
    "GMAIL_REFRESH_TOKEN": _Cfg.gmail_refresh_token,
}

def __getattr__(name: str):
    fn = _DYNAMIC_KEYS.get(name)
    if fn:
        return fn()
    raise AttributeError(f"module 'config' has no attribute {name!r}")


# =============================================================================
# Gmail Paths
# =============================================================================
GMAIL_CREDENTIALS_FILE = CREDENTIALS_DIR / "gmail_credentials.json"
GMAIL_TOKEN_FILE = CREDENTIALS_DIR / "gmail_token.json"

# =============================================================================
# Scraping Configuration  (runtime-updatable)
# =============================================================================
def _scrape_min_delay():
    return float(_resolve("scrape_min_delay", "SCRAPE_MIN_DELAY", "2"))

def _scrape_max_delay():
    return float(_resolve("scrape_max_delay", "SCRAPE_MAX_DELAY", "5"))

def _max_leads():
    return int(_resolve("max_leads_per_session", "MAX_LEADS_PER_SESSION", "50"))

def _max_concurrent_browsers():
    return int(_resolve("max_concurrent_browsers", "MAX_CONCURRENT_BROWSERS", "10"))

# Register dynamic scraping keys
_DYNAMIC_KEYS.update({
    "SCRAPE_MIN_DELAY":        _scrape_min_delay,
    "SCRAPE_MAX_DELAY":        _scrape_max_delay,
    "MAX_LEADS_PER_SESSION":   _max_leads,
    "MAX_CONCURRENT_BROWSERS": _max_concurrent_browsers,
})

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# =============================================================================
# Email Generation Settings  (runtime-updatable)
# =============================================================================
def _email_framework():
    return _resolve("default_email_framework", "DEFAULT_EMAIL_FRAMEWORK", "AIDA")

def _max_email_words():
    return int(_resolve("max_email_words", "MAX_EMAIL_WORDS", "120"))

def _gemini_temperature():
    return float(_resolve("gemini_temperature", "GEMINI_TEMPERATURE", "0.8"))

_DYNAMIC_KEYS.update({
    "DEFAULT_EMAIL_FRAMEWORK": _email_framework,
    "MAX_EMAIL_WORDS":         _max_email_words,
    "GEMINI_TEMPERATURE":      _gemini_temperature,
})

GEMINI_MODEL = "gemini-1.5-flash"

# =============================================================================
# Data Storage
# =============================================================================
LEADS_DB_FILE = DATA_DIR / "leads.json"

# =============================================================================
# UI Settings
# =============================================================================
PAGE_TITLE = "BruceLeads"
PAGE_ICON = "🥊"
LAYOUT = "wide"

LEAD_STATUSES = {
    "pending": "⏳ Pending",
    "enriched": "📧 Enriched",
    "generated": "✉️ Email Generated",
    "draft": "📝 Draft Created",
    "sent": "✅ Sent",
    "failed": "❌ Failed",
}

LEAD_SOURCES = ["Google Maps", "X/Twitter", "LinkedIn"]


# =============================================================================
# Validation & Summary
# =============================================================================
def validate_config():
    """Check if required configuration is present."""
    warnings = []
    if not _Cfg.gemini_api_key():
        warnings.append("GEMINI_API_KEY not set — AI email generation will use template fallback")
    return warnings


def get_config_summary():
    """Return a summary of current configuration for UI display."""
    has_gemini = bool(_Cfg.gemini_api_key())
    has_gmail_smtp = bool(_Cfg.gmail_user() and _Cfg.gmail_app_password())
    has_gmail_oauth = GMAIL_TOKEN_FILE.exists()
    has_gmail_creds = GMAIL_CREDENTIALS_FILE.exists()

    return {
        "gemini_api": "configured" if has_gemini else "not_set",
        "gmail_oauth": (
            "connected" if has_gmail_oauth
            else "credentials_ready" if has_gmail_creds
            else "not_setup"
        ),
        "gmail_smtp": "configured" if has_gmail_smtp else "not_set",
        "scrape_delay": f"{_scrape_min_delay()}-{_scrape_max_delay()}s",
        "max_leads": _max_leads(),
        "max_concurrent_browsers": _max_concurrent_browsers(),
        "email_framework": _email_framework(),
        "max_email_words": _max_email_words(),
        "gemini_temperature": _gemini_temperature(),
    }


def is_setup_complete() -> bool:
    """Return True if the user has completed initial setup."""
    # Check explicit flag first (set by setup wizard /complete endpoint)
    if get_setting("setup_completed"):
        return True
    # Fallback: if they have a Gemini key configured (e.g. via .env), consider setup done
    return bool(_Cfg.gemini_api_key())
