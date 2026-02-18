
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path

# Add parent directory to path to import existing modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import LeadsDatabase, Lead
from backend.api import leads, scraper, email, gmail, sessions, setup, auth, updater
from backend.dependencies import get_db

app = FastAPI(title="BruceLeads API")

# Allow CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify generic localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    """Get current configuration summary."""
    import config as cfg
    return cfg.get_config_summary()
