
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import sys
from pathlib import Path

# Add parent directory to path to import existing modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import LeadsDatabase, Lead
from backend.api import leads, scraper, email, gmail, sessions, setup, auth, updater
from backend.dependencies import get_db

app = FastAPI(title="BruceLeads API", docs_url=None, redoc_url=None)

# ── Security Headers Middleware ──────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "font-src 'self' data:; "
            "frame-ancestors 'none'"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Allow CORS for React Frontend — restrict to localhost only
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Use shared Database instance
db = get_db()

# Mount Routers
app.include_router(leads.router, prefix="/api/leads", tags=["leads"])
app.include_router(scraper.router, prefix="/api/scrape", tags=["scraper"])
app.include_router(email.router, prefix="/api/email", tags=["email"])
app.include_router(gmail.router, prefix="/api/gmail", tags=["gmail"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(setup.router, prefix="/api/setup", tags=["setup"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(updater.router, prefix="/api/update", tags=["update"])

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"status": "ok", "app": "BruceLeads API"}

@app.get("/stats")
def get_stats():
    """Get dashboard stats."""
    return db.get_stats()

@app.get("/config")
def get_config():
    """Get current configuration summary (secrets masked)."""
    import config as cfg
    summary = cfg.get_config_summary()
    # Never expose raw secret values over the API
    for key in ("gemini_api", "gmail_smtp"):
        if summary.get(key) not in ("configured", "not_set", None):
            summary[key] = "configured"
    return summary
