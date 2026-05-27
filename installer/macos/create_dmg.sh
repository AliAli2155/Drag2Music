#!/usr/bin/env bash
# TuneFetch: Infinity Studio — macOS .dmg creator
# Called by build_scripts/build_macos.sh after PyInstaller completes.
# Requires: hdiutil (bundled with macOS), optional: AppleScript for custom layout
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

APP_NAME="TuneFetch"
APP_BUNDLE="dist/${APP_NAME}.app"
DMG_NAME="${APP_NAME}"
DMG_OUT="dist/${DMG_NAME}.dmg"
TMP_DIR="$(mktemp -d)"
VOLUME_NAME="TuneFetch Infinity Studio"

echo "[DMG] Checking for built .app..."
if [ ! -d "$APP_BUNDLE" ]; then
    echo "[ERROR] $APP_BUNDLE not found. Run PyInstaller first."
    exit 1
fi

echo "[DMG] Preparing staging directory: $TMP_DIR"
# Copy .app into staging area
cp -R "$APP_BUNDLE" "$TMP_DIR/${APP_NAME}.app"
# Symlink /Applications for drag-and-drop installation
ln -s /Applications "$TMP_DIR/Applications"

# Copy background image if it exists
BACKGROUND="assets/dmg_background.png"
if [ -f "$BACKGROUND" ]; then
    mkdir -p "$TMP_DIR/.background"
    cp "$BACKGROUND" "$TMP_DIR/.background/background.png"
fi

# Remove old DMG if present
[ -f "$DMG_OUT" ] && rm -f "$DMG_OUT"

echo "[DMG] Creating compressed DMG directly from staging folder..."
hdiutil create \
    -volname "$VOLUME_NAME" \
    -srcfolder "$TMP_DIR" \
    -ov \
    -format UDZO \
    -imagekey zlib-level=9 \
    "$DMG_OUT"

echo "[DMG] Cleaning up..."
rm -rf "$TMP_DIR"

echo "[DMG] Done → $DMG_OUT"
ls -lh "$DMG_OUT"
