"""
BruceLeads Application Launcher
Starts the FastAPI backend and opens the UI in the default browser.
Handles both development mode and frozen EXE (PyInstaller) distribution.
"""

import sys
import os
import time
import threading
import webbrowser
from pathlib import Path


def get_base_dir():
    """Get the base directory (works for both dev and frozen EXE)."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def setup_playwright_env():
    """Set PLAYWRIGHT_BROWSERS_PATH so Playwright finds installed browsers.
    In frozen EXE mode, Playwright's bundled driver looks in the wrong place.
    We redirect it to the user's standard ms-playwright install location."""
    if 'PLAYWRIGHT_BROWSERS_PATH' not in os.environ:
        # Standard user install location
        if sys.platform == 'win32':
            default_path = Path(os.environ.get('LOCALAPPDATA', '')) / 'ms-playwright'
        else:
            default_path = Path.home() / '.cache' / 'ms-playwright'
        
        if default_path.exists():
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(default_path)


def ensure_data_dirs():
    """Create required data directories if they don't exist."""
    # Use CWD for mutable data in frozen mode, project root otherwise
    if getattr(sys, 'frozen', False):
        data_root = Path(os.getcwd())
    else:
        data_root = Path(__file__).parent

    for d in ['data', 'credentials']:
        (data_root / d).mkdir(exist_ok=True)


def mount_static_frontend(app):
    """Mount the built React frontend for production/EXE mode."""
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    base = get_base_dir()
    dist_dir = base / "frontend" / "dist"

    if not dist_dir.exists():
        # Try relative to CWD for onedir builds
        dist_dir = Path(os.getcwd()) / "frontend" / "dist"

    if dist_dir.exists():
        index_file = dist_dir / "index.html"

        # Serve static assets (JS, CSS, images)
        app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="static-assets")

        # Override the root "/" route to serve index.html instead of API JSON
        # We need to remove the existing "/" route and replace it
        app.routes[:] = [r for r in app.routes if not (hasattr(r, 'path') and r.path == '/' and hasattr(r, 'endpoint') and r.endpoint.__name__ == 'read_root')]

        @app.get("/", include_in_schema=False)
        async def serve_index():
            return FileResponse(str(index_file))

        # Catch-all: serve index.html for client-side routes (React Router)
        @app.api_route("/{full_path:path}", methods=["GET"], include_in_schema=False)
        async def serve_spa(full_path: str):
            # Don't intercept API, stats, or config routes
            if full_path.startswith("api/") or full_path in ("stats", "config"):
                return None
            return FileResponse(str(index_file))

        print(f"[BruceLeads] Serving frontend from {dist_dir}")
        return True
    else:
        print("[BruceLeads] No frontend/dist found — run 'npm run build' in frontend/ first")
        return False


def open_browser(port: int, delay: float = 2.5):
    """Open the app in the default browser after a short delay."""
    def _open():
        time.sleep(delay)
        url = f"http://localhost:{port}"
        try:
            # os.startfile is most reliable on Windows from frozen EXEs
            if sys.platform == "win32":
                os.startfile(url)
            else:
                webbrowser.open(url)
            print(f"[BruceLeads] Opened browser: {url}")
        except Exception as e:
            print(f"[BruceLeads] Could not open browser automatically: {e}")
            print(f"[BruceLeads] Please open {url} in your browser manually.")
    threading.Thread(target=_open, daemon=True).start()


def main():
    import uvicorn

    host = "127.0.0.1"
    port = 8000
    is_frozen = getattr(sys, 'frozen', False)

    ensure_data_dirs()

    if is_frozen:
        # Production / EXE mode
        # Import and mount the frontend
        from backend.main import app
        mount_static_frontend(app)

        print(f"[BruceLeads] Starting on http://localhost:{port}")
        open_browser(port)

        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="warning"
        )
    else:
        # Development mode — use reload for hot reloading
        print(f"[BruceLeads] Dev server starting on http://localhost:{port}")
        print("[BruceLeads] Frontend dev server: cd frontend && npm run dev")

        uvicorn.run(
            "backend.main:app",
            host=host,
            port=port,
            reload=True
        )


if __name__ == "__main__":
    # Always set up Playwright browser path for frozen mode
    setup_playwright_env()
    
    # Support --worker mode for subprocess workers in frozen EXE
    if len(sys.argv) >= 3 and sys.argv[1] == "--worker":
        # Run a worker script: BruceLeads.exe --worker <script> [args...]
        worker_script = sys.argv[2]
        worker_args = sys.argv[3:]
        
        # Replace sys.argv so the worker sees the right args
        sys.argv = [worker_script] + worker_args
        
        # Execute the worker script
        import runpy
        runpy.run_path(worker_script, run_name="__main__")
    else:
        main()
