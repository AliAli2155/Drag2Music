import sys

# ── App version (keep in sync with installer scripts) ────────────────────────
APP_VERSION = "3.1.0"

# ── Platform-native UI font ──────────────────────────────────────────────────
# Tk silently falls back to a default if the family is missing, so this is safe.
if sys.platform == "win32":
    FONT = "Segoe UI"
elif sys.platform == "darwin":
    FONT = "Helvetica Neue"
else:
    FONT = "DejaVu Sans"

FORMAT_QUALITIES = {
    "🎵 MP3":  ["320 kbps", "256 kbps", "192 kbps", "128 kbps", "96 kbps", "64 kbps"],
    "🎵 AAC":  ["256 kbps", "192 kbps", "128 kbps", "96 kbps"],
    "🎵 OGG":  ["320 kbps", "256 kbps", "192 kbps", "128 kbps"],
    "🎵 OPUS": ["320 kbps", "192 kbps", "128 kbps", "64 kbps"],
    "🎵 WAV":  ["48kHz PCM (Lossless)", "44.1kHz PCM (Lossless)"],
    "🎵 FLAC": ["Lossless (Best)", "Lossless (CD Quality)"],
    "🎬 MP4":  ["4K (2160p)", "1080p FHD", "720p HD", "480p SD", "360p"],
    "🎬 MKV":  ["4K (2160p)", "1080p FHD", "720p HD", "480p SD"],
    "🎬 WEBM": ["1080p FHD", "720p HD", "480p SD", "360p"],
    "🎬 AVI":  ["1080p FHD", "720p HD", "480p SD"],
}

THUMBNAIL_EMBED_FMTS = {"MP3", "AAC", "OGG", "OPUS", "FLAC", "MP4", "MKV"}

# Audio formats eligible for loudness normalization / sample-rate standardization
AUDIO_FMTS = {"MP3", "AAC", "OGG", "OPUS", "WAV", "FLAC"}

# Loudness presets (EBU R128 integrated target in LUFS). None = leave untouched.
LOUDNESS_PRESETS = {
    "Off":                   None,
    "Streaming (-14 LUFS)":  -14.0,
    "Club / Loud (-9 LUFS)": -9.0,
}

# Standard sample rate for a DJ-friendly, consistent library
TARGET_SAMPLE_RATE = 44100

THEME_COLORS = [
    ("Spotify Green", "#1DB954"),
    ("Sky Blue",      "#3498db"),
    ("Purple",        "#9b59b6"),
    ("Orange",        "#e67e22"),
    ("Red",           "#e74c3c"),
    ("Cyan",          "#00bcd4"),
]

# ── Color system ─────────────────────────────────────────────────────────────
# CTk tuple format: (light_mode, dark_mode)
# Passing these tuples to widgets lets CTk auto-update colors on mode change.
C = {
    "bg":           ("#f0f2f5", "#0d0d0d"),   # window background
    "panel":        ("#ffffff", "#161616"),   # sidebar / popups
    "card":         ("#f8f9fa", "#141414"),   # frames / input fields
    "border":       ("#dee2e6", "#2a2a2a"),   # main borders
    "border2":      ("#e9ecef", "#242424"),   # card borders
    "border3":      ("#ced4da", "#282828"),   # entry border
    "btn_sec":      ("#e9ecef", "#222222"),   # secondary buttons
    "btn_sec_hov":  ("#dee2e6", "#2e2e2e"),   # hover color
    "btn_conv":     ("#f1f3f5", "#1a1a1a"),   # converter button
    "btn_conv_brd": ("#dee2e6", "#2e2e2e"),   # converter button border
    "tag_bg":       ("#e9ecef", "#1c1c1c"),   # format tag background
    "dim":          ("#6c757d", "#555555"),   # muted text
    "mid":          ("#495057", "#bbbbbb"),   # medium text
    "bright":       ("#212529", "#dddddd"),   # prominent text
    "very_dim":     ("#ced4da", "#2e2e2e"),   # very muted / placeholder
    "path_txt":     ("#6c757d", "#666666"),   # folder path text
    "tune":         ("#212529", "#ffffff"),   # "Drag2" logo (white in dark)
    "nav_hover":    ("#e9ecef", "#1e1e1e"),   # sidebar nav hover
    "error":        "#E5484D",                # error / cancel accent
    "error_hover":  "#C62828",
}
