# Drag2Music — DJ Pack

The **DJ Pack** is the optional, downloadable add-on behind the app's **DJ Tools**
page. It carries the heavy AI/DSP stack so the base installer stays small:

| Feature | Engine |
|--------|--------|
| 2-stem (Vocals + Instrumental) | `audio-separator` (onnxruntime) |
| 4-stem (Drums/Bass/Vocals/Other) | `demucs` (PyTorch, CPU) |
| BPM + Key analysis | `librosa` (beat tracking + Krumhansl-Schmuckler) |

The base app **never imports** any of this. It locates the frozen worker
(`d2m-dj-worker`) under `~/.drag2music/dj-pack/` and calls it over a subprocess,
exactly like it does with `ffmpeg` — see [`core/dj_pack.py`](../core/dj_pack.py).

## How it reaches users

The app ships with no ML dependencies. The first time a user opens **DJ Tools**
(or enables *Auto BPM + key*), they see a **"Download DJ Pack"** banner. Clicking
it fetches the per-platform zip from the GitHub Release tagged `djpack-v*` and
extracts it into `~/.drag2music/dj-pack/`.

URLs / asset names / version live in [`core/constants.py`](../core/constants.py)
(`DJ_PACK_*`).

## Worker protocol

```
stdout : exactly one JSON object (the result)
stderr : human-readable progress lines (streamed into the UI status label)
exit   : 0 success, non-zero failure
```

```bash
d2m-dj-worker selftest
d2m-dj-worker analyze  --input track.mp3
d2m-dj-worker separate --input track.mp3 --engine onnx   --stems 2 --outdir ./out
d2m-dj-worker separate --input track.mp3 --engine demucs --stems 4 --outdir ./out
```

## Building locally

Build in a **dedicated** venv (keep these deps out of the app's env):

```bash
python -m venv .venv-djpack
# Windows:  .venv-djpack\Scripts\activate
# POSIX:    source .venv-djpack/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r dj_pack/requirements.txt
python dj_pack/build_djpack.py        # -> dist/Drag2Music-DJPack-<platform>.zip
```

Flags: `--reuse` (skip re-freeze), `--no-models` (don't warm caches).

## Releasing

Push a `djpack-v*` tag (or run the workflow manually). The
[`build-djpack.yml`](../.github/workflows/build-djpack.yml) workflow builds the
pack on Windows/macOS/Linux and attaches the three zips to a GitHub Release.

> Keep `DJ_PACK_VERSION` / `DJ_PACK_RELEASE_TAG` in `core/constants.py` and
> `PACK_VERSION` in `build_djpack.py` in sync with the tag you push.
