# -*- coding: utf-8 -*-
"""
core/stems.py — vocal/instrumental (and 4-stem) separation via the DJ Pack.

Thin client only. The separation models (audio-separator/onnxruntime for the
2-stem engine, demucs/torch for the 4-stem engine) live inside the optional DJ
Pack worker; the base app never imports them.
"""

import os

from . import dj_pack


def separate(path, engine="onnx", n_stems=2, outdir=None, on_line=None):
    """Split `path` into stems.

    engine  : "onnx" (2-stem vocals+instrumental) or "demucs" (4-stem).
    n_stems : 2 or 4.
    outdir  : where to write the stems (defaults to the source folder).
    on_line : called with each progress line from the worker.

    Returns the list of written stem file paths.
    Raises dj_pack.DJPackNotInstalled / dj_pack.DJPackError.
    """
    if not outdir:
        outdir = os.path.dirname(os.path.abspath(path))
    args = ["separate", "--input", path,
            "--engine", engine, "--stems", str(n_stems),
            "--outdir", outdir]
    res = dj_pack.run_worker(args, on_line=on_line) or {}
    return res.get("files", [])
