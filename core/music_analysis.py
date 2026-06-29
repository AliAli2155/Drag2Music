# -*- coding: utf-8 -*-
"""
core/music_analysis.py — BPM + musical-key analysis (via the DJ Pack worker).

The actual DSP (librosa beat tracking + Krumhansl-Schmuckler key estimation)
runs inside the optional DJ Pack worker, so the base app stays free of numpy /
scipy / librosa. This module is just the thin client + the Camelot lookup used
to label results in the UI.
"""

from . import dj_pack

# Open-key / Camelot wheel — maps "<Tonic> <major|minor>" to its Camelot code.
CAMELOT = {
    "B major": "1B",  "G# minor": "1A", "Ab minor": "1A",
    "F# major": "2B", "Gb major": "2B", "D# minor": "2A", "Eb minor": "2A",
    "C# major": "3B", "Db major": "3B", "A# minor": "3A", "Bb minor": "3A",
    "G# major": "4B", "Ab major": "4B", "F minor": "4A",
    "D# major": "5B", "Eb major": "5B", "C minor": "5A",
    "A# major": "6B", "Bb major": "6B", "G minor": "6A",
    "F major": "7B",  "D minor": "7A",
    "C major": "8B",  "A minor": "8A",
    "G major": "9B",  "E minor": "9A",
    "D major": "10B", "B minor": "10A",
    "A major": "11B", "F# minor": "11A", "Gb minor": "11A",
    "E major": "12B", "C# minor": "12A", "Db minor": "12A",
}


def camelot_of(key):
    """Best-effort Camelot code for a textual key, or None."""
    if not key:
        return None
    return CAMELOT.get(key.strip())


def analyze(path, on_line=None):
    """Run BPM + key analysis on `path`.

    Returns {"bpm": float|None, "key": str|None, "camelot": str|None}.
    Raises dj_pack.DJPackNotInstalled when the pack is absent and
    dj_pack.DJPackError on worker failure.
    """
    res = dj_pack.run_worker(["analyze", "--input", path], on_line=on_line) or {}
    key = res.get("key")
    return {
        "bpm":     res.get("bpm"),
        "key":     key,
        "camelot": res.get("camelot") or camelot_of(key),
    }
