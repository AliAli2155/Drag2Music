# 🎵 TuneFetch: Infinity Studio

A powerful all-in-one desktop music application built with Python — search, stream, download, convert, and read lyrics, all from a beautiful modern UI.

---

## ✨ Features

- 🔍 **Search & Analyze** — Search YouTube by URL or keyword and instantly fetch track info, thumbnail, and duration
- ▶️ **Built-in Player** — Play previews directly in the app with playback controls, seek bar, and volume slider
- ⬇️ **Downloader** — Download audio (MP3, AAC, OGG, WAV, FLAC, OPUS) or video in multiple quality options
- 🔄 **Converter** — Convert local audio/video files to different formats with quality control
- 📝 **Lyrics** — Auto-fetches lyrics for the currently playing track
- 📚 **Library** — Keeps a history of all your downloaded tracks
- 🌙 **Themes** — Light/Dark mode + multiple accent color choices
- 🌐 **Multi-language** — UI supports multiple languages

---

## 🖥️ Requirements

- Python 3.9+
- `ffmpeg` — must be installed and available in PATH (or placed in the project folder)

---

## 📦 Installation

```bash
# 1. Clone the repository
git clone https://github.com/AliAli2155/TuneFetch.git
cd TuneFetch

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python main.py
```

---

## 🔧 Dependencies

Install all required packages with:

```bash
pip install customtkinter pillow pygame yt-dlp requests
```

| Package | Purpose |
|---|---|
| `customtkinter` | Modern UI framework |
| `Pillow` | Thumbnail image processing |
| `pygame` | Audio playback |
| `yt-dlp` | YouTube downloading & streaming |
| `requests` | Fetching thumbnails and lyrics |

---

## 📁 Project Structure

```
TuneFetch/
├── main.py                 # App entry point
├── core/
│   ├── constants.py        # Colors, format/quality maps
│   ├── translations.py     # Multi-language strings
│   ├── ui_setup.py         # UI layout and widgets
│   ├── player.py           # Playback logic
│   ├── downloader.py       # Download logic
│   ├── lyrics.py           # Lyrics fetching
│   └── converter.py        # File conversion logic
└── requirements.txt
```

---

## ⚠️ ffmpeg Setup

TuneFetch requires **ffmpeg** for audio conversion and high-quality downloads.

**Windows:**
1. Download from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. Extract and add the `bin` folder to your system PATH
   - Or place `ffmpeg.exe` directly in the TuneFetch project folder

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

---

## 📸 Screenshots

> Coming soon

---

## 📄 License

This project is private. All rights reserved.
