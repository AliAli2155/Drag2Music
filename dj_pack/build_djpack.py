# -*- coding: utf-8 -*-
"""
build_djpack.py — build the optional DJ Pack for the current platform.

Steps:
  1. Freeze worker.py with PyInstaller (onedir -> dist/d2m-dj-worker/).
  2. Warm the model caches so the pack works fully offline (best-effort).
  3. Stamp a VERSION file (read by core/dj_pack.installed_version()).
  4. Zip dist/d2m-dj-worker/ -> dist/Drag2Music-DJPack-<platform>.zip

Run from the repo root inside the dedicated dj_pack venv:
    python dj_pack/build_djpack.py
"""

import os
import sys
import shutil
import zipfile
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist", "d2m-dj-worker")

PLATFORM = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")

# Keep in sync with core/constants.DJ_PACK_VERSION
PACK_VERSION = "1.0.0"


def _run(cmd):
    print("›", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)


def freeze():
    _run([sys.executable, "-m", "PyInstaller",
          os.path.join("dj_pack", "worker.spec"), "--clean", "--noconfirm"])


def warm_models():
    """Trigger a one-off load so model files land in the bundled caches.
    Failures here are non-fatal — the worker will fetch on first real use."""
    try:
        import logging
        from audio_separator.separator import Separator
        print("Warming 2-stem model…")
        Separator(output_dir=os.path.join(ROOT, "dist"),
                  log_level=logging.ERROR).load_model(
            model_filename="UVR-MDX-NET-Inst_HQ_3.onnx")
    except Exception as e:
        print(f"  (skipped 2-stem warm: {e})")
    try:
        print("Warming 4-stem model (htdemucs)…")
        from demucs.pretrained import get_model
        get_model("htdemucs")
    except Exception as e:
        print(f"  (skipped 4-stem warm: {e})")


def stamp_version():
    with open(os.path.join(DIST, "VERSION"), "w", encoding="utf-8") as f:
        f.write(PACK_VERSION)


def make_zip():
    out = os.path.join(ROOT, "dist", f"Drag2Music-DJPack-{PLATFORM}.zip")
    if os.path.exists(out):
        os.remove(out)
    print(f"Zipping -> {out}")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _dirs, files in os.walk(DIST):
            for fn in files:
                full = os.path.join(base, fn)
                # Store paths relative to the d2m-dj-worker folder so the app
                # extracts ~/.drag2music/dj-pack/d2m-dj-worker/...
                rel = os.path.relpath(full, os.path.dirname(DIST))
                z.write(full, rel)
    print("Done:", out, f"({os.path.getsize(out) / 1e6:.0f} MB)")
    return out


if __name__ == "__main__":
    if not os.path.isdir(DIST):
        freeze()
    elif "--reuse" not in sys.argv:
        freeze()
    if "--no-models" not in sys.argv:
        warm_models()
    stamp_version()
    make_zip()
