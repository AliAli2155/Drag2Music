# Drag2Music: Infinity Studio — Build Guide

This document explains how to build native installers for Windows, macOS, and Linux from source.

---

## Prerequisites

### All Platforms
- **Python 3.11+** — [python.org](https://www.python.org/downloads/) (must be in PATH)
- All Python dependencies are installed automatically by the build scripts via `requirements.txt`

### Windows
- **Inno Setup 6** — [jrsoftware.org/isinfo.php](https://jrsoftware.org/isinfo.php)
  Install to the default location; the build script auto-detects it.
  Alternatively, add `ISCC.exe` to your system PATH.
- **Git** (optional, for cloning the repo)

### macOS
- **Xcode Command Line Tools**
  ```bash
  xcode-select --install
  ```
- **Python 3.11+** via Homebrew (recommended):
  ```bash
  brew install python@3.11
  ```
- `hdiutil` is bundled with macOS — no extra install needed.

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3 python3-pip python3-tk python3-dev \
                 libsdl2-dev libsdl2-mixer-dev \
                 fuse libfuse2 \
                 dpkg-dev
```

---

## Build Commands

### Windows — produces `dist\Drag2Music_Setup.exe`

Double-click **`build_scripts\build_windows.bat`**, or from a terminal:

```bat
build_scripts\build_windows.bat
```

The script:
1. `pip install -r requirements.txt`
2. Generates icon assets (`build_scripts/setup_assets.py`)
3. Downloads `ffmpeg-release-essentials.zip` for Windows → `ffmpeg_bins/windows/ffmpeg.exe`
4. Runs `pyinstaller drag2music.spec --clean --noconfirm` → `dist/Drag2Music/`
5. Runs `iscc installer\windows\drag2music_setup.iss` → `dist/Drag2Music_Setup.exe`

---

### macOS — produces `dist/Drag2Music.dmg`

```bash
chmod +x build_scripts/build_macos.sh
./build_scripts/build_macos.sh
```

The script:
1. `pip3 install -r requirements.txt`
2. Generates icon assets (including `.icns` via `iconutil`)
3. Downloads static ffmpeg for macOS → `ffmpeg_bins/macos/ffmpeg`
4. Runs PyInstaller → `dist/Drag2Music.app`
5. Runs `installer/macos/create_dmg.sh` → `dist/Drag2Music.dmg`

---

### Linux — produces `Drag2Music-x86_64.AppImage` **and** `drag2music_1.0.0_amd64.deb`

```bash
chmod +x build_scripts/build_linux.sh
./build_scripts/build_linux.sh
```

The script:
1. `pip3 install -r requirements.txt`
2. Generates icon assets
3. Downloads `ffmpeg-release-amd64-static.tar.xz` → `ffmpeg_bins/linux/ffmpeg`
4. Runs PyInstaller → `dist/Drag2Music/`
5. Runs `installer/linux/create_appimage.sh`:
   - Downloads `appimagetool` from GitHub AppImageKit releases
   - Builds `AppDir/` structure and produces `Drag2Music-x86_64.AppImage`
   - Builds a `.deb` package via `dpkg-deb`

---

## Manual Steps

### Download ffmpeg only (any platform)
```bash
python build_scripts/download_ffmpeg.py --platform windows   # or macos / linux / all
```

### Generate icons only
```bash
python build_scripts/setup_assets.py
```

### PyInstaller only (after ffmpeg + icons are ready)
```bash
pyinstaller drag2music.spec --clean --noconfirm
```

---

## Project Structure

```
Drag2Music/
├── main.py                          Entry point
├── core/                            Python package (player, downloader, etc.)
├── assets/
│   ├── icon.ico                     Windows icon (auto-generated from Drag2Music.ico)
│   ├── icon.icns                    macOS icon (auto-generated)
│   └── icon.png                     Linux / generic icon (512×512)
├── ffmpeg_bins/
│   ├── windows/ffmpeg.exe           Downloaded by download_ffmpeg.py
│   ├── macos/ffmpeg                 Downloaded by download_ffmpeg.py
│   └── linux/ffmpeg                 Downloaded by download_ffmpeg.py
├── build_scripts/
│   ├── build_windows.bat            Full Windows build
│   ├── build_macos.sh               Full macOS build
│   ├── build_linux.sh               Full Linux build
│   ├── download_ffmpeg.py           Downloads static ffmpeg binaries
│   └── setup_assets.py             Generates icon.ico / icon.png / icon.icns
├── installer/
│   ├── windows/drag2music_setup.iss  Inno Setup 6 installer script
│   ├── macos/create_dmg.sh          hdiutil DMG creator
│   └── linux/create_appimage.sh     AppImage + .deb builder
├── drag2music.spec                  PyInstaller spec (all platforms)
├── requirements.txt                 Python dependencies
└── README_BUILD.md                  This file
```

---

## Troubleshooting

### `ModuleNotFoundError: pygame` at runtime (frozen app)
The spec already lists `pygame` and `pygame.mixer` as `hiddenimports`. If the error persists,
add `pygame._sdl2` to `hiddenimports` in `drag2music.spec` and rebuild.

### customtkinter themes not found / blank UI
Verify that the `customtkinter/assets` directory was included. After building, check:
```
dist/Drag2Music/customtkinter/assets/themes/
```
If missing, run `pyinstaller` again — the spec's glob-based asset collection should fix it.

### `ffmpeg` not found at runtime in frozen bundle
Ensure `build_scripts/download_ffmpeg.py` ran successfully before `pyinstaller`.
Check that `dist/Drag2Music/ffmpeg_bins/<platform>/ffmpeg[.exe]` exists.
The `main.py` frozen-path injection at the top of the file sets `FFMPEG_BINARY` and prepends
the ffmpeg directory to `PATH` automatically when `sys.frozen` is `True`.

### Inno Setup compiler not found (Windows)
Set the `ISCC` environment variable before running the build script:
```bat
set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
build_scripts\build_windows.bat
```

### `hdiutil: create failed` (macOS)
Ensure enough free disk space (the writable intermediate image is ~500 MB).
Check that `dist/Drag2Music.app` was created by PyInstaller before running `create_dmg.sh`.

### AppImage fails with `FUSE not available` (Linux)
```bash
sudo apt install fuse libfuse2
# or on newer Ubuntu/Debian with fuse3:
sudo apt install libfuse2t64
```
Alternatively, run the AppImage with `--appimage-extract-and-run` flag.

### `dpkg-deb` errors on .deb build (Linux)
Ensure `dpkg` is installed:
```bash
sudo apt install dpkg
```
The build script sets correct file permissions automatically. If you still get
"suspicious ownership" errors, run the build as a non-root user.

### UPX not found (non-critical warning)
UPX is optional. If not installed, PyInstaller skips compression silently.
Install via `sudo apt install upx-ucl` (Linux) or `brew install upx` (macOS).

---

## Output Sizes (approximate)

| Platform | Format        | Size     |
|----------|---------------|----------|
| Windows  | .exe installer| ~55 MB   |
| macOS    | .dmg          | ~70 MB   |
| Linux    | .AppImage     | ~65 MB   |
| Linux    | .deb          | ~65 MB   |

*(Sizes vary depending on Python version and included libraries.)*
