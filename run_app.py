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

# ── PyInstaller hidden-import hints ──
# Worker scripts (worker.py, social_worker.py, enrich_worker.py, login_worker.py)
# are executed via runpy.run_path() in --worker mode. PyInstaller cannot trace
# their imports because they are added as data files. This block ensures all
# worker dependencies are bundled in the frozen EXE.
if False:  # never executed — only read by PyInstaller's analysis
    import playwright.async_api          # worker.py, enrich_worker.py
    import playwright.sync_api           # social_worker.py, login_worker.py
    import playwright._impl              # internal playwright machinery
    import playwright._impl._connection
    import playwright._impl._driver
    import playwright._impl._transport
    import playwright_stealth             # stealth evasions in workers
    import bs4                            # enrich_worker.py
    import lxml                           # bs4 parser backend
    import greenlet                       # playwright dependency
    import pyee                           # playwright dependency


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
        
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(default_path)


def install_dependencies():
    """Install required dependencies on first run.
    Checks for Playwright browsers and installs them if missing.
    Also installs pip requirements if running from source."""
    import subprocess as _sp

    is_frozen = getattr(sys, 'frozen', False)

    # ── Playwright browsers ──
    if sys.platform == 'win32':
        browsers_dir = Path(os.environ.get('LOCALAPPDATA', '')) / 'ms-playwright'
    else:
        browsers_dir = Path.home() / '.cache' / 'ms-playwright'

    # Check if chromium is installed (the main browser we need)
    chromium_installed = False
    if browsers_dir.exists():
        for child in browsers_dir.iterdir():
            if child.is_dir() and 'chromium' in child.name.lower():
                chromium_installed = True
                break

    if not chromium_installed:
        print("[BruceLeads] First run — installing Playwright Chromium browser...")
        print("[BruceLeads] This may take a minute, please wait...")
        try:
            if is_frozen:
                # In frozen EXE, sys.executable is BruceLeads.exe — NOT Python.
                # Using sys.executable would re-launch the app in an infinite loop.
                # Instead, use Playwright's bundled driver (Node.js binary) directly.
                from playwright._impl._driver import compute_driver_executable, get_driver_env
                driver = compute_driver_executable()
                _sp.run(
                    [str(driver), "install", "chromium"],
                    env=get_driver_env(),
                    check=True,
                    timeout=300,
                )
            else:
                _sp.run(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    check=True,
                    timeout=300,
                )
            print("[BruceLeads] Chromium browser installed successfully.")
        except Exception as e:
            print(f"[BruceLeads] Warning: Could not install Chromium automatically: {e}")
            print("[BruceLeads] Run 'playwright install chromium' manually if scraping fails.")

    # ── Pip requirements (source mode only) ──
    if not is_frozen:
        req_file = Path(__file__).parent / "requirements.txt"
        if req_file.exists():
            # Quick check: try importing a key dependency
            try:
                import fastapi
                import playwright
            except ImportError:
                print("[BruceLeads] Installing Python dependencies...")
                try:
                    _sp.run(
                        [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"],
                        check=True,
                        timeout=300,
                    )
                    print("[BruceLeads] Dependencies installed.")
                except Exception as e:
                    print(f"[BruceLeads] Warning: pip install failed: {e}")
                    print("[BruceLeads] Run 'pip install -r requirements.txt' manually.")


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
    from starlette.exceptions import HTTPException as StarletteHTTPException

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
        app.routes[:] = [r for r in app.routes if not (hasattr(r, 'path') and r.path == '/' and hasattr(r, 'endpoint') and r.endpoint.__name__ == 'read_root')]

        @app.get("/", include_in_schema=False)
        async def serve_index():
            return FileResponse(str(index_file))

        # Use 404 exception handler for SPA fallback instead of a catch-all route.
        # A catch-all /{path:path} would intercept API calls (e.g. /api/leads
        # without trailing slash) before they reach the router, returning null.
        @app.exception_handler(404)
        async def spa_fallback(request, exc):
            path = request.url.path
            if path.startswith("/api") or path in ("/stats", "/config"):
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "Not Found"}, status_code=404)
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
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='BruceLeads Application')
    parser.add_argument('--port', type=int, default=8001, help='Port to run the application on')
    args = parser.parse_args()

    host = "127.0.0.1"
    port = args.port
    is_frozen = getattr(sys, 'frozen', False)

    ensure_data_dirs()

    if is_frozen:
        # Production / EXE mode
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
        # Development mode
        from backend.main import app

        # Mount the built frontend if available (enables localhost:8000 for full-stack dev)
        mount_static_frontend(app)

        print(f"[BruceLeads] Dev server starting on http://localhost:{port}")

        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=False
        )


if __name__ == "__main__":
    # Always set up Playwright browser path for frozen mode
    setup_playwright_env()

    # Install dependencies (Playwright browsers, pip packages) if missing
    # Skip for worker subprocesses — only the main app installs
    if not (len(sys.argv) >= 3 and sys.argv[1] == "--worker"):
        install_dependencies()

    # Support --worker mode for subprocess workers in frozen EXE
    if len(sys.argv) >= 3 and sys.argv[1] == "--worker":
        # Run a worker script: BruceLeads.exe --worker <script> [args...]
        worker_script = sys.argv[2]
        worker_args = sys.argv[3:]

        # Security: validate the worker script is within the project directory
        import os
        base = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
        try:
            worker_path = Path(worker_script).resolve()
            base_resolved = base.resolve()
            if not str(worker_path).startswith(str(base_resolved)):
                print(f"[BruceLeads] Security: worker script '{worker_script}' is outside project directory", file=sys.stderr)
                sys.exit(1)
            if not worker_path.exists():
                print(f"[BruceLeads] Worker script not found: {worker_script}", file=sys.stderr)
                sys.exit(1)
            if not worker_path.suffix == '.py':
                print(f"[BruceLeads] Worker script must be a .py file: {worker_script}", file=sys.stderr)
                sys.exit(1)
        except Exception as e:
            print(f"[BruceLeads] Invalid worker script path: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Replace sys.argv so the worker sees the right args
        sys.argv = [worker_script] + worker_args
        
        # Execute the worker script
        import runpy
        runpy.run_path(worker_script, run_name="__main__")
    else:
        main()
