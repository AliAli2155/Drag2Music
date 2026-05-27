#!/usr/bin/env python3
"""
Download static ffmpeg binaries for each target platform.
Usage:
    python download_ffmpeg.py --platform windows
    python download_ffmpeg.py --platform macos
    python download_ffmpeg.py --platform linux
    python download_ffmpeg.py --platform all
"""
import argparse
import os
import sys
import stat
import time
import zipfile
import tarfile
import urllib.request
import urllib.error

# Root of the project (parent of build_scripts/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FFMPEG_URLS = {
    "windows": "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    "macos":   "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip",
    "linux":   "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz",
}

DEST_DIRS = {
    "windows": os.path.join(PROJECT_ROOT, "ffmpeg_bins", "windows"),
    "macos":   os.path.join(PROJECT_ROOT, "ffmpeg_bins", "macos"),
    "linux":   os.path.join(PROJECT_ROOT, "ffmpeg_bins", "linux"),
}

BINARY_NAMES = {
    "windows": "ffmpeg.exe",
    "macos":   "ffmpeg",
    "linux":   "ffmpeg",
}


def _progress_hook(downloaded: int, total: int) -> None:
    if total > 0:
        pct = min(100, int(downloaded * 100 / total))
        mb_done = downloaded / 1_048_576
        mb_total = total / 1_048_576
        bar_filled = pct // 5
        bar = "#" * bar_filled + "-" * (20 - bar_filled)
        print(f"\r  [{bar}] {pct:3d}%  {mb_done:.1f}/{mb_total:.1f} MB  ", end="", flush=True)
    else:
        mb_done = downloaded / 1_048_576
        print(f"\r  Downloaded {mb_done:.1f} MB  ", end="", flush=True)


def download_with_retry(url: str, dest_path: str, max_retries: int = 3, timeout: int = 180) -> None:
    """Download *url* to *dest_path* with exponential-backoff retry."""
    headers = {"User-Agent": "TuneFetch-Installer/1.0 (+https://github.com/AliAli2155/TuneFetch)"}
    for attempt in range(1, max_retries + 1):
        try:
            print(f"  Attempt {attempt}/{max_retries} -> {url}")
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                with open(dest_path, "wb") as fh:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        fh.write(chunk)
                        downloaded += len(chunk)
                        _progress_hook(downloaded, total)
            print()  # newline after progress bar
            return
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            print(f"\n  Download error: {exc}")
            if attempt < max_retries:
                wait = 2 ** attempt
                print(f"  Waiting {wait}s before retry...")
                time.sleep(wait)
            else:
                raise RuntimeError(
                    f"Failed to download {url} after {max_retries} attempts: {exc}"
                ) from exc


def _set_executable(path: str) -> None:
    mode = os.stat(path).st_mode
    os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def extract_windows_ffmpeg(archive_path: str, dest_dir: str) -> None:
    print("  Extracting ffmpeg.exe from zip archive...")
    dest_file = os.path.join(dest_dir, "ffmpeg.exe")
    with zipfile.ZipFile(archive_path, "r") as zf:
        # gyan.dev archives have layout: ffmpeg-X.X-essentials_build/bin/ffmpeg.exe
        candidate = None
        for name in zf.namelist():
            parts = name.replace("\\", "/").split("/")
            if parts[-1].lower() == "ffmpeg.exe":
                # Prefer the one inside bin/
                if candidate is None or "/bin/" in name.lower():
                    candidate = name
        if candidate is None:
            raise RuntimeError("ffmpeg.exe not found inside the zip archive")
        with zf.open(candidate) as src, open(dest_file, "wb") as dst:
            while True:
                data = src.read(65536)
                if not data:
                    break
                dst.write(data)
    print(f"  Saved -> {dest_file}")


def extract_macos_ffmpeg(archive_path: str, dest_dir: str) -> None:
    print("  Extracting ffmpeg from zip archive...")
    dest_file = os.path.join(dest_dir, "ffmpeg")
    with zipfile.ZipFile(archive_path, "r") as zf:
        candidate = None
        for name in zf.namelist():
            if os.path.basename(name) == "ffmpeg" and not name.endswith("/"):
                candidate = name
                break
        if candidate is None:
            raise RuntimeError("ffmpeg binary not found inside the zip archive")
        with zf.open(candidate) as src, open(dest_file, "wb") as dst:
            while True:
                data = src.read(65536)
                if not data:
                    break
                dst.write(data)
    _set_executable(dest_file)
    print(f"  Saved -> {dest_file}")


