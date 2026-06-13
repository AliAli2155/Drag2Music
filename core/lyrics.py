import re
from .constants import C


class LyricsMixin:

    def auto_find_lyrics(self, title, video_url=""):
        import requests   # deferred: keeps app startup fast
        self.after(0, lambda: self.lbl_lyrics.configure(
            text=self.t("lyrics_searching"), text_color=self.current_theme_color))

        clean = re.sub(
            r'\((?:official|lyrics?|audio|video|hd|4k|clip)[^)]*\)'
            r'|\[(?:official|lyrics?|audio|video|hd|4k|clip)[^\]]*\]'
            r'|(?:official\s+(?:music\s+)?video|official\s+audio|lyrics?\s+video'
            r'|official\s+lyric\s+video|hd|4k)',
            '', title, flags=re.I).strip()

        candidates = [clean, title]

        try:
            import syncedlyrics
            for q in candidates:
                try:
                    raw = syncedlyrics.search(q, allow_plain_format=True, enhanced=False)
                    if raw and len(raw.strip()) > 40:
                        plain = re.sub(r'\[\d{1,2}:\d{2}[.:]\d{1,3}\]', '', raw).strip()
                        if len(plain) > 40:
                            self.after(0, lambda p=plain: self.lbl_lyrics.configure(
                                text=p, text_color=C["bright"]))
                            return
                except Exception:
                    pass
        except ImportError:
            pass

        for q in candidates:
            try:
                url = "https://lyrist.vercel.app/api/" + requests.utils.quote(q)
                r   = requests.get(url, timeout=8)
                if r.status_code == 200:
                    lyr = r.json().get("lyrics", "").strip()
                    if lyr and len(lyr) > 40:
                        self.after(0, lambda l=lyr: self.lbl_lyrics.configure(
                            text=l, text_color=C["bright"]))
                        return
            except Exception:
                pass

        for q in candidates:
            parts = q.split(" - ", 1)
            if len(parts) == 2:
                try:
                    artist = requests.utils.quote(parts[0].strip())
                    song   = requests.utils.quote(parts[1].strip())
                    r = requests.get(f"https://api.lyrics.ovh/v1/{artist}/{song}", timeout=8)
                    if r.status_code == 200:
                        lyr = r.json().get("lyrics", "").strip()
                        if lyr and len(lyr) > 40:
                            self.after(0, lambda l=lyr: self.lbl_lyrics.configure(
                                text=l, text_color=C["bright"]))
                            return
                except Exception:
                    pass

        for q in candidates:
            parts = q.split(" - ", 1)
            if len(parts) == 2:
                try:
                    r = requests.get("https://lrclib.net/api/get", params={
                        "artist_name": parts[0].strip(), "track_name": parts[1].strip()
                    }, timeout=8)
                    if r.status_code == 200:
                        data = r.json()
                        lyr  = (data.get("plainLyrics") or data.get("syncedLyrics") or "").strip()
                        lyr  = re.sub(r'\[\d{1,2}:\d{2}[.:]\d{1,3}\]', '', lyr).strip()
                        if lyr and len(lyr) > 40:
                            self.after(0, lambda l=lyr: self.lbl_lyrics.configure(
                                text=l, text_color=C["bright"]))
                            return
                except Exception:
                    pass

        msg = (f"❌  Lyrics not found for '{clean}'.\n\n"
               "💡 Tip: Use the format  Artist - Song Title\n"
               "   (example: Daft Punk - Get Lucky)")
        self.after(0, lambda m=msg: self.lbl_lyrics.configure(
            text=m, text_color=C["dim"]))
