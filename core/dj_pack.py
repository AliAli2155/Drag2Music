# -*- coding: utf-8 -*-
"""
core/dj_pack.py — manager for the optional "DJ Pack".

The DJ Pack is a separate, downloadable bundle that carries the heavy ML stack
(librosa for BPM/key, audio-separator/onnxruntime for 2-stem, demucs/torch for
4-stem) as a self-contained worker executable. The base app NEVER imports any
of that — it locates the worker and calls it over a subprocess, the same way it
already shells out to ffmpeg. This keeps the base installer small and the
PyInstaller excludes (numpy/scipy/torch) intact.

Layout once installed:
    ~/.drag2music/dj-pack/
        d2m-dj-worker(.exe)        # frozen worker
        _internal/ ...             # PyInstaller onedir payload + models

Worker protocol (see dj_pack/worker.py):
    progress  -> human-readable lines on STDERR
    result    -> a single JSON object on STDOUT
    exit code -> 0 on success, non-zero on failure
"""

import os
import sys
import json
import zipfile
import threading
import subprocess

from .constants import (DJ_PACK_BASE_URL, DJ_PACK_ASSETS, DJ_WORKER_NAME,
                        DJ_PACK_VERSION)

_NO_WINDOW = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW


class DJPackNotInstalled(Exception):
    """Raised when a worker action is requested but no pack is available."""
    pass


class DJPackError(RuntimeError):
    """Raised when the worker runs but reports a failure."""
    pass


# ── locations ─────────────────────────────────────────────────────────────────

def data_dir():
    """User-writable install dir for the pack (created on demand)."""
    return os.path.join(os.path.expanduser("~"), ".drag2music", "dj-pack")


def _worker_filename():
    return DJ_WORKER_NAME + (".exe" if sys.platform == "win32" else "")


def _dev_worker():
    """When running from source, fall back to dj_pack/worker.py executed with
    the current interpreter — handy for development if the dev installed the
    pack's requirements into their venv. None in a frozen build."""
    if getattr(sys, "frozen", False):
        return None
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cand = os.path.join(here, "dj_pack", "worker.py")
    return cand if os.path.exists(cand) else None


def installed_worker_path():
    """Path to an installed frozen worker, or None. Handles both a flat layout
    and a PyInstaller onedir subfolder."""
    name = _worker_filename()
    for cand in (os.path.join(data_dir(), name),
                 os.path.join(data_dir(), DJ_WORKER_NAME, name)):
        if os.path.exists(cand):
            return cand
    return None


def is_installed():
    """True if any usable worker (installed pack or dev fallback) is present."""
    return installed_worker_path() is not None or _dev_worker() is not None


def pack_available_for_platform():
    return sys.platform in DJ_PACK_ASSETS


def download_url():
    asset = DJ_PACK_ASSETS.get(sys.platform)
    return f"{DJ_PACK_BASE_URL}/{asset}" if asset else None


# ── install (download + extract) ──────────────────────────────────────────────

def download_pack(progress=None, cancel=None):
    """Download and extract the per-platform DJ Pack.

    progress(frac, done_bytes, total_bytes) is called during download
              (frac is None when the server omits Content-Length).
    cancel()  -> truthy aborts the download (raises DJPackError).
    Returns the installed worker path. Requires `requests` (bundled).
    """
    asset = DJ_PACK_ASSETS.get(sys.platform)
    if not asset:
        raise DJPackError("DJ Pack is not available for this platform.")
    url = f"{DJ_PACK_BASE_URL}/{asset}"

    import requests
    os.makedirs(data_dir(), exist_ok=True)
    tmp_zip = os.path.join(data_dir(), asset + ".part")

    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length") or 0)
            done = 0
            with open(tmp_zip, "wb") as f:
                for chunk in r.iter_content(chunk_size=262144):
                    if cancel and cancel():
                        raise DJPackError("cancelled")
                    if not chunk:
                        continue
                    f.write(chunk)
                    done += len(chunk)
                    if progress:
                        progress((done / total) if total else None, done, total)

        # Extract alongside the worker, replacing any previous install.
        with zipfile.ZipFile(tmp_zip) as z:
            z.extractall(data_dir())
    finally:
        try:
            if os.path.exists(tmp_zip):
                os.remove(tmp_zip)
        except OSError:
            pass

    worker = installed_worker_path()
    if not worker:
        raise DJPackError("Pack downloaded but the worker was not found inside it.")
    if sys.platform != "win32":
        try:
            os.chmod(worker, 0o755)
        except OSError:
            pass
    _write_version()
    return worker


def _write_version():
    try:
        with open(os.path.join(data_dir(), "VERSION"), "w", encoding="utf-8") as f:
            f.write(DJ_PACK_VERSION)
    except OSError:
        pass


def installed_version():
    try:
        with open(os.path.join(data_dir(), "VERSION"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


# ── run the worker ────────────────────────────────────────────────────────────

def run_worker(args, on_line=None, env=None):
    """Run the worker with `args`, streaming STDERR lines to on_line(str) and
    returning the parsed JSON object printed on STDOUT.

    Raises DJPackNotInstalled if no worker is present, DJPackError on failure.
    """
    worker = installed_worker_path()
    if worker:
        cmd = [worker] + list(args)
    else:
        dev = _dev_worker()
        if not dev:
            raise DJPackNotInstalled()
        cmd = [sys.executable, dev] + list(args)

    run_env = dict(os.environ)
    if env:
        run_env.update(env)
    # Reuse the ffmpeg the app already injected, so the worker doesn't need its own.
    run_env.setdefault("FFMPEG_BINARY", os.environ.get("FFMPEG_BINARY", ""))

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
        creationflags=_NO_WINDOW, env=run_env,
    )

    err_lines = []

    def _pump_err():
        try:
            for line in proc.stderr:
                line = line.rstrip("\n")
                if not line:
                    continue
                err_lines.append(line)
                if len(err_lines) > 120:
                    del err_lines[0]
                if on_line:
                    try:
                        on_line(line)
                    except Exception:
                        pass
        except Exception:
            pass

    t = threading.Thread(target=_pump_err, daemon=True)
    t.start()
    out = proc.stdout.read() if proc.stdout else ""
    proc.wait()
    t.join(timeout=1.0)

    # Parse the result / structured error: the last JSON object on stdout.
    result = None
    for line in reversed([l for l in out.splitlines() if l.strip()]):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            result = obj
            break

    if proc.returncode != 0:
        # Surface the real cause: the worker's {"error": …}, else its last
        # "ERROR:" log line, else the exit code.
        if result and result.get("error"):
            raise DJPackError(str(result["error"]))
        for line in reversed(err_lines):
            if line.startswith("ERROR:"):
                raise DJPackError(line[6:].strip())
        tail = err_lines[-1] if err_lines else f"exit code {proc.returncode}"
        raise DJPackError(tail)

    if result is None:
        raise DJPackError("worker produced no JSON result")
    if result.get("error"):
        raise DJPackError(str(result["error"]))
    return result
