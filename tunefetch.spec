# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for TuneFetch: Infinity Studio
Build:  pyinstaller tunefetch.spec --clean --noconfirm
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
        "core.player",
        "core.downloader",
        "core.lyrics",
        "core.converter",
        # stdlib extras sometimes missed
        "pkg_resources",
        "pkg_resources.py2_warn",
    ],
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
    name="TuneFetch",
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
    name="TuneFetch",
)

# ── macOS .app BUNDLE ─────────────────────────────────────────────────────────
# This block is only active when building on macOS (PyInstaller ignores it on
# other platforms if BUNDLE is not available, but we guard it explicitly).
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="TuneFetch.app",
        icon=_icon_mac,
        bundle_identifier="com.tunefetch.infinitystudio",
        info_plist={
            "CFBundleDisplayName":        "TuneFetch: Infinity Studio",
            "CFBundleShortVersionString":  "1.0.0",
            "CFBundleVersion":            "1.0.0",
            "NSHighResolutionCapable":    True,
            "NSRequiresAquaSystemAppearance": False,
            "LSMinimumSystemVersion":     "10.14.0",
        },
    )
