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

THEME_COLORS = [
    ("Spotify Green", "#1DB954"),
    ("Sky Blue",      "#3498db"),
    ("Purple",        "#9b59b6"),
    ("Orange",        "#e67e22"),
    ("Red",           "#e74c3c"),
    ("Cyan",          "#00bcd4"),
]

# ── Renk sistemi ─────────────────────────────────────────────────────────────
# CTk tuple formatı: (açık_mod, koyu_mod)
# Bu renkleri widget'lara verince CTk mode değişimini otomatik yönetir.
C = {
    "bg":           ("#f0f2f5", "#0d0d0d"),   # pencere arka planı
    "panel":        ("#ffffff", "#161616"),   # player bar
    "card":         ("#f8f9fa", "#141414"),   # çerçeve / giriş kutuları
    "border":       ("#dee2e6", "#2a2a2a"),   # ana kenarlıklar
    "border2":      ("#e9ecef", "#242424"),   # kart kenarlıkları
    "border3":      ("#ced4da", "#282828"),   # giriş kenarlığı
    "btn_sec":      ("#e9ecef", "#222222"),   # önceki/sonraki butonlar
    "btn_sec_hov":  ("#dee2e6", "#2e2e2e"),   # hover rengi
    "btn_conv":     ("#f1f3f5", "#1a1a1a"),   # dönüştür butonu
    "btn_conv_brd": ("#dee2e6", "#2e2e2e"),   # dönüştür kenarlığı
    "tag_bg":       ("#e9ecef", "#1c1c1c"),   # format etiketi arka planı
    "dim":          ("#6c757d", "#555555"),   # soluk yazı
    "mid":          ("#495057", "#bbbbbb"),   # orta ton yazı
    "bright":       ("#212529", "#dddddd"),   # belirgin yazı
    "very_dim":     ("#ced4da", "#2e2e2e"),   # çok soluk / placeholder
    "studio":       ("#adb5bd", "#444444"),   # "Studio" logo yazısı
    "path_txt":     ("#6c757d", "#666666"),   # klasör yolu metni
    "tune":         ("#212529", "#ffffff"),   # "Tune" logo (koyu'da beyaz)
}
