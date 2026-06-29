#!/usr/bin/env bash
# Drag2Music — Linux AppImage + .deb builder
# Called by build_scripts/build_linux.sh after PyInstaller completes.
# Requirements:
#   - fuse / libfuse2  (sudo apt install fuse libfuse2)
#   - dpkg-deb         (sudo apt install dpkg)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

APP_NAME="Drag2Music"
APP_VERSION="3.2.0"
ARCH="x86_64"
DIST_DIR="dist/${APP_NAME}"
APPIMAGE_OUT="${APP_NAME}-${ARCH}.AppImage"
DEB_NAME="drag2music_${APP_VERSION}_amd64"

# ============================================================
#  PART A — AppImage
# ============================================================
echo "============================================================"
echo " Building AppImage"
echo "============================================================"

if [ ! -d "$DIST_DIR" ]; then
    echo "[ERROR] $DIST_DIR not found. Run PyInstaller first."
    exit 1
fi

# ── Download appimagetool ────────────────────────────────────────────────────
APPIMAGETOOL="./appimagetool-x86_64.AppImage"
if [ ! -f "$APPIMAGETOOL" ]; then
    echo "[AppImage] Downloading appimagetool..."
    APPIMAGETOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    for attempt in 1 2 3; do
        echo "  Attempt $attempt/3..."
        if curl -fsSL --retry 3 --retry-delay 2 -o "$APPIMAGETOOL" "$APPIMAGETOOL_URL"; then
            break
        fi
        echo "  Download failed, retrying..."
        sleep $((attempt * 2))
    done
    chmod +x "$APPIMAGETOOL"
    echo "[AppImage] appimagetool downloaded."
fi

# ── Build AppDir ─────────────────────────────────────────────────────────────
APPDIR="AppDir"
echo "[AppImage] Building AppDir structure..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin/${APP_NAME}"

# Copy PyInstaller output
cp -r "$DIST_DIR/." "$APPDIR/usr/bin/${APP_NAME}/"

# AppRun entry-point script
cat > "$APPDIR/AppRun" <<'APPRUN'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "${0}")")"
export LD_LIBRARY_PATH="${HERE}/usr/bin/Drag2Music:${LD_LIBRARY_PATH:-}"
export PATH="${HERE}/usr/bin/Drag2Music:${PATH}"
exec "${HERE}/usr/bin/Drag2Music/Drag2Music" "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

# .desktop file (required by AppImage spec)
cat > "$APPDIR/drag2music.desktop" <<DESKTOP
[Desktop Entry]
Name=Drag2Music
Comment=Download, convert and play music from YouTube
Exec=Drag2Music
Icon=icon
Terminal=false
Type=Application
Categories=Audio;Music;Network;
Keywords=music;youtube;download;convert;lyrics;
DESKTOP

# Icon
if [ -f "assets/icon.png" ]; then
    cp "assets/icon.png" "$APPDIR/icon.png"
else
    echo "[AppImage] WARNING: assets/icon.png not found — AppImage will have no icon."
    # Create 1x1 placeholder so appimagetool doesn't fail
    python3 -c "
from PIL import Image
Image.new('RGBA', (256,256), (29,185,84,255)).save('$APPDIR/icon.png')
" 2>/dev/null || touch "$APPDIR/icon.png"
fi

# ── Run appimagetool ─────────────────────────────────────────────────────────
echo "[AppImage] Running appimagetool..."
ARCH="${ARCH}" "$APPIMAGETOOL" "$APPDIR" "$APPIMAGE_OUT"

echo "[AppImage] Done → $APPIMAGE_OUT"
ls -lh "$APPIMAGE_OUT"


# ============================================================
#  PART B — .deb package
# ============================================================
echo
echo "============================================================"
echo " Building .deb package"
echo "============================================================"

DEB_ROOT="${DEB_NAME}"
rm -rf "$DEB_ROOT"

