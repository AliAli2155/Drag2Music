# DJ / Producer features

New **DJ Tools** for Drag2Music, built so the base app stays lean: the heavy
AI/DSP code lives in a separate, optional **DJ Pack**, while everything light
(tagging, playlist export, the page itself) ships in the app.

## What's new

| Feature | Where | Needs DJ Pack? |
|--------|-------|:--:|
| **Stem separation** — 2-stem (vocals + instrumental) or 4-stem (drums/bass/vocals/other) | DJ Tools page | ✅ |
| **BPM + Key analysis** (Camelot codes) | DJ Tools page · auto on download | ✅ |
| **Metadata tagging** — writes BPM/key into the file for Rekordbox/Serato/Traktor | DJ Tools page · auto on download | ❌ (mutagen) |
| **M3U8 export** — library → DJ-software playlist | DJ Tools page | ❌ |
| **Auto BPM+key on download** toggle | Settings | ✅ |

## Architecture

The base app **never imports** torch / onnxruntime / librosa. The PyInstaller
`excludes` (numpy/scipy/torch) are untouched. Heavy work is delegated to a
frozen worker the same way ffmpeg is handled — a subprocess with a tiny JSON
protocol.

```
core/dj_tools.py        DJToolsMixin — page actions, install flow, auto-analyze
core/ui_setup.py        setup_djtools_tab() builds the page; nav has 'djtools'
core/dj_pack.py         finds/downloads the DJ Pack, runs the worker (subprocess)
core/stems.py           thin client -> worker `separate`
core/music_analysis.py  thin client -> worker `analyze` (+ Camelot table)
core/tagger.py          mutagen tag writer (base app)
core/dj_export.py       .m3u8 writer (base app)
core/constants.py       STEM_ENGINES, DJ_PACK_* (urls/version/paths)

dj_pack/worker.py       the heavy worker (librosa / audio-separator / demucs)
dj_pack/worker.spec     PyInstaller spec for the worker
dj_pack/build_djpack.py freeze + warm models + zip
.github/workflows/build-djpack.yml   per-platform pack build & release
```

### Worker protocol
`stdout` = one JSON result line · `stderr` = progress lines (shown live) ·
exit 0/non-zero. Commands: `selftest`, `analyze --input`,
`separate --input --engine {onnx,demucs} --stems {2,4} --outdir`.

### DJ Pack lifecycle
Installed under `~/.drag2music/dj-pack/`. Missing → the DJ Tools page shows a
**Download DJ Pack** banner that fetches the per-platform zip from the
`djpack-v*` GitHub Release. In a source checkout the app falls back to running
`dj_pack/worker.py` with the current interpreter (handy for development if you
`pip install -r dj_pack/requirements.txt`).

## Persistence

`~/.drag2music_history.json` gains `stem_engine` and `auto_analyze`; analyzed
tracks store `bpm`, `key` and `camelot` on their history entry (shown in the
Library detail line).

## Build / release notes

* Building the pack needs a **separate** venv — see [`dj_pack/README.md`](../dj_pack/README.md).
* Releasing the pack: push a `djpack-v*` tag. Keep `DJ_PACK_VERSION` /
  `DJ_PACK_RELEASE_TAG` (constants.py) and `PACK_VERSION` (build_djpack.py) in
  sync with the tag.
* **Version bump:** when cutting an app release for these features, bump
  `APP_VERSION` (constants.py) **and** the two `CFBundle*` strings in
  `drag2music.spec`, the Inno Setup `.iss`, and the `.deb` filename in
  `build.yml` together — they are matched by name in the release job.
