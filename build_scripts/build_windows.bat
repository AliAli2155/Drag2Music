@echo off
setlocal EnableDelayedExpansion

echo ============================================================
echo  TuneFetch: Infinity Studio — Windows Build Script
echo ============================================================
echo.

:: Move to project root (parent of build_scripts\)
cd /d "%~dp0.."
set "PROJECT_ROOT=%CD%"
echo [INFO] Project root: %PROJECT_ROOT%
echo.

:: ── Step 1: Install Python dependencies ─────────────────────────────────────
echo [STEP 1/4] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed. Ensure Python 3.11+ and pip are available.
    exit /b 1
)
echo.

:: ── Step 2: Set up assets (icons) ───────────────────────────────────────────
echo [STEP 2/4] Setting up assets...
python build_scripts\setup_assets.py
if errorlevel 1 (
    echo [ERROR] Asset setup failed.
    exit /b 1
)
echo.

:: ── Step 3: Download ffmpeg for Windows ─────────────────────────────────────
echo [STEP 3/4] Downloading Windows ffmpeg binary...
python build_scripts\download_ffmpeg.py --platform windows
if errorlevel 1 (
    echo [ERROR] ffmpeg download failed.
    exit /b 1
)
echo.

:: ── Step 4: PyInstaller build ────────────────────────────────────────────────
echo [STEP 4/5] Running PyInstaller...
pyinstaller tunefetch.spec --clean --noconfirm
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    exit /b 1
)
echo.

:: ── Step 5: Inno Setup ──────────────────────────────────────────────────────
echo [STEP 5/5] Building installer with Inno Setup...

:: Locate ISCC (Inno Setup Compiler)
set "ISCC="
if exist "%ISCC%" goto :found_iscc

:: Check PATH
where iscc >nul 2>&1 && set "ISCC=iscc" && goto :found_iscc

:: Common install locations
for %%P in (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    "C:\Program Files\Inno Setup 6\ISCC.exe"
    "C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
    "C:\Program Files\Inno Setup 5\ISCC.exe"
) do (
    if exist %%P (
        set "ISCC=%%P"
        goto :found_iscc
    )
)

echo [WARNING] Inno Setup not found. Skipping installer creation.
echo   To build the installer manually, install Inno Setup 6 from:
echo   https://jrsoftware.org/isinfo.php
echo   Then run: iscc installer\windows\tunefetch_setup.iss
goto :build_done

:found_iscc
echo [INFO] Using ISCC: %ISCC%
"%ISCC%" installer\windows\tunefetch_setup.iss
if errorlevel 1 (
    echo [ERROR] Inno Setup compilation failed.
    exit /b 1
)
echo.

:build_done
echo ============================================================
echo  Build complete!
echo  Installer : dist\TuneFetch_Setup.exe
echo  App folder: dist\TuneFetch\
echo ============================================================
endlocal
