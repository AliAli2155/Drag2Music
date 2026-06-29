#!/usr/bin/env bash
# Drag2Music — Linux Build Script
# Usage: chmod +x build_scripts/build_linux.sh && ./build_scripts/build_linux.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "============================================================"
echo " Drag2Music — Linux Build"
echo "============================================================"
echo "[INFO] Project root: $PROJECT_ROOT"
echo

# ── Step 1: Install Python dependencies ─────────────────────────────────────
echo "[STEP 1/4] Installing Python dependencies..."
pip3 install -r requirements.txt
echo

# ── Step 2: Set up assets ────────────────────────────────────────────────────
echo "[STEP 2/4] Setting up assets (icons)..."
python3 build_scripts/setup_assets.py
echo

# ── Step 3: Download Linux ffmpeg ────────────────────────────────────────────
echo "[STEP 3/4] Downloading Linux ffmpeg binary..."
python3 build_scripts/download_ffmpeg.py --platform linux
echo

# ── Step 4: PyInstaller ──────────────────────────────────────────────────────
echo "[STEP 4/5] Running PyInstaller (onedir)..."
pyinstaller drag2music.spec --clean --noconfirm
echo

# ── Step 5: AppImage + .deb ──────────────────────────────────────────────────
echo "[STEP 5/5] Creating AppImage and .deb package..."
chmod +x installer/linux/create_appimage.sh
bash installer/linux/create_appimage.sh
echo

echo "============================================================"
echo " Build complete!"
echo " App dir  : dist/Drag2Music/"
echo " AppImage : Drag2Music-x86_64.AppImage"
echo " Deb pkg  : drag2music_3.2.0_amd64.deb"
echo "============================================================"
