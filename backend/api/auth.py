"""
Google OAuth Authentication
Login with Google, session management, logout.
Also provisions the Gmail API token so the emailer can send via OAuth.
"""

import json
import os
import secrets
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

import config

router = APIRouter()

_SESSION_FILE = config.DATA_DIR / "auth_session.json"
_oauth_state = {}

# Allowed redirect hosts (prevent open-redirect attacks)
_ALLOWED_REDIRECT_HOSTS = {"localhost", "127.0.0.1"}

# Combined scopes: login + Gmail send
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def _load_session() -> dict:
    if _SESSION_FILE.exists():
        try:
            return json.loads(_SESSION_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_session(data: dict):
    _SESSION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _save_gmail_token(credentials):
    """Persist the OAuth token so GmailClient can send via Gmail API."""
    try:
        token_path = config.GMAIL_TOKEN_FILE
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(credentials.to_json(), encoding="utf-8")
    except Exception as exc:
        print(f"[auth] Warning: could not save gmail token: {exc}")


# ─── Endpoints ────────────────────────────────────────────────


@router.get("/has-credentials")
def has_credentials():
    """Check if Google OAuth credentials.json has been uploaded."""
    return {"exists": config.GMAIL_CREDENTIALS_FILE.exists()}


@router.get("/login-url")
def get_login_url(redirect: str = "http://localhost:8000"):
    """Generate a Google OAuth consent URL."""
    # Validate redirect URL to prevent open-redirect attacks
    try:
        parsed = urlparse(redirect)
        if parsed.hostname not in _ALLOWED_REDIRECT_HOSTS:
            raise HTTPException(400, "Invalid redirect URL")
        if parsed.scheme not in ("http", "https"):
            raise HTTPException(400, "Invalid redirect URL scheme")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Invalid redirect URL")

    if not config.GMAIL_CREDENTIALS_FILE.exists():
        raise HTTPException(400, "Upload Google OAuth credentials.json first")

    from google_auth_oauthlib.flow import Flow

    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # allow http://localhost

    flow = Flow.from_client_secrets_file(
        str(config.GMAIL_CREDENTIALS_FILE),
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/api/auth/callback",
    )
    auth_url, state = flow.authorization_url(
        prompt="consent", access_type="offline"
    )
    _oauth_state.update({"state": state, "redirect": redirect})
    return {"url": auth_url}


@router.get("/callback")
def auth_callback(code: str = None, error: str = None):
    """Handle the OAuth redirect from Google."""
    redirect_base = _oauth_state.get("redirect", "http://localhost:8000")

    # Validate redirect_base before using it
    try:
        parsed = urlparse(redirect_base)
        if parsed.hostname not in _ALLOWED_REDIRECT_HOSTS:
            redirect_base = "http://localhost:8000"
    except Exception:
        redirect_base = "http://localhost:8000"

    if error:
        return RedirectResponse(f"{redirect_base}/?auth_error={error}")
    if not code:
        raise HTTPException(400, "Missing authorization code")

    from google_auth_oauthlib.flow import Flow

    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    flow = Flow.from_client_secrets_file(
        str(config.GMAIL_CREDENTIALS_FILE),
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/api/auth/callback",
    )
    flow.fetch_token(code=code)

    # Save the token for GmailClient (email sending via Gmail API)
    _save_gmail_token(flow.credentials)

    # Fetch user profile from Google
    import requests as req

    userinfo = req.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {flow.credentials.token}"},
    ).json()

    token = secrets.token_urlsafe(32)
    _save_session(
        {
            "token": token,
            "user": {
                "email": userinfo.get("email", ""),
                "name": userinfo.get("name", ""),
                "picture": userinfo.get("picture", ""),
            },
        }
    )
    return RedirectResponse(f"{redirect_base}/?auth_token={token}")


@router.get("/me")
def get_me(token: str = ""):
    """Return the currently logged-in user (if any)."""
    session = _load_session()
    if session.get("token") and token == session["token"]:
        return {"authenticated": True, "user": session.get("user", {})}
    return {"authenticated": False}


@router.post("/logout")
def logout():
    """Clear the active session."""
    if _SESSION_FILE.exists():
        _SESSION_FILE.unlink()
    return {"success": True}
