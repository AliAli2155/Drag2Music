# -*- coding: utf-8 -*-
"""
core/dj_export.py — Export the Drag2Music library as a DJ playlist.

Writes an Extended M3U (.m3u8, UTF-8) which every major DJ app imports
directly: Rekordbox, Serato, Traktor and VirtualDJ all read #EXTM3U /
#EXTINF playlists and pull each track's own embedded BPM/key tags from the
files themselves (see core/tagger.py).

Pure standard library — no extra dependencies, lives in the base app.
"""

import os
import datetime


def _extinf(entry):
    """Build the '#EXTINF:<secs>,<Artist - Title>' line for one entry."""
    dur = entry.get("duration")
    try:
        secs = int(dur)
    except (TypeError, ValueError):
        secs = -1
    name = entry.get("name") or "?"
    artist = entry.get("artist")
    label = f"{artist} - {name}" if artist else name
    # Strip newlines — they would corrupt the single-line EXTINF record.
    label = " ".join(str(label).splitlines())
    return f"#EXTINF:{secs},{label}"


def export_m3u8(history, out_path, only_existing=True):
    """Write `history` (list of library entries) to `out_path` as .m3u8.

    only_existing : skip entries whose file is missing on disk (default).
    Returns (written, skipped). Raises OSError if the file can't be written.
    """
    lines = ["#EXTM3U",
             f"# Drag2Music export · {datetime.datetime.now():%Y-%m-%d %H:%M}"]
    written = skipped = 0
    for entry in history:
        path = entry.get("path")
        if not path:
            skipped += 1
            continue
        if only_existing and not os.path.exists(path):
            skipped += 1
            continue
        lines.append(_extinf(entry))
        lines.append(os.path.abspath(path))
        written += 1

    # .m3u8 is UTF-8 by definition; newline="\n" keeps it portable.
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return written, skipped


def default_export_name():
    """A sensible default filename for the save dialog."""
    return f"Drag2Music_{datetime.datetime.now():%Y-%m-%d}.m3u8"
