"""
Setup API Router
First-run wizard and runtime settings management.

Endpoints:
  GET  /api/setup/status             — Is initial setup complete?
  POST /api/setup/gemini             — Save Gemini API key
  POST /api/setup/gmail-smtp         — Save Gmail SMTP credentials
  POST /api/setup/gmail-upload       — Upload OAuth credentials JSON
  POST /api/setup/complete           — Mark setup as done
  GET  /api/setup/settings           — Get all runtime settings
  POST /api/setup/settings           — Update runtime settings
  GET  /api/setup/playwright-status  — Check if Playwright Chromium is installed
  POST /api/setup/install-playwright — Install Playwright Chromium
"""

import json
import subprocess
import sys
import shutil
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional

import config

router = APIRouter()


# ─── Models ────────────────────────────────────────────────────

class GeminiSetup(BaseModel):
    api_key: str


class GmailSMTPSetup(BaseModel):
    email: str
    app_password: str


class SettingsUpdate(BaseModel):
    gemini_api_key: Optional[str] = None
    gmail_user: Optional[str] = None
    gmail_address: Optional[str] = None      # alias accepted from frontend
    gmail_app_password: Optional[str] = None
    max_concurrent_browsers: Optional[int] = None
    max_leads_per_session: Optional[int] = None
    scrape_min_delay: Optional[float] = None
    scrape_max_delay: Optional[float] = None
    scraping_delay: Optional[float] = None   # alias accepted from frontend
    default_email_framework: Optional[str] = None
    max_email_words: Optional[int] = None
    gemini_temperature: Optional[float] = None


# ─── Setup Wizard Endpoints ───────────────────────────────────

@router.get("/status")
def setup_status():
    """Check if first-run setup has been completed."""
    return {
        "setup_complete": config.is_setup_complete(),
        "has_gemini_key": bool(config.GEMINI_API_KEY),
        "has_gmail_oauth": config.GMAIL_CREDENTIALS_FILE.exists(),
        "has_gmail_smtp": bool(config.GMAIL_USER and config.GMAIL_APP_PASSWORD),
        "has_gmail_token": config.GMAIL_TOKEN_FILE.exists(),
    }


@router.post("/gemini")
def save_gemini_key(body: GeminiSetup):
    """Save Gemini API key to runtime settings."""
    key = body.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API key cannot be empty")

    # Quick validation: try to configure the SDK
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        # Fire a tiny request to validate the key
        model.generate_content("Say OK", generation_config={"max_output_tokens": 5})
    except Exception as e:
        err = str(e)
        if "API_KEY_INVALID" in err or "INVALID" in err.upper():
            raise HTTPException(status_code=400, detail="Invalid API key. Please check and try again.")
        # Non-key errors (quota, etc.) — the key itself is probably fine
        pass

    config.update_settings({"gemini_api_key": key})
    return {"success": True, "message": "Gemini API key saved"}


@router.post("/gmail-smtp")
def save_gmail_smtp(body: GmailSMTPSetup):
    """Save Gmail SMTP (App Password) credentials."""
    if not body.email or not body.app_password:
        raise HTTPException(status_code=400, detail="Email and app password are required")

    config.update_settings({
        "gmail_user": body.email.strip(),
        "gmail_app_password": body.app_password.strip(),
    })
    return {"success": True, "message": "Gmail SMTP credentials saved"}


@router.post("/gmail-upload")
async def upload_gmail_credentials(file: UploadFile = File(...)):
    """
    Upload Google Cloud OAuth credentials JSON.
    The file is saved to credentials/gmail_credentials.json.
    """
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="File must be a .json file")

    content = await file.read()

    # Validate it looks like a Google credentials file
    try:
        data = json.loads(content)
        # Google credentials have either "installed" or "web" as top-level key
        if "installed" not in data and "web" not in data:
            raise HTTPException(
                status_code=400,
                detail="Invalid credentials file. Expected a Google OAuth credentials JSON with 'installed' or 'web' key.",
            )
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    # Save the file
    config.CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.GMAIL_CREDENTIALS_FILE, "wb") as f:
        f.write(content)

    return {"success": True, "message": "Gmail OAuth credentials uploaded"}


@router.post("/complete")
def mark_setup_complete():
    """Mark the initial setup wizard as completed."""
    config.update_settings({"setup_completed": True})
    return {"success": True}


# ─── Playwright Management ────────────────────────────────────

