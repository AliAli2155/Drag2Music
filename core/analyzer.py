import threading
import requests
from PIL import Image, ImageTk
from io import BytesIO
import yt_dlp

from .constants import C

try:
    from tkinterdnd2 import DND_TEXT, DND_FILES
    _HAS_DND = True
except ImportError:
    _HAS_DND = False


class AnalyzerMixin:

    # ── Thumbnail helpers ─────────────────────────────────────────────────────

    def _hide_thumbnail(self):
        self._thumb_photo = None
        self.thumb_img.configure(image="")
        self.thumb_img.lower()
        self.thumb_label.configure(text=self.t("thumb_ready"))
        self.thumb_label.lift()

    def clear_search(self):
        self._analysis_id = getattr(self, '_analysis_id', 0) + 1
        self.url_entry.delete(0, "end")
        self.current_video_url   = ""
        self.current_video_title = ""
        self.current_video_info  = {}
        self.track_duration      = 0
        self._pending_playlist   = None

        self._hide_thumbnail()
        self.lbl_title.configure(text="")
        self.lbl_source_badge.configure(text="", fg_color="transparent")
        self.lbl_lyrics.configure(text=self.t("lyrics_placeholder"),
                                  text_color=C["very_dim"])
        self.btn_download.configure(state="disabled", text=self.t("main_btn"))

    # ── Analysis ──────────────────────────────────────────────────────────────

    def start_analysis_thread(self):
        q = self.url_entry.get().strip()
        if len(q) > 2:
            self._pending_playlist = None
            self._analysis_id = getattr(self, '_analysis_id', 0) + 1
            threading.Thread(
                target=self.analyze_video,
                args=(q, self._analysis_id),
                daemon=True).start()

    def analyze_video(self, q, aid: int = 0):
        def stale():
            return aid != getattr(self, '_analysis_id', 0)

        self.after(0, lambda: self.btn_search.configure(
            state="disabled", text=self.t("analyzing")))
        self.after(0, lambda: (self._hide_thumbnail(),
                               self.thumb_label.configure(text=self.t("loading"))))
        self.after(0, lambda: self.lbl_source_badge.configure(
            text="", fg_color="transparent"))
        try:
            sq      = q if q.startswith("http") else f"ytsearch1:{q}"
            is_list = any(k in sq for k in ("list=", "/playlist?", "/sets/"))

            if is_list:
                with yt_dlp.YoutubeDL({
                    'quiet': True, 'skip_download': True,
                    'extract_flat': 'in_playlist', 'ignoreerrors': True,
                }) as ydl:
                    pinfo = ydl.extract_info(sq, download=False)
                entries = [e for e in (pinfo.get('entries') or []) if e]
                if len(entries) > 1:
                    if not stale():
                        self._process_playlist(pinfo, entries)
                    return
                if entries:
                    sq = (entries[0].get('webpage_url') or
                          entries[0].get('url') or
                          (f"https://www.youtube.com/watch?v={entries[0]['id']}"
                           if entries[0].get('id') else sq))

            with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
                info = ydl.extract_info(sq, download=False)
                if 'entries' in info:
                    info = info['entries'][0]

            if stale():
                return

            self.current_video_url   = info['webpage_url']
            self.current_video_title = info['title']
            self.track_duration      = info.get('duration', 0) or 0
            self.current_video_info  = info

            badge_text, badge_color = self._source_badge(self.current_video_url)
            self.after(0, lambda t=badge_text, c=badge_color:
                       self.lbl_source_badge.configure(text=t, fg_color=c))

            vid_id = info.get('id', '')
            ttxt   = info['title'][:65]

            new_pil_img = None
            for _url in filter(None, [
                f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg" if vid_id else None,
                f"https://i.ytimg.com/vi/{vid_id}/mqdefault.jpg" if vid_id else None,
                info.get('thumbnail', ''),
            ]):
                try:
                    _resp = requests.get(_url, timeout=8)
                    if _resp.status_code == 200 and len(_resp.content) > 500:
                        new_pil_img = Image.open(BytesIO(_resp.content)).resize((310, 172))
                        break
                except Exception:
                    continue

            if stale():
                return

            if new_pil_img:
                def _apply_thumb(pil=new_pil_img):
                    if stale():
                        return
                    photo = ImageTk.PhotoImage(pil)
                    self._thumb_photo = photo
                    self.thumb_img.configure(image=photo)
                    self.thumb_img.lift()
                    self.thumb_label.configure(text="")
                    self.thumb_label.lower()
                self.after(0, _apply_thumb)
            else:
                self.after(0, self._hide_thumbnail)

            self.after(0, lambda: self.lbl_title.configure(text=ttxt))
            self.after(0, lambda: self.btn_download.configure(
                state="normal", text=self.t("main_btn")))

            threading.Thread(
                target=self.auto_find_lyrics,
                args=(info['title'], info['webpage_url']),
                daemon=True).start()

        except Exception as e:
            print(f"[Analyze] Error: {e}")
            self.after(0, lambda: (self._hide_thumbnail(),
                                   self.thumb_label.configure(
                                       text=self.t("analysis_failed"))))
        finally:
            self.after(0, lambda: self.btn_search.configure(
                state="normal", text=self.t("search_btn")))

    # ── Playlist ──────────────────────────────────────────────────────────────

    def _process_playlist(self, info, entries):
        fmt     = self.mode_menu.get().split()[-1].upper()
        quality = self.quality_combo.get()
        title   = info.get("title", "Playlist")
        pl_url  = info.get("webpage_url", "")

        items = []
        for e in entries:
            if not e:
                continue
            url = e.get("webpage_url") or e.get("url") or ""
            if not url.startswith("http"):
                vid_id = e.get("id", "")
                if vid_id:
                    url = f"https://www.youtube.com/watch?v={vid_id}"
            if not url.startswith("http"):
                continue
            items.append({
                "url": url, "title": e.get("title", "Unknown")[:80],
                "fmt": fmt, "quality": quality,
                "status": "pending", "progress": 0,
            })

        self._pending_playlist = items
        n = len(items)

        badge_text, badge_color = self._source_badge(pl_url)
        self.after(0, lambda t=badge_text, c=badge_color:
                   self.lbl_source_badge.configure(text=t, fg_color=c))
        self.after(0, lambda: self.thumb_label.configure(
            text=f"📋  {n} tracks", image=None))
        self.after(0, lambda t=title[:65]: self.lbl_title.configure(text=f"📋  {t}"))
        self.after(0, lambda n=n: self.btn_download.configure(
            state="normal", text=f"QUEUE ALL  ({n} tracks)"))

    def _source_badge(self, url):
        if "soundcloud.com" in url:
            return " ● SoundCloud ", "#e84f00"
        if "youtube.com" in url or "youtu.be" in url:
            return " ▶ YouTube ", "#b00000"
        return " ◆ Web ", "#444444"

    # ── Drag & Drop ───────────────────────────────────────────────────────────

    def setup_drag_drop(self):
        if not _HAS_DND:
            return
        try:
            from tkinterdnd2 import TkinterDnD
            TkinterDnD._require(self)
            inner = self.url_entry._entry
            inner.drop_target_register(DND_TEXT, DND_FILES)
            inner.dnd_bind("<<Drop>>", self._on_drop)
        except Exception as e:
            print(f"[DnD] Setup error: {e}")

    def _on_drop(self, event):
        try:
            raw = event.data.strip().strip("{}")
            url = raw.split()[0]
            if url.startswith("http"):
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, url)
                self.start_analysis_thread()
        except Exception as e:
            print(f"[DnD] Drop error: {e}")
