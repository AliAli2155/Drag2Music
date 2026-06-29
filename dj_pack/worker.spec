# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the DJ Pack worker (d2m-dj-worker).

Build (in the dedicated dj_pack venv, from the repo root):
    pyinstaller dj_pack/worker.spec --clean --noconfirm

Produces dist/d2m-dj-worker/ (onedir). build_djpack.py wraps this, warms the
model caches and zips the result into Drag2Music-DJPack-<platform>.zip.
"""
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = []
hidden = []

# librosa / soundfile ship data + lazy submodules PyInstaller misses.
for pkg in ("librosa", "audio_separator", "demucs", "lazy_loader"):
    try:
        datas += collect_data_files(pkg)
        hidden += collect_submodules(pkg)
    except Exception:
        pass

hidden += [
    "sklearn.utils._typedefs",
    "sklearn.neighbors._partition_nodes",
    "soundfile",
    "audioread",
    "onnxruntime",
]

a = Analysis(
    ["worker.py"],
    pathex=["dj_pack"],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["customtkinter", "tkinterdnd2", "matplotlib", "PyQt5", "PyQt6"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="d2m-dj-worker",
    console=True,           # a CLI worker — no window
    upx=False,
)
coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    upx=False,
    name="d2m-dj-worker",
)
