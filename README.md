<div align="center">

# TuneFetch: Infinity Studio

**Search · Download · Convert · Lyrics — all in one beautiful desktop app**

[![Build](https://github.com/AliAli2155/TuneFetch/actions/workflows/build.yml/badge.svg)](https://github.com/AliAli2155/TuneFetch/actions/workflows/build.yml)
[![License](https://img.shields.io/badge/license-All%20Rights%20Reserved-red)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](#download)

</div>

---

## Download

| Platform | Installer | Notes |
|----------|-----------|-------|
| 🪟 Windows | [TuneFetch_Setup.exe](https://github.com/AliAli2155/TuneFetch/releases/latest/download/TuneFetch_Setup.exe) | One-click installer — no Python required |
| 🍎 macOS | [TuneFetch.dmg](https://github.com/AliAli2155/TuneFetch/releases/latest/download/TuneFetch.dmg) | Drag & drop to Applications |
| 🐧 Linux | [TuneFetch-x86_64.AppImage](https://github.com/AliAli2155/TuneFetch/releases/latest/download/TuneFetch-x86_64.AppImage) | Single file, runs on any distro |
| 🐧 Linux | [tunefetch_1.0.0_amd64.deb](https://github.com/AliAli2155/TuneFetch/releases/latest/download/tunefetch_1.0.0_amd64.deb) | Debian / Ubuntu package |

> **Fully self-contained** — Python runtime, ffmpeg, and all libraries are bundled inside. Nothing else to install.

---

## Features

| | |
|---|---|
| 🔍 **Search & Analyze** | Search YouTube or SoundCloud by URL or keyword — instantly loads title, thumbnail, and source badge |
| ⬇️ **Downloader** | Download audio (MP3, AAC, OGG, WAV, FLAC, OPUS) or video (MP4, MKV, WEBM, AVI) with quality selection |
| 📋 **Playlist Support** | Paste any YouTube playlist or SoundCloud set → queue all tracks in one click |
| 🔄 **File Converter** | Convert local audio/video files to any format using bundled ffmpeg |
| 📜 **Auto Lyrics** | Automatically fetches lyrics from multiple sources (syncedlyrics, lyrist, lrclib) |
| 📚 **Library** | Full download history with format tags and timestamps |
| 🎨 **Themes** | 6 accent colors + Dark / Light mode |
| 🌐 **11 Languages** | English, Türkçe, Español, Français, Deutsch, Português, Italiano, Русский, Ελληνικά, 日本語, 中文 |
| 🔗 **Drag & Drop** | Drag a URL directly onto the search bar |

---

## Screenshots

> Coming soon

---

## Running from Source

### Requirements

- Python 3.11+
- ffmpeg in PATH **or** placed in the project root (auto-detected)

### Install & Run

```bash
git clone https://github.com/AliAli2155/TuneFetch.git
cd TuneFetch
pip install -r requirements.txt
python main.py
```

### Python Dependencies

| Package | Purpose |
|---------|---------|
| `customtkinter` | Modern UI framework |
| `yt-dlp` | YouTube / SoundCloud downloading & info extraction |
| `Pillow` | Thumbnail image processing |
| `plyer` | Desktop notifications |
| `requests` | HTTP (thumbnails, lyrics APIs) |
| `syncedlyrics` | Synced lyrics fetching |
| `pyinstaller` | Packaging (build only) |

### ffmpeg

**Windows** — place `ffmpeg.exe` in the project folder, or download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)

**macOS** — `brew install ffmpeg`

**Linux** — `sudo apt install ffmpeg`

---

## Project Structure

```
TuneFetch/
├── main.py                    Boot + __init__ (~90 lines)
├── core/
│   ├── analyzer.py            Video analysis, playlist, thumbnail, drag-drop
│   ├── downloader.py          Download queue, progress hooks, yt-dlp opts
│   ├── settings.py            Settings popup, theme, language, data I/O, library UI
│   ├── ui_setup.py            Widget creation and layout
│   ├── converter.py           Local file conversion (ffmpeg)
│   ├── lyrics.py              Auto lyrics (syncedlyrics + 3 fallback APIs)
│   ├── constants.py           Colors, format maps, theme palette
│   └── translations.py        11-language string table
├── assets/                    App icons (ico / icns / png)
├── ffmpeg_bins/               Static ffmpeg binaries (downloaded at build time)
├── build_scripts/             Platform build scripts + ffmpeg downloader
├── installer/                 Inno Setup / DMG / AppImage scripts
├── .github/workflows/         CI: builds all 3 platforms on every push
├── tunefetch.spec             PyInstaller spec
└── requirements.txt
```

---

## Building

All three platforms build automatically via **GitHub Actions** on every push.  
For local builds see [README_BUILD.md](README_BUILD.md).

```bat
# Windows
build_scripts\build_windows.bat

# macOS
chmod +x build_scripts/build_macos.sh && ./build_scripts/build_macos.sh

# Linux
chmod +x build_scripts/build_linux.sh && ./build_scripts/build_linux.sh
```

---

## Made by Ali A.

---

*All rights reserved.*
