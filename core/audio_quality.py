# -*- coding: utf-8 -*-
"""
core/audio_quality.py — Quality & format consistency for Drag2Music.

Provides:
  * source_quality(info)   -> read REAL source quality from a yt-dlp info dict
                              (for the quality badge, no ffmpeg needed)
  * probe(path)            -> read actual quality of a file on disk
  * normalize(path, ...)   -> EBU R128 loudness normalization (two-pass)
                              + fixed sample rate, re-encoded to same format,
                              atomic in-place replace

All ffmpeg/ffprobe calls reuse the binary main.py already injects via
the FFMPEG_BINARY env var, with a plain "ffmpeg" fallback.
"""

import os
import re
import json
import shutil
import subprocess
import tempfile

# ── binary resolution ─────────────────────────────────────────────────────────

def _ffmpeg_bin():
    return os.environ.get("FFMPEG_BINARY") or shutil.which("ffmpeg") or "ffmpeg"


def _ffprobe_bin():
    """ffprobe usually sits next to ffmpeg; many bundles ship only ffmpeg,
    so callers must tolerate None and fall back to parsing `ffmpeg -i`."""
    ff = _ffmpeg_bin()
    base = os.path.dirname(ff)
    name = "ffprobe.exe" if ff.lower().endswith(".exe") else "ffprobe"
    cand = os.path.join(base, name) if base else name
    if os.path.exists(cand):
        return cand
    found = shutil.which("ffprobe")
    return found  # may be None


_NO_WINDOW = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW


def _run(cmd):
    """Run a command, return (returncode, stdout, stderr) as text."""
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=_NO_WINDOW,
    )
    dec = lambda b: (b or b"").decode("utf-8", "replace")
    return p.returncode, dec(p.stdout), dec(p.stderr)


# ── quality tiers / labels ──────────────────────────────────────────────────────

# Lossless first, then by effective bitrate (kbps).
def _tier(codec, kbps, lossless=False):
    codec = (codec or "").lower()
    if lossless or codec in ("flac", "alac", "pcm_s16le", "pcm_s24le", "wav"):
        return "lossless"
    if kbps is None:
        return "unknown"
    if kbps >= 256:
        return "high"
    if kbps >= 160:
        return "medium"
    return "low"


_TIER_TEXT = {
    "lossless": "Lossless",
    "high":     "High",
    "medium":   "Medium",
    "low":      "Low",
    "unknown":  "Unknown",
}


def _codec_label(codec):
    c = (codec or "").lower().split(".")[0].strip()  # "mp4a.40.2" -> "mp4a"
    return {
        "aac": "AAC", "mp4a": "AAC", "m4a": "AAC",
        "opus": "Opus", "vorbis": "Vorbis", "ogg": "Vorbis",
        "mp3": "MP3", "mp3float": "MP3", "flac": "FLAC", "alac": "ALAC",
        "pcm_s16le": "WAV", "pcm_s24le": "WAV", "pcm": "WAV",
    }.get(c, (c or "?").upper())


def _badge(codec, kbps, sample_rate, lossless=False):
    tier = _tier(codec, kbps, lossless)
    parts = [_codec_label(codec)]
    if not lossless and kbps:
        parts.append(f"{int(round(kbps))} kbps")
    if sample_rate:
        parts.append(f"{round(sample_rate / 1000, 1)} kHz")
    return {
        "tier": tier,                       # lossless | high | medium | low | unknown
        "tier_text": _TIER_TEXT[tier],
        "label": " · ".join(parts),         # e.g. "AAC · 256 kbps · 44.1 kHz"
        "codec": _codec_label(codec),
        "bitrate_kbps": int(round(kbps)) if kbps else None,
        "sample_rate": sample_rate,
    }


# ── source quality from a yt-dlp info dict (no ffmpeg) ───────────────────────────

def source_quality(info):
    """Read the *real* source quality straight from yt-dlp's info dict.
    Call this right after extract_info / inside the progress hook so the UI
    shows an honest badge instead of the user-requested format.

    Returns the same dict shape as _badge(...)."""
    info = info or {}
    # yt-dlp exposes: abr (audio bitrate kbps), acodec, asr (sample rate Hz).
    # On merged formats these may live in the chosen 'requested_downloads'.
    def pick(d):
        return (
            d.get("abr") or d.get("tbr"),
            d.get("acodec") or d.get("ext"),
            d.get("asr"),
        )

    abr, acodec, asr = pick(info)
    if not abr and info.get("requested_downloads"):
        abr, acodec, asr = pick(info["requested_downloads"][0])
    if not abr and info.get("formats"):
        # fall back to the best audio format listed
        best = max(
            (f for f in info["formats"] if f.get("acodec") not in (None, "none")),
            key=lambda f: f.get("abr") or 0,
            default={},
        )
        abr, acodec, asr = abr or best.get("abr"), acodec or best.get("acodec"), asr or best.get("asr")

    return _badge(acodec, abr, asr)


# ── probe an actual file on disk ────────────────────────────────────────────────

