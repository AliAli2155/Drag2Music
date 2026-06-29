# -*- coding: utf-8 -*-
"""
d2m-dj-worker — the heavy lifter behind Drag2Music's DJ Tools.

This program is NOT part of the base app. It is built separately (PyInstaller,
see worker.spec) and shipped as the optional "DJ Pack" so the main installer
stays small. The app finds it under ~/.drag2music/dj-pack/ and calls it over a
subprocess (see core/dj_pack.py).

Protocol
--------
  stdout : exactly one JSON object — the result
  stderr : free-form human progress lines (surfaced live in the UI)
  exit   : 0 success, non-zero failure

Sub-commands
------------
  selftest
  analyze  --input PATH
  separate --input PATH --engine {onnx,demucs} --stems {2,4} --outdir DIR
"""

import os
import sys
import json
import argparse


def _log(msg):
    """Progress line -> stderr (the app streams these to the status label)."""
    print(msg, file=sys.stderr, flush=True)


def _emit(obj):
    """Result object -> stdout (single JSON line)."""
    print(json.dumps(obj), flush=True)


_NO_WINDOW = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW


def _load_audio(path, sr, mono=False):
    """Decode any input to float32 PCM at `sr` via ffmpeg, then read with
    soundfile. This sidesteps every torchaudio / librosa codec backend issue
    (notably the TorchCodec save/load requirement in newer torchaudio).

    Returns (n,) when mono else (channels, n)."""
    import subprocess
    import tempfile
    import numpy as np
    import soundfile as sf

    ff = os.environ.get("FFMPEG_BINARY") or "ffmpeg"
    ch = "1" if mono else "2"
    tmp = tempfile.mktemp(suffix=".wav")
    cmd = [ff, "-y", "-hide_banner", "-loglevel", "error",
           "-i", path, "-ac", ch, "-ar", str(sr), "-c:a", "pcm_f32le", tmp]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   creationflags=_NO_WINDOW, check=True)
    try:
        data, _ = sf.read(tmp, dtype="float32", always_2d=True)   # (n, ch)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    if mono:
        return data.mean(axis=1)          # (n,)
    return np.ascontiguousarray(data.T)   # (ch, n)


# Camelot wheel — mirror of core/music_analysis.CAMELOT (kept in sync by hand).
_CAMELOT = {
    "B major": "1B",  "G# minor": "1A",
    "F# major": "2B", "D# minor": "2A",
    "C# major": "3B", "A# minor": "3A",
    "G# major": "4B", "F minor": "4A",
    "D# major": "5B", "C minor": "5A",
    "A# major": "6B", "G minor": "6A",
    "F major": "7B",  "D minor": "7A",
    "C major": "8B",  "A minor": "8A",
    "G major": "9B",  "E minor": "9A",
    "D major": "10B", "B minor": "10A",
    "A major": "11B", "F# minor": "11A",
    "E major": "12B", "C# minor": "12A",
}
_PITCHES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


# ── analyze: BPM + key ────────────────────────────────────────────────────────

def _analyze(path):
    import numpy as np
    import librosa

    _log("Loading audio…")
    # 22.05 kHz mono is plenty for tempo + chroma and keeps it fast.
    # Decode via ffmpeg (robust for mp3/m4a/etc.) instead of librosa's backends.
    sr = 22050
    y = _load_audio(path, sr, mono=True)

    _log("Estimating tempo…")
    tempo, _beats = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(np.atleast_1d(tempo)[0])
    # Fold obvious half/double-time results into a DJ-friendly range.
    while bpm and bpm < 70:
        bpm *= 2
    while bpm and bpm > 185:
        bpm /= 2

    _log("Estimating key…")
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    profile = chroma.mean(axis=1)

    # Krumhansl-Schmuckler key profiles.
    maj = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                    2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                      2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

    best_corr, best_key = -2.0, None
    for i in range(12):
        for prof, mode in ((maj, "major"), (minor, "minor")):
            rolled = np.roll(prof, i)
            corr = float(np.corrcoef(rolled, profile)[0, 1])
            if corr > best_corr:
                best_corr = corr
                best_key = f"{_PITCHES[i]} {mode}"

    return {
        "bpm": round(bpm, 1) if bpm else None,
        "key": best_key,
        "camelot": _CAMELOT.get(best_key) if best_key else None,
    }


