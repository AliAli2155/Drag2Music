# -*- coding: utf-8 -*-
"""
core/tagger.py — DJ metadata tagging for Drag2Music.

Writes BPM, musical key (with Camelot code), genre and the usual
title/artist/comment fields into audio files so they import cleanly into
Rekordbox / Serato / Traktor / VirtualDJ.

Only `mutagen` is used (already a Drag2Music dependency), so this lives in the
base app — no heavy ML stack required. Each format keeps its own tag scheme:

  * MP3      -> ID3v2 frames  (TBPM, TKEY, TCON, COMM, TIT2, TPE1)
  * FLAC/OGG -> Vorbis comments (BPM, INITIALKEY/KEY, GENRE, ...)
  * MP4/M4A  -> iTunes atoms  (tmpo for BPM, freeform '----' for key)

We deliberately write the key to *several* plausible fields per container,
because the DJ apps disagree on which one they read (Serato favours
INITIALKEY, Traktor/Rekordbox read TKEY, etc.).
"""

import os


def write_tags(path, *, bpm=None, key=None, camelot=None, genre=None,
               title=None, artist=None, comment=None):
    """Write the given DJ tags into `path` in place. Unknown/None fields are
    skipped. Returns True on success, False if the format is unsupported or
    mutagen raised. Never raises — tagging is best-effort."""
    if not path or not os.path.exists(path):
        return False
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".mp3":
            return _tag_mp3(path, bpm, key, camelot, genre, title, artist, comment)
        if ext in (".flac", ".ogg", ".opus"):
            return _tag_vorbis(path, ext, bpm, key, camelot, genre, title, artist, comment)
        if ext in (".m4a", ".mp4", ".aac"):
            return _tag_mp4(path, bpm, key, camelot, genre, title, artist, comment)
    except Exception as e:
        print(f"[tagger] {os.path.basename(path)}: {e}")
    return False


def _key_comment(key, camelot, comment):
    """Fold the Camelot code into the comment so apps that ignore key tags
    still surface it (e.g. '8A - A minor | <user comment>')."""
    bits = []
    if camelot and key:
        bits.append(f"{camelot} - {key}")
    elif camelot:
        bits.append(str(camelot))
    elif key:
        bits.append(str(key))
    if comment:
        bits.append(str(comment))
    return " | ".join(bits) if bits else None


# ── MP3 / ID3 ─────────────────────────────────────────────────────────────────

def _tag_mp3(path, bpm, key, camelot, genre, title, artist, comment):
    from mutagen.id3 import (ID3, TBPM, TKEY, TCON, TIT2, TPE1, COMM, error as ID3Error)
    try:
        tags = ID3(path)
    except ID3Error:
        tags = ID3()
    if bpm is not None:
        tags.setall("TBPM", [TBPM(encoding=3, text=str(int(round(float(bpm)))))])
    # TKEY expects musical key notation; many apps also read the Camelot code.
    key_text = camelot or key
    if key_text:
        tags.setall("TKEY", [TKEY(encoding=3, text=str(key_text))])
    if genre:
        tags.setall("TCON", [TCON(encoding=3, text=str(genre))])
    if title:
        tags.setall("TIT2", [TIT2(encoding=3, text=str(title))])
    if artist:
        tags.setall("TPE1", [TPE1(encoding=3, text=str(artist))])
    cmt = _key_comment(key, camelot, comment)
    if cmt:
        tags.setall("COMM", [COMM(encoding=3, lang="eng", desc="", text=cmt)])
    tags.save(path, v2_version=3)
    return True


# ── FLAC / OGG Vorbis / Opus ──────────────────────────────────────────────────

def _tag_vorbis(path, ext, bpm, key, camelot, genre, title, artist, comment):
    if ext == ".flac":
        from mutagen.flac import FLAC as _Open
    elif ext == ".opus":
        from mutagen.oggopus import OggOpus as _Open
    else:
        from mutagen.oggvorbis import OggVorbis as _Open
    audio = _Open(path)
    if bpm is not None:
        audio["BPM"] = str(int(round(float(bpm))))
    if key:
        # INITIALKEY: Serato/Traktor; KEY: VirtualDJ/Mixed In Key fallback
        audio["INITIALKEY"] = str(key)
        audio["KEY"] = str(key)
    if camelot:
        audio["CAMELOT"] = str(camelot)
    if genre:
        audio["GENRE"] = str(genre)
    if title:
        audio["TITLE"] = str(title)
    if artist:
        audio["ARTIST"] = str(artist)
    cmt = _key_comment(key, camelot, comment)
    if cmt:
        audio["COMMENT"] = cmt
    audio.save()
    return True


# ── MP4 / M4A (iTunes-style atoms) ────────────────────────────────────────────

def _tag_mp4(path, bpm, key, camelot, genre, title, artist, comment):
    from mutagen.mp4 import MP4, MP4FreeText
    audio = MP4(path)
    if bpm is not None:
        audio["tmpo"] = [int(round(float(bpm)))]          # native tempo atom (int)
    key_text = key or camelot
    if key_text:
        # Freeform atoms keyed the way Serato/Mixed In Key expect them.
        audio["----:com.apple.iTunes:initialkey"] = [
            MP4FreeText(str(key_text).encode("utf-8"))]
        audio["----:com.apple.iTunes:KEY"] = [
            MP4FreeText(str(key_text).encode("utf-8"))]
    if camelot:
        audio["----:com.apple.iTunes:CAMELOT"] = [
            MP4FreeText(str(camelot).encode("utf-8"))]
    if genre:
        audio["\xa9gen"] = [str(genre)]
    if title:
        audio["\xa9nam"] = [str(title)]
    if artist:
        audio["\xa9ART"] = [str(artist)]
    cmt = _key_comment(key, camelot, comment)
    if cmt:
        audio["\xa9cmt"] = [cmt]
    audio.save()
    return True
