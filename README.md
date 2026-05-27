# TuneFetch: Infinity Studio

A powerful all-in-one desktop music application built with Python — search, stream, download, convert, and read lyrics, all from a beautiful modern UI.

---

## Download

| Platform | File | Notes |
|----------|------|-------|
| Windows  | [TuneFetch_Setup.exe](https://github.com/AliAli2155/TuneFetch/releases/latest/download/TuneFetch_Setup.exe) | One-click installer, no Python required |
| macOS    | [TuneFetch.dmg](https://github.com/AliAli2155/TuneFetch/releases/latest/download/TuneFetch.dmg) | Drag & drop to Applications |
| Linux    | [TuneFetch-x86_64.AppImage](https://github.com/AliAli2155/TuneFetch/releases/latest/download/TuneFetch-x86_64.AppImage) | Single file, runs anywhere |
| Linux    | [tunefetch_1.0.0_amd64.deb](https://github.com/AliAli2155/TuneFetch/releases/latest/download/tunefetch_1.0.0_amd64.deb) | Debian/Ubuntu package |

> All installers are fully self-contained — Python, ffmpeg, and all dependencies are bundled. Nothing extra to install.

---

## Features

- **Search & Analyze** — Search YouTube by URL or keyword, instantly fetch track info, thumbnail, and duration
- **Built-in Player** — Play previews directly in the app with playback controls, seek bar, and volume slider
- **Downloader** — Download audio (MP3, AAC, OGG, WAV, FLAC, OPUS) or video (MP4, MKV, WEBM, AVI) in multiple quality options
- **Converter** — Convert any local audio/video file to a different format with quality control
- **Lyrics** — Auto-fetches synced lyrics for the currently playing track
- **Library** — Keeps a history of all downloaded tracks
- **Themes** — Light/Dark mode + 6 accent color choices (Spotify Green, Sky Blue, Purple, Orange, Red, Cyan)
- **Multi-language** — UI supports multiple languages

---

## Running from Source

### Requirements

- Python 3.11+
- ffmpeg (for audio conversion and yt-dlp postprocessing)

### Python Dependencies

```bash
pip install -r requirements.txt
```

| Package | Version | Purpose |
|---------|---------|---------|
| `customtkinter` | >=5.2.0 | Modern UI framework |
| `yt-dlp` | >=2024.1.1 | YouTube downloading & info extraction |
| `Pillow` | >=10.0.0 | Thumbnail image processing |
| `plyer` | >=2.1.0 | Desktop notifications |
| `pygame` | >=2.5.0 | Audio playback |
| `requests` | >=2.31.0 | HTTP requests (thumbnails, lyrics) |
| `syncedlyrics` | >=0.4.0 | Synced lyrics fetching |
| `pyinstaller` | >=6.0.0 | Packaging (build only) |

### ffmpeg Setup

**Windows** — download static build and add to PATH, or place `ffmpeg.exe` in the project folder:
- [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/)

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

### Run

```bash
git clone https://github.com/AliAli2155/TuneFetch.git
cd TuneFetch
pip install -r requirements.txt
python main.py
```

---

## Project Structure

```
TuneFetch/
├── main.py                        Entry point + frozen-bundle ffmpeg injection
├── core/
│   ├── constants.py               Colors, format/quality maps, theme colors
│   ├── translations.py            Multi-language strings
│   ├── ui_setup.py                UI layout and widgets
│   ├── player.py                  Audio playback logic
│   ├── downloader.py              yt-dlp download logic
│   ├── lyrics.py                  Lyrics auto-fetch (syncedlyrics + fallback APIs)
│   └── converter.py               ffmpeg-based file conversion
├── assets/
│   ├── icon.ico                   Windows icon
│   ├── icon.icns                  macOS icon
│   └── icon.png                   Linux icon
├── ffmpeg_bins/
│   ├── windows/ffmpeg.exe         Bundled static ffmpeg (Windows)
│   ├── macos/ffmpeg               Bundled static ffmpeg (macOS)
│   └── linux/ffmpeg               Bundled static ffmpeg (Linux)
├── build_scripts/
│   ├── build_windows.bat          Full Windows build script
│   ├── build_macos.sh             Full macOS build script
│   ├── build_linux.sh             Full Linux build script
│   ├── download_ffmpeg.py         Downloads static ffmpeg for each platform
│   └── setup_assets.py            Generates icon files
├── installer/
│   ├── windows/tunefetch_setup.iss  Inno Setup 6 installer script
│   ├── macos/create_dmg.sh          DMG creator
│   └── linux/create_appimage.sh     AppImage + .deb builder
├── .github/workflows/build.yml    GitHub Actions CI (Windows + macOS + Linux)
├── tunefetch.spec                 PyInstaller spec
└── requirements.txt               Python dependencies
```

---

## Building

See [README_BUILD.md](README_BUILD.md) for full build instructions.

**Quick start (Windows):**
```bat
build_scripts\build_windows.bat
```

**Quick start (macOS):**
```bash
chmod +x build_scripts/build_macos.sh && ./build_scripts/build_macos.sh
```

**Quick start (Linux):**
```bash
chmod +x build_scripts/build_linux.sh && ./build_scripts/build_linux.sh
```

CI builds run automatically on every push via GitHub Actions.

---

## Made by Ali A.

---

## License

This project is private. All rights reserved.