def extract_linux_ffmpeg(archive_path: str, dest_dir: str) -> None:
    print("  Extracting ffmpeg from tar.xz archive...")
    # Validate file header before attempting extraction
    with open(archive_path, "rb") as fh:
        magic = fh.read(6)
    if magic[:2] == b'\xfd7' or magic[:6] == b'\xfd7zXZ\x00':
        mode = "r:xz"
    elif magic[:3] == b'\x1f\x8b\x08':
        mode = "r:gz"
    elif magic[:5] == b'BZh91':
        mode = "r:bz2"
    else:
        raise RuntimeError(
            f"Downloaded file does not look like a tar archive (magic={magic.hex()}). "
            "The server may have returned an error page instead of the binary."
        )

    dest_file = os.path.join(dest_dir, "ffmpeg")
    with tarfile.open(archive_path, mode) as tf:
        # BtbN layout: ffmpeg-master-.../bin/ffmpeg
        # johnvansickle layout: ffmpeg-*-static/ffmpeg
        candidate = None
        for member in tf.getmembers():
            bname = os.path.basename(member.name)
            if bname == "ffmpeg" and member.isfile():
                # prefer the one in a bin/ subdirectory (BtbN)
                if candidate is None or "/bin/" in member.name:
                    candidate = member
        if candidate is None:
            raise RuntimeError("ffmpeg binary not found inside the tar archive")
        fobj = tf.extractfile(candidate)
        if fobj is None:
            raise RuntimeError("Could not open ffmpeg entry in archive")
        with open(dest_file, "wb") as dst:
            while True:
                data = fobj.read(65536)
                if not data:
                    break
                dst.write(data)
    _set_executable(dest_file)
    print(f"  Saved -> {dest_file}")


def download_platform(platform: str) -> None:
    if platform not in FFMPEG_URLS:
        raise ValueError(f"Unknown platform '{platform}'. Choose: windows, macos, linux, all")

    dest_dir = DEST_DIRS[platform]
    os.makedirs(dest_dir, exist_ok=True)

    binary_name = BINARY_NAMES[platform]
    binary_path = os.path.join(dest_dir, binary_name)

    if os.path.exists(binary_path):
        size_mb = os.path.getsize(binary_path) / 1_048_576
        print(f"[{platform.upper()}] ffmpeg already present ({size_mb:.1f} MB) — skipping.")
        return

    print(f"\n[{platform.upper()}] Downloading ffmpeg static binary...")
    ext = ".zip" if platform in ("windows", "macos") else ".tar.xz"
    tmp_path = os.path.join(dest_dir, f"_ffmpeg_download_tmp{ext}")

    try:
        download_with_retry(FFMPEG_URLS[platform], tmp_path)

        print(f"  Download complete, extracting...")
        if platform == "windows":
            extract_windows_ffmpeg(tmp_path, dest_dir)
        elif platform == "macos":
            extract_macos_ffmpeg(tmp_path, dest_dir)
        elif platform == "linux":
            extract_linux_ffmpeg(tmp_path, dest_dir)

        size_mb = os.path.getsize(binary_path) / 1_048_576
        print(f"[{platform.upper()}] Done! ffmpeg ({size_mb:.1f} MB) ready at {binary_path}")
    except Exception as exc:
        print(f"[{platform.upper()}] ERROR: {exc}", file=sys.stderr)
        raise
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _detect_current_platform() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download static ffmpeg binaries for TuneFetch packaging"
    )
    parser.add_argument(
        "--platform",
        default=_detect_current_platform(),
        choices=["windows", "macos", "linux", "all"],
        help="Target platform (default: auto-detect current OS)",
    )
    args = parser.parse_args()

    if args.platform == "all":
        for p in ["windows", "macos", "linux"]:
            download_platform(p)
    else:
        download_platform(args.platform)

    print("\nAll done.")


if __name__ == "__main__":
    main()
