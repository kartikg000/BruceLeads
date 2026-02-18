"""
Auto-Update API Router
Checks GitHub Releases for newer versions and applies updates in-place.

Endpoints:
  GET  /api/update/check  — Compare local version to latest GitHub release
  POST /api/update/apply  — Download latest release ZIP, extract, restart app
"""

import sys
import os
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

import config

router = APIRouter()

# ─── Helpers ───────────────────────────────────────────────────

def _parse_version(tag: str) -> tuple:
    """Turn 'v2.1.0' or '2.1.0' into (2, 1, 0) for comparison."""
    tag = tag.lstrip("vV").strip()
    parts = []
    for p in tag.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def _get_app_dir() -> Path:
    """Return the directory that contains the running app (EXE folder or project root)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


# ─── Endpoints ─────────────────────────────────────────────────

@router.get("/check")
async def check_for_update():
    """
    Query the GitHub Releases API and compare tags.
    Returns: { update_available, current_version, latest_version, download_url, release_notes }
    """
    api_url = f"https://api.github.com/repos/{config.GITHUB_REPO}/releases/latest"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(api_url, headers={"Accept": "application/vnd.github+json"})
        if resp.status_code == 404:
            return {"update_available": False, "current_version": config.APP_VERSION,
                    "latest_version": config.APP_VERSION, "message": "No releases found"}
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach GitHub: {exc}")

    data = resp.json()
    latest_tag = data.get("tag_name", "0.0.0")
    latest_ver = _parse_version(latest_tag)
    current_ver = _parse_version(config.APP_VERSION)

    # Find the .zip asset
    download_url = None
    for asset in data.get("assets", []):
        if asset["name"].endswith(".zip"):
            download_url = asset["browser_download_url"]
            break

    return {
        "update_available": latest_ver > current_ver,
        "current_version": config.APP_VERSION,
        "latest_version": latest_tag.lstrip("vV"),
        "release_notes": data.get("body", ""),
        "download_url": download_url,
    }


@router.post("/apply")
async def apply_update():
    """
    Download the latest release ZIP from GitHub, extract it, and launch a
    helper script that replaces the current app files and restarts.
    """
    # 1. Fetch latest release info
    check = await check_for_update()
    if not check["update_available"]:
        return {"status": "already_up_to_date", "current_version": config.APP_VERSION}

    download_url = check.get("download_url")
    if not download_url:
        raise HTTPException(status_code=404, detail="No ZIP asset found in the latest release")

    app_dir = _get_app_dir()
    tmp_dir = Path(tempfile.mkdtemp(prefix="bruceleads_update_"))
    zip_path = tmp_dir / "update.zip"

    # 2. Download the ZIP
    try:
        async with httpx.AsyncClient(timeout=600, follow_redirects=True) as client:
            async with client.stream("GET", download_url) as resp:
                resp.raise_for_status()
                with open(zip_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=1024 * 64):
                        f.write(chunk)
    except httpx.HTTPError as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=502, detail=f"Download failed: {exc}")

    # 3. Extract
    extract_dir = tmp_dir / "extracted"
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)
    except zipfile.BadZipFile:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail="Downloaded file is not a valid ZIP")

    # The ZIP likely contains a single top-level folder (e.g. BruceLeads/)
    children = list(extract_dir.iterdir())
    source_dir = children[0] if len(children) == 1 and children[0].is_dir() else extract_dir

    # 4. Write a batch/ps1 script that:
    #    a) waits for this process to exit
    #    b) copies new files over old ones (preserving data/ and credentials/)
    #    c) restarts the app
    if sys.platform == "win32":
        updater_script = tmp_dir / "do_update.bat"
        exe_name = Path(sys.executable).name if getattr(sys, "frozen", False) else "python"

        # Build the restart command
        if getattr(sys, "frozen", False):
            restart_cmd = f'start "" "{app_dir / exe_name}"'
        else:
            restart_cmd = f'start "" python "{app_dir / "run_app.py"}"'

        updater_script.write_text(
            f"""@echo off
echo [BruceLeads Updater] Waiting for app to exit...
timeout /t 3 /nobreak >nul

echo [BruceLeads Updater] Copying new files...
xcopy /E /Y /I /Q "{source_dir}\\*" "{app_dir}\\" >nul 2>&1

echo [BruceLeads Updater] Cleaning up temp files...
rmdir /S /Q "{tmp_dir}" >nul 2>&1

echo [BruceLeads Updater] Restarting BruceLeads...
cd /d "{app_dir}"
{restart_cmd}
exit
""",
            encoding="utf-8",
        )

        # 5. Launch the updater script detached, then signal the app to shut down
        subprocess.Popen(
            ["cmd", "/c", str(updater_script)],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
    else:
        # macOS / Linux
        updater_script = tmp_dir / "do_update.sh"
        if getattr(sys, "frozen", False):
            restart_cmd = f'"{app_dir / Path(sys.executable).name}" &'
        else:
            restart_cmd = f'python3 "{app_dir / "run_app.py"}" &'

        updater_script.write_text(
            f"""#!/bin/bash
echo "[BruceLeads Updater] Waiting for app to exit..."
sleep 3

echo "[BruceLeads Updater] Copying new files..."
cp -rf "{source_dir}/"* "{app_dir}/"

echo "[BruceLeads Updater] Cleaning up..."
rm -rf "{tmp_dir}"

echo "[BruceLeads Updater] Restarting BruceLeads..."
cd "{app_dir}"
{restart_cmd}
""",
            encoding="utf-8",
        )
        os.chmod(updater_script, 0o755)

        subprocess.Popen(
            ["bash", str(updater_script)],
            start_new_session=True,
            close_fds=True,
        )

    # 6. Tell the frontend update is in progress, then shut down
    import threading

    def _shutdown():
        import time
        time.sleep(1)
        os._exit(0)

    threading.Thread(target=_shutdown, daemon=True).start()

    return {
        "status": "updating",
        "message": "Downloading update and restarting. The app will relaunch automatically.",
    }