# Standard deb directory layout
DEB_CONTROL="${DEB_ROOT}/DEBIAN"
DEB_LIB="${DEB_ROOT}/usr/lib/drag2music"
DEB_SHARE="${DEB_ROOT}/usr/share/applications"
DEB_PIXMAPS="${DEB_ROOT}/usr/share/pixmaps"
DEB_BIN="${DEB_ROOT}/usr/bin"
mkdir -p "$DEB_CONTROL" "$DEB_LIB" "$DEB_SHARE" "$DEB_PIXMAPS" "$DEB_BIN"

# Copy app files
cp -r "$DIST_DIR/." "$DEB_LIB/"

# Launcher wrapper in /usr/bin so it's on PATH
cat > "${DEB_BIN}/drag2music" <<'LAUNCHER'
#!/usr/bin/env bash
exec /usr/lib/drag2music/Drag2Music "$@"
LAUNCHER
chmod +x "${DEB_BIN}/drag2music"

# .desktop file
cat > "${DEB_SHARE}/drag2music.desktop" <<DESKTOP
[Desktop Entry]
Name=Drag2Music
GenericName=Music Downloader
Comment=Download, convert and play music from YouTube
Exec=/usr/lib/drag2music/Drag2Music
Icon=drag2music
Terminal=false
Type=Application
Categories=Audio;Music;Network;
Keywords=music;youtube;download;convert;lyrics;
StartupNotify=true
DESKTOP

# App icon
if [ -f "assets/icon.png" ]; then
    cp "assets/icon.png" "${DEB_PIXMAPS}/drag2music.png"
fi

# DEBIAN/control
INSTALLED_SIZE="$(du -sk "$DEB_LIB" | cut -f1)"
cat > "${DEB_CONTROL}/control" <<CONTROL
Package: drag2music
Version: ${APP_VERSION}
Architecture: amd64
Maintainer: Drag2Music <23022006ali@gmail.com>
Installed-Size: ${INSTALLED_SIZE}
Depends: libc6 (>= 2.17), libfuse2 | libfuse3, python3-tk
Homepage: https://github.com/AliAli2155/Drag2Music
Section: sound
Priority: optional
Description: Drag2Music
 Download, convert and play music from YouTube.
 Supports MP3, AAC, OGG, OPUS, WAV, FLAC, MP4, MKV video formats.
 Includes built-in music player, lyrics viewer, and format converter.
CONTROL

# DEBIAN/postinst — update desktop database after install
cat > "${DEB_CONTROL}/postinst" <<'POSTINST'
#!/bin/sh
set -e
update-desktop-database /usr/share/applications 2>/dev/null || true
gtk-update-icon-cache /usr/share/pixmaps 2>/dev/null || true
exit 0
POSTINST
chmod 0755 "${DEB_CONTROL}/postinst"

# DEBIAN/postrm — update desktop database after removal
cat > "${DEB_CONTROL}/postrm" <<'POSTRM'
#!/bin/sh
set -e
update-desktop-database /usr/share/applications 2>/dev/null || true
exit 0
POSTRM
chmod 0755 "${DEB_CONTROL}/postrm"

# Fix permissions (dpkg requires 0755 on DEBIAN scripts, 0644 on data files)
find "$DEB_ROOT" -type f -not -path "*/DEBIAN/*" -exec chmod 644 {} \;
find "$DEB_ROOT" -type d -exec chmod 755 {} \;
chmod 0755 "${DEB_BIN}/drag2music"
chmod 0755 "${DEB_LIB}/Drag2Music"

echo "[deb] Running dpkg-deb..."
dpkg-deb --build --root-owner-group "$DEB_ROOT"

DEB_FILE="${DEB_NAME}.deb"
echo "[deb] Done → $DEB_FILE"
ls -lh "$DEB_FILE"

# Clean up staging tree
rm -rf "$DEB_ROOT"
rm -rf "$APPDIR"

echo
echo "Outputs:"
echo "  AppImage : $APPIMAGE_OUT"
echo "  Deb pkg  : $DEB_FILE"