def probe(path):
    """Return real quality of a file. Uses ffprobe when available,
    otherwise parses `ffmpeg -i` stderr."""
    fp = _ffprobe_bin()
    if fp:
        rc, out, _ = _run([
            fp, "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_name,sample_rate,channels,bit_rate",
            "-show_entries", "format=bit_rate,duration",
            "-of", "json", path,
        ])
        if rc == 0 and out.strip():
            try:
                data = json.loads(out)
                st = (data.get("streams") or [{}])[0]
                fmt = data.get("format", {})
                codec = st.get("codec_name")
                sr = int(st["sample_rate"]) if st.get("sample_rate") else None
                br = st.get("bit_rate") or fmt.get("bit_rate")
                kbps = (int(br) / 1000) if br and br != "N/A" else None
                lossless = codec in ("flac", "alac", "pcm_s16le", "pcm_s24le")
                return _badge(codec, kbps, sr, lossless)
            except Exception:
                pass
    # fallback: parse `ffmpeg -i`
    _, _, err = _run([_ffmpeg_bin(), "-hide_banner", "-i", path])
    codec = sr = kbps = None
    m = re.search(r"Audio:\s*([a-z0-9_]+).*?(\d+)\s*Hz.*?(\d+)\s*kb/s", err, re.I | re.S)
    if m:
        codec, sr, kbps = m.group(1), int(m.group(2)), float(m.group(3))
    else:
        m2 = re.search(r"Audio:\s*([a-z0-9_]+).*?(\d+)\s*Hz", err, re.I)
        if m2:
            codec, sr = m2.group(1), int(m2.group(2))
    lossless = (codec or "") in ("flac", "alac", "pcm_s16le", "pcm_s24le")
    return _badge(codec, kbps, sr, lossless)


# ── yt-dlp injection (single-pass, in-pipeline, preserves cover art) ─────────────

def loudnorm_filter(target_lufs=-14.0, true_peak=-1.0, lra=11.0):
    return f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}"


def ytdlp_audio_filter_args(target_lufs=None, sample_rate=44100):
    """Build a yt-dlp `postprocessor_args` dict that makes the ExtractAudio
    step apply single-pass loudness normalization and/or force a sample rate.

    Runs INSIDE the existing extraction encode (one generation, no extra
    re-encode) and BEFORE EmbedThumbnail, so embedded cover art survives.

    IMPORTANT: ffmpeg's loudnorm resamples internally to 192 kHz, so an
    explicit aresample MUST follow it or every file ends up at 192 kHz.

    Returns {} when there is nothing to do."""
    args = []
    if target_lufs is not None:
        af = loudnorm_filter(target_lufs)
        if sample_rate:
            af += f",aresample={sample_rate}"   # undo loudnorm's 192 kHz output
        args += ["-af", af]
    elif sample_rate:
        args += ["-ar", str(sample_rate)]
    # key 'extractaudio' scopes args to FFmpegExtractAudio only (not EmbedThumbnail)
    return {"extractaudio": args} if args else {}


# ── loudness normalization + sample-rate standardization (two-pass, standalone) ──

# Re-encode targets per extension. Normalizing requires re-encoding, so we keep
# the original container/codec and a high bitrate to minimise generation loss.
_ENCODER = {
    ".mp3":  ["-c:a", "libmp3lame", "-q:a", "0"],          # ~245 kbps VBR
    ".m4a":  ["-c:a", "aac", "-b:a", "256k"],
    ".aac":  ["-c:a", "aac", "-b:a", "256k"],
    ".ogg":  ["-c:a", "libvorbis", "-q:a", "8"],           # ~256 kbps
    ".opus": ["-c:a", "libopus", "-b:a", "256k"],
    ".flac": ["-c:a", "flac"],                              # lossless
    ".wav":  ["-c:a", "pcm_s16le"],                         # lossless
}


def _measure_loudnorm(path, I, TP, LRA):
    """Pass 1: measure integrated loudness; returns the measured dict or None."""
    af = f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json"
    rc, _, err = _run([
        _ffmpeg_bin(), "-hide_banner", "-i", path,
        "-af", af, "-f", "null", os.devnull,
    ])
    # ffmpeg prints the JSON block at the tail of stderr
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", err, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def normalize(path, target_lufs=-14.0, true_peak=-1.0, lra=11.0,
              sample_rate=44100, two_pass=True):
    """Loudness-normalize a file to EBU R128 and force `sample_rate`,
    replacing the original in place (atomic).

    target_lufs : integrated loudness target (-14 = streaming standard).
                  Clubs sometimes push to ~-9..-10, but that compresses more.
    Returns the measured-loudness dict from pass 1 (or {} if single-pass).

    NOTE: lossy inputs are re-encoded, so this costs one generation of quality.
    For a lossless alternative, write ReplayGain tags instead (see chat notes)."""
    ext = os.path.splitext(path)[1].lower()
    enc = _ENCODER.get(ext, ["-c:a", "aac", "-b:a", "256k"])

    measured = {}
    if two_pass:
        measured = _measure_loudnorm(path, target_lufs, true_peak, lra) or {}

    if measured:
        ln = (
            f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}"
            f":measured_I={measured['input_i']}"
            f":measured_TP={measured['input_tp']}"
            f":measured_LRA={measured['input_lra']}"
            f":measured_thresh={measured['input_thresh']}"
            f":offset={measured['target_offset']}"
            f":linear=true:print_format=summary"
        )
    else:
        ln = f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}"

    af = f"{ln},aresample={sample_rate}"
    tmp_fd, tmp = tempfile.mkstemp(suffix=ext, dir=os.path.dirname(path) or None)
    os.close(tmp_fd)
    try:
        cmd = ([_ffmpeg_bin(), "-hide_banner", "-y", "-i", path,
                "-af", af, "-ar", str(sample_rate)] + enc +
               ["-map_metadata", "0", tmp])
        rc, _, err = _run(cmd)
        if rc != 0 or not os.path.exists(tmp) or os.path.getsize(tmp) == 0:
            raise RuntimeError(f"ffmpeg loudnorm failed: {err[-400:]}")
        os.replace(tmp, path)  # atomic on same filesystem
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
    return measured
