#!/usr/bin/env bash
# Drag2Music — macOS Build Script
# Usage: chmod +x build_scripts/build_macos.sh && ./build_scripts/build_macos.sh
set -euo pipefail

# Move to project root (parent of build_scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"
echo "============================================================"
echo " Drag2Music — macOS Build"
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

# ── Step 3: Download macOS ffmpeg ────────────────────────────────────────────
echo "[STEP 3/4] Downloading macOS ffmpeg binary..."
python3 build_scripts/download_ffmpeg.py --platform macos
echo

# ── Step 4: PyInstaller ──────────────────────────────────────────────────────
echo "[STEP 4/5] Running PyInstaller (onedir → Drag2Music.app)..."
pyinstaller drag2music.spec --clean --noconfirm
echo

# ── Step 5: Create DMG ───────────────────────────────────────────────────────
echo "[STEP 5/5] Creating .dmg installer..."
chmod +x installer/macos/create_dmg.sh
bash installer/macos/create_dmg.sh
echo

echo "============================================================"
echo " Build complete!"
echo " App     : dist/Drag2Music.app"
echo " Disk img: dist/Drag2Music.dmg"
echo "============================================================"
