# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Drag2Music
Build:  pyinstaller drag2music.spec --clean --noconfirm
"""
import os
import sys
import glob as _glob

block_cipher = None

# ── Locate customtkinter asset directory ────────────────────────────────────
try:
    import customtkinter as _ctk
    _ctk_assets = os.path.join(os.path.dirname(_ctk.__file__), "assets")
except ImportError:
    _ctk_assets = None

# ── Data files to bundle ─────────────────────────────────────────────────────
datas = [
    ("ffmpeg_bins", "ffmpeg_bins"),
    ("assets",      "assets"),
    ("core",        "core"),
]

if _ctk_assets and os.path.isdir(_ctk_assets):
    datas.append((_ctk_assets, os.path.join("customtkinter", "assets")))

# ── tkinterdnd2 (drag & drop) native libraries ───────────────────────────────
_dnd_hidden = []
try:
    from PyInstaller.utils.hooks import collect_data_files as _cdf
    import tkinterdnd2 as _dnd
    datas += _cdf("tkinterdnd2")
    _dnd_hidden = ["tkinterdnd2"]
except Exception:
    pass

# Also bundle any top-level JSON theme files customtkinter might look for
try:
    import customtkinter as _ctk2
    _ctk_root = os.path.dirname(_ctk2.__file__)
    for _json in _glob.glob(os.path.join(_ctk_root, "**", "*.json"), recursive=True):
        _rel = os.path.relpath(os.path.dirname(_json), os.path.dirname(_ctk_root))
        datas.append((_json, _rel))
except Exception:
    pass

# ── Analysis ─────────────────────────────────────────────────────────────────
a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # plyer platform backends
        "plyer.platforms.win.notification",
        "plyer.platforms.win.libs",
        "plyer.platforms.win.filechooser",
        "plyer.platforms.macosx.notification",
        "plyer.platforms.linux.notification",
        # yt-dlp internals
        "yt_dlp",
        "yt_dlp.networking",
        "yt_dlp.networking.common",
        "yt_dlp.networking._urllib",
        "yt_dlp.networking.impersonate",
        "yt_dlp.postprocessor",
        "yt_dlp.postprocessor.ffmpeg",
        "yt_dlp.postprocessor.embedthumbnail",
        # mutagen: imported lazily by yt-dlp for MP4/M4A/FLAC cover embedding
        "mutagen",
        "mutagen.mp4",
        "mutagen.flac",
        "mutagen.oggvorbis",
        "mutagen.oggopus",
        "mutagen.id3",
        # PIL / Pillow
        "PIL",
        "PIL._tkinter_finder",
        "PIL.Image",
        "PIL.ImageDraw",
        # customtkinter
        "customtkinter",
        "customtkinter.windows",
        "customtkinter.windows.widgets",
        # pygame
        "pygame",
        "pygame.mixer",
        "pygame.mixer_music",
        # lyrics / requests extras
        "syncedlyrics",
        "requests.packages.urllib3",
        "requests.packages.urllib3.util",
        # core package (explicit, in case auto-detection misses them)
        "core",
        "core.translations",
        "core.constants",
        "core.ui_setup",
        "core.analyzer",
        "core.audio_quality",
        "core.settings",
        "core.downloader",
        "core.lyrics",
        "core.converter",
        "core.dj_tools",
        "core.dj_pack",
        "core.stems",
        "core.music_analysis",
        "core.tagger",
        "core.dj_export",
        # stdlib extras sometimes missed
        "pkg_resources",
        "pkg_resources.py2_warn",
    ] + _dnd_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "numpy",
        "scipy",
        "IPython",
        "jupyter",
        "notebook",
        "pandas",
        "sklearn",
        "tensorflow",
        "torch",
        "cv2",
        "wx",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ── PYZ archive ───────────────────────────────────────────────────────────────
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Executable ────────────────────────────────────────────────────────────────
# icon: .ico on Windows, .icns on macOS — PyInstaller uses the right one per platform
_icon_win  = os.path.join("assets", "icon.ico")
_icon_mac  = os.path.join("assets", "icon.icns")
_icon_path = _icon_mac if sys.platform == "darwin" else _icon_win

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Drag2Music",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon_path,
)

# ── COLLECT (onedir bundle) ───────────────────────────────────────────────────
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Drag2Music",
)

# ── macOS .app BUNDLE ─────────────────────────────────────────────────────────
# This block is only active when building on macOS (PyInstaller ignores it on
# other platforms if BUNDLE is not available, but we guard it explicitly).
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Drag2Music.app",
        icon=_icon_mac,
        bundle_identifier="com.ali.drag2music",
        info_plist={
            "CFBundleDisplayName":        "Drag2Music",
            "CFBundleShortVersionString":  "3.2.0",
            "CFBundleVersion":            "3.2.0",
            "NSHighResolutionCapable":    True,
            "NSRequiresAquaSystemAppearance": False,
            "LSMinimumSystemVersion":     "10.14.0",
        },
    )
