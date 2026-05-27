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

echo "[DMG] Creating temporary writable image..."
TMP_DMG="dist/_tmp_tunefetch.dmg"
hdiutil create \
    -volname "$VOLUME_NAME" \
    -srcfolder "$TMP_DIR" \
    -ov \
    -format UDRW \
    -size 500m \
    "$TMP_DMG"

echo "[DMG] Mounting writable image..."
MOUNT_DIR="/Volumes/${VOLUME_NAME}"
hdiutil attach "$TMP_DMG" -readwrite -noverify -noautoopen -mountpoint "$MOUNT_DIR"

# ── Optional: Set Finder window layout via AppleScript ───────────────────────
# Uncomment the block below to set a custom window position and icon layout.
# This is cosmetic only — the installer works without it.
#
# echo "[DMG] Customising Finder window with AppleScript..."
# osascript <<APPLESCRIPT
# tell application "Finder"
#     tell disk "$VOLUME_NAME"
#         open
#         set current view of container window to icon view
#         set toolbar visible of container window to false
#         set statusbar visible of container window to false
#         set the bounds of container window to {100, 100, 700, 500}
#         set theViewOptions to the icon view options of container window
#         set arrangement of theViewOptions to not arranged
#         set icon size of theViewOptions to 128
#         set position of item "${APP_NAME}.app" of container window to {175, 200}
#         set position of item "Applications"    of container window to {475, 200}
#         close
#         open
#         update without registering applications
#         delay 2
#     end tell
# end tell
# APPLESCRIPT
# ─────────────────────────────────────────────────────────────────────────────

echo "[DMG] Detaching writable image..."
hdiutil detach "$MOUNT_DIR" -force

echo "[DMG] Converting to compressed read-only DMG..."
hdiutil convert "$TMP_DMG" \
    -format UDZO \
    -imagekey zlib-level=9 \
    -o "$DMG_OUT"

echo "[DMG] Cleaning up..."
rm -f "$TMP_DMG"
rm -rf "$TMP_DIR"

echo "[DMG] Done → $DMG_OUT"
ls -lh "$DMG_OUT"