# ── separate: 2-stem (ONNX / audio-separator) ─────────────────────────────────

def _separate_onnx(path, outdir):
    """Vocals + Instrumental via audio-separator (onnxruntime backend)."""
    import logging
    from audio_separator.separator import Separator

    _log("Loading 2-stem model…")
    # NOTE: log_level is a numeric logging level (audio-separator compares it
    # with `>`), not a string — passing "WARNING" raises a str/int TypeError.
    sep = Separator(output_dir=outdir, output_format="WAV",
                    log_level=logging.WARNING)
    # A solid, lightweight default vocal model; the build pre-caches it.
    sep.load_model(model_filename="UVR-MDX-NET-Inst_HQ_3.onnx")
    _log("Separating (vocals / instrumental)…")
    outputs = sep.separate(path)
    # audio-separator returns names relative to output_dir on some versions.
    files = [o if os.path.isabs(o) else os.path.join(outdir, o) for o in outputs]
    return files


# ── separate: 4-stem (Demucs / torch) ─────────────────────────────────────────

def _separate_demucs(path, outdir):
    """Drums / bass / vocals / other via Demucs (htdemucs).

    Runs the model through the low-level API and writes each stem with
    soundfile. We deliberately avoid demucs' built-in save (and the demucs CLI),
    because newer torchaudio routes audio I/O through TorchCodec, which is an
    extra native dependency we don't want to require — soundfile is already in
    the pack via librosa.
    """
    import numpy as np
    import torch
    import soundfile as sf
    from demucs.pretrained import get_model
    from demucs.apply import apply_model

    _log("Loading 4-stem model (htdemucs)…")
    model = get_model("htdemucs")
    model.eval()
    sr = model.samplerate

    _log("Decoding audio…")
    wav = _load_audio(path, sr, mono=False)        # (ch, n) float32
    wav_t = torch.from_numpy(wav)

    # Demucs expects per-input normalisation; undo it on the way out.
    ref = wav_t.mean(0)
    mean = ref.mean()
    std = ref.std() + 1e-8
    wav_n = (wav_t - mean) / std

    _log("Separating (drums / bass / vocals / other)…")
    with torch.no_grad():
        sources = apply_model(model, wav_n[None], device="cpu",
                              split=True, overlap=0.25, progress=True)[0]
    sources = sources * std + mean

    base = os.path.splitext(os.path.basename(path))[0]
    files = []
    for name, source in zip(model.sources, sources):
        out = os.path.join(outdir, f"{base} - {name}.wav")
        sf.write(out, source.t().cpu().numpy(), sr)   # (n, ch)
        files.append(out)
        _log(f"saved {name}")
    return files


# ── entry point ───────────────────────────────────────────────────────────────

def main(argv=None):
    parser = argparse.ArgumentParser(prog="d2m-dj-worker")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("selftest")

    pa = sub.add_parser("analyze")
    pa.add_argument("--input", required=True)

    ps = sub.add_parser("separate")
    ps.add_argument("--input", required=True)
    ps.add_argument("--engine", choices=["onnx", "demucs"], default="onnx")
    ps.add_argument("--stems", type=int, default=2)
    ps.add_argument("--outdir", required=True)

    args = parser.parse_args(argv)

    # Reuse the ffmpeg the app passed down, if any, so decoding works uniformly.
    ff = os.environ.get("FFMPEG_BINARY")
    if ff and os.path.dirname(ff):
        os.environ["PATH"] = os.path.dirname(ff) + os.pathsep + os.environ.get("PATH", "")

    try:
        if args.cmd == "selftest":
            info = {"ok": True}
            for mod in ("numpy", "librosa", "audio_separator", "demucs", "torch",
                        "onnxruntime"):
                try:
                    m = __import__(mod)
                    info[mod] = getattr(m, "__version__", "?")
                except Exception as e:
                    info[mod] = f"missing: {e}"
            _emit(info)
            return 0

        if args.cmd == "analyze":
            _emit(_analyze(args.input))
            return 0

        if args.cmd == "separate":
            os.makedirs(args.outdir, exist_ok=True)
            if args.engine == "demucs" or args.stems >= 4:
                files = _separate_demucs(args.input, args.outdir)
            else:
                files = _separate_onnx(args.input, args.outdir)
            _emit({"files": files})
            return 0
    except Exception as e:
        _log(f"ERROR: {e}")
        _emit({"error": str(e)})
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