def _check_playwright_chromium() -> bool:
    """Check if Playwright Chromium browser is installed."""
    try:
        # Check if the chromium executable exists via playwright's registry
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"],
            capture_output=True, text=True, timeout=15
        )
        # If dry-run doesn't exist in this version, try checking directly
        if result.returncode != 0:
            # Fallback: try to import and check
            try:
                from playwright.sync_api import sync_playwright
                p = sync_playwright().start()
                try:
                    browser = p.chromium.launch(headless=True)
                    browser.close()
                    p.stop()
                    return True
                except Exception:
                    p.stop()
                    return False
            except Exception:
                return False
        return True
    except Exception:
        # Another fallback: check common install paths
        try:
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "--help"],
                capture_output=True, text=True, timeout=10
            )
            # If playwright module exists, check if chromium is there
            if result.returncode == 0:
                # Try browsers path
                import pathlib
                browsers_path = pathlib.Path.home() / "AppData" / "Local" / "ms-playwright"
                if browsers_path.exists():
                    chromium_dirs = list(browsers_path.glob("chromium-*"))
                    return len(chromium_dirs) > 0
            return False
        except Exception:
            return False


@router.get("/playwright-status")
def playwright_status():
    """Check if Playwright and Chromium are available."""
    try:
        # Check if playwright module is installed
        import playwright
        pw_installed = True
    except ImportError:
        pw_installed = False

    chromium_installed = False
    if pw_installed:
        # Check common Playwright browser path
        import pathlib
        browsers_path = pathlib.Path.home() / "AppData" / "Local" / "ms-playwright"
        if browsers_path.exists():
            chromium_dirs = list(browsers_path.glob("chromium-*"))
            chromium_installed = len(chromium_dirs) > 0

    return {
        "playwright_installed": pw_installed,
        "chromium_installed": chromium_installed,
    }


@router.post("/install-playwright")
def install_playwright():
    """Install Playwright Chromium browser. This may take a minute."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode == 0:
            return {
                "success": True,
                "message": "Chromium browser installed successfully!",
            }
        else:
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            return {
                "success": False,
                "message": f"Installation failed: {error_msg[:300]}",
            }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Installation timed out. Please try again or run 'playwright install chromium' manually.",
        }
    except FileNotFoundError:
        return {
            "success": False,
            "message": "Playwright is not installed. Run 'pip install playwright' first.",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)[:200]}",
        }


# ─── Runtime Settings Endpoints ───────────────────────────────

@router.get("/settings")
def get_settings():
    """Return all current runtime settings (merged with defaults)."""
    summary = config.get_config_summary()
    raw = config.get_all_settings()

    # Mask secrets for display
    return {
        "summary": summary,
        "settings": {
            "gemini_api_key": _mask(raw.get("gemini_api_key", "")),
            "gmail_user": raw.get("gmail_user", "") or config.GMAIL_USER,
            "gmail_app_password": _mask(raw.get("gmail_app_password", "")),
            "max_concurrent_browsers": config.MAX_CONCURRENT_BROWSERS,
            "max_leads_per_session": config.MAX_LEADS_PER_SESSION,
            "scrape_min_delay": config.SCRAPE_MIN_DELAY,
            "scrape_max_delay": config.SCRAPE_MAX_DELAY,
            "default_email_framework": config.DEFAULT_EMAIL_FRAMEWORK,
            "max_email_words": config.MAX_EMAIL_WORDS,
            "gemini_temperature": config.GEMINI_TEMPERATURE,
        },
    }


@router.post("/settings")
def update_settings(body: SettingsUpdate):
    """Update one or more runtime settings."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No settings to update")

    # Normalize frontend aliases
    if "gmail_address" in updates:
        updates["gmail_user"] = updates.pop("gmail_address")
    if "scraping_delay" in updates:
        delay = updates.pop("scraping_delay")
        updates["scrape_min_delay"] = delay
        updates["scrape_max_delay"] = delay + 3.0

    # Validate ranges
    if "max_concurrent_browsers" in updates:
        val = updates["max_concurrent_browsers"]
        if not 1 <= val <= 10:
            raise HTTPException(status_code=400, detail="max_concurrent_browsers must be 1-10")

    if "gemini_temperature" in updates:
        val = updates["gemini_temperature"]
        if not 0.0 <= val <= 2.0:
            raise HTTPException(status_code=400, detail="Temperature must be 0.0-2.0")

    if "max_email_words" in updates:
        val = updates["max_email_words"]
        if not 50 <= val <= 500:
            raise HTTPException(status_code=400, detail="Max email words must be 50-500")

    config.update_settings(updates)
    return {"success": True, "message": f"Updated {len(updates)} setting(s)"}


# ─── Helpers ──────────────────────────────────────────────────

def _mask(value: str) -> str:
    """Mask a secret string for display, e.g. 'AIza...Xyz'."""
    if not value or len(value) < 8:
        return "••••" if value else ""
    return value[:4] + "•" * (len(value) - 8) + value[-4:]
