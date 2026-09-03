
@echo off
echo ============================================
echo   BruceLeads - Build Executable
echo ============================================
echo.

:: Step 1: Build React frontend
echo [1/3] Building React frontend...
cd frontend
call npm install
call npm run build
cd ..

if not exist "frontend\dist\index.html" (
    echo ERROR: Frontend build failed! Check for errors above.
    pause
    exit /b 1
)
echo       Frontend built successfully.
echo.

:: Step 2: Install Python dependencies
echo [2/3] Checking Python dependencies...
pip install pyinstaller --quiet
echo       Dependencies ready.
echo.

:: Step 3: Build EXE with PyInstaller
echo [3/3] Building EXE with PyInstaller...
pyinstaller --noconfirm --onedir --console --clean ^
    --name "BruceLeads" ^
    --icon "bruceLeads.ico" ^
    --add-data "backend;backend" ^
    --add-data "models;models" ^
    --add-data "scrapers;scrapers" ^
    --add-data "emailer;emailer" ^
    --add-data "utils;utils" ^
    --add-data "config.py;." ^
    --add-data "frontend/dist;frontend/dist" ^
    --hidden-import "playwright" ^
    --hidden-import "playwright.async_api" ^
    --hidden-import "playwright.sync_api" ^
    --hidden-import "playwright._impl" ^
    --hidden-import "playwright._impl._connection" ^
    --hidden-import "playwright._impl._driver" ^
    --hidden-import "playwright._impl._transport" ^
    --hidden-import "playwright_stealth" ^
    --hidden-import "greenlet" ^
    --hidden-import "pyee" ^
    --hidden-import "uvicorn" ^
    --hidden-import "uvicorn.logging" ^
    --hidden-import "uvicorn.loops" ^
    --hidden-import "uvicorn.loops.auto" ^
    --hidden-import "uvicorn.protocols" ^
    --hidden-import "uvicorn.protocols.http" ^
    --hidden-import "uvicorn.protocols.http.auto" ^
    --hidden-import "uvicorn.protocols.websockets" ^
    --hidden-import "uvicorn.protocols.websockets.auto" ^
    --hidden-import "uvicorn.lifespan" ^
    --hidden-import "uvicorn.lifespan.on" ^
    --hidden-import "uvicorn.lifespan.off" ^
    --hidden-import "fastapi" ^
    --hidden-import "google.genai" ^
    --hidden-import "google.auth" ^
    --hidden-import "google.auth.transport.requests" ^
    --hidden-import "google_auth_oauthlib" ^
    --hidden-import "googleapiclient" ^
    --hidden-import "bs4" ^
    --hidden-import "dotenv" ^
    --hidden-import "multipart" ^
    --collect-submodules "uvicorn" ^
    --collect-submodules "fastapi" ^
    --collect-submodules "playwright" ^
    --collect-data "playwright" ^
    --exclude-module "PyQt5" ^
    --exclude-module "PyQt6" ^
    --exclude-module "PySide2" ^
    --exclude-module "PySide6" ^
    --exclude-module "tkinter" ^
    --exclude-module "panel" ^
    --exclude-module "bokeh" ^
    --exclude-module "matplotlib" ^
    --exclude-module "scipy" ^
    --exclude-module "sklearn" ^
    --exclude-module "skimage" ^
    --exclude-module "notebook" ^
    --exclude-module "jupyterlab" ^
    --exclude-module "jupyter" ^
    --exclude-module "IPython" ^
    --exclude-module "sphinx" ^
    --exclude-module "llvmlite" ^
    --exclude-module "numba" ^
    --exclude-module "botocore" ^
    --exclude-module "boto3" ^
    --exclude-module "selenium" ^
    --exclude-module "pyarrow" ^
    --exclude-module "dask" ^
    --exclude-module "sympy" ^
    --exclude-module "tornado" ^
    --exclude-module "zmq" ^
    --exclude-module "cv2" ^
    --exclude-module "PIL" ^
    --exclude-module "wx" ^
    --exclude-module "qtpy" ^
    run_app.py

:: Create data directories in dist
if not exist "dist\BruceLeads\data" mkdir "dist\BruceLeads\data"
if not exist "dist\BruceLeads\credentials" mkdir "dist\BruceLeads\credentials"

echo.
echo ============================================
echo   Build Complete!
echo ============================================
echo.
echo   Output: dist\BruceLeads\
echo   Run:    dist\BruceLeads\BruceLeads.exe
echo.
echo   The app will open in your browser
echo   automatically when launched.
echo.
echo   To distribute: zip the dist\BruceLeads folder.
echo ============================================
pause
