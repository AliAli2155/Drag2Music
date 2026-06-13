import sys
import threading
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageTk
from io import BytesIO

from .constants import C

try:
    _LANCZOS = Image.Resampling.LANCZOS
    _BILINEAR = Image.Resampling.BILINEAR
except AttributeError:
    _LANCZOS = Image.LANCZOS
    _BILINEAR = Image.BILINEAR

from .audio_quality import source_quality


def _pil_font(size):
    """Best-effort platform UI font for PIL text rendering."""
    if sys.platform == "win32":
        names = ["segoeui.ttf", "arial.ttf"]
    elif sys.platform == "darwin":
        names = ["/System/Library/Fonts/Helvetica.ttc",
                 "/System/Library/Fonts/HelveticaNeue.ttc"]
    else:
        names = ["DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size)   # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def _strip_emoji(s):
    return "\n".join(
        line for line in
        "".join(ch for ch in (s or "") if ord(ch) < 0x1F000).splitlines()
        if line.strip()).strip()


class AnalyzerMixin:

    # ── Thumbnail helpers ─────────────────────────────────────────────────────

    def _set_badge(self, w, text, color=None):
        """Show a cover badge with text, or hide it entirely when empty —
        'transparent' CTk labels still paint the card colour, so empty badges
        must drop below the artwork."""
        try:
            w.configure(text=text,
                        fg_color=(color if (text and color) else "transparent"))
            if text:
                w.lift()
            else:
                w.lower()
        except Exception:
            pass

    def _hide_thumbnail(self, status_key="thumb_ready", literal=None):
        """Clear the artwork and show the gradient idle art with a status
        message (translated key, or a literal string for playlists)."""
        self._cancel_cover_fade()
        self._thumb_pil_raw = None
        self._thumb_photo = None
        self._idle_key, self._idle_literal = status_key, literal
        self.thumb_label.lower()
        self._set_badge(self.lbl_duration, "")
        self._render_idle_art()

    def _render_idle_art(self):
        """Accent-tinted gradient placeholder (vinyl motif + status text)
        shown in the cover card whenever no artwork is loaded."""
        if getattr(self, "_thumb_pil_raw", None) is not None:
            return
        try:
            if not self.preview_frame.winfo_exists():
                return
            fw = self.preview_frame.winfo_width()
            fh = self.preview_frame.winfo_height()
        except Exception:
            return
        if fw < 40 or fh < 40:    # not laid out yet — retry shortly
            self.after(60, self._render_idle_art)
            return

        dark   = ctk.get_appearance_mode() == "Dark"
        bg_hex = C["bg"][1] if dark else C["bg"][0]
        bg     = tuple(int(bg_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        card_hex = C["card"][1] if dark else C["card"][0]
        card   = tuple(int(card_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        acc_hex = getattr(self, "current_theme_color", "#1DB954")
        acc    = tuple(int(acc_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

        def mix(a, b, t):
            return tuple(int(x + (y - x) * t) for x, y in zip(a, b))

        # Symmetric radial glow: an accent tint at the centre fading evenly
        # to the card colour at the edges (no diagonal bias → fully mirror-
        # symmetric both horizontally and vertically).
        depth   = 0.30 if dark else 0.20
        centre  = mix(card, acc, depth)
        rmask   = Image.radial_gradient("L").resize((fw, fh), _BILINEAR)
        inner   = Image.new("RGB", (fw, fh), centre)
        outer   = Image.new("RGB", (fw, fh), card)
        img     = Image.composite(outer, inner, rmask).convert("RGBA")
        draw    = ImageDraw.Draw(img)

        # Vinyl disc + status text, centred as one balanced group.
        mono   = (255, 255, 255) if dark else (0, 0, 0)
        disc   = mix(card, mono, 0.05)
        ring   = mix(card, mono, 0.12)
        R      = int(min(fw, fh) * 0.24)
        fs     = max(13, int(min(fw, fh) * 0.052))
        gap    = int(fh * 0.07)
        block  = 2 * R + gap + fs
        top    = (fh - block) // 2
        cx     = fw // 2
        cy     = top + R                       # disc centre

        draw.ellipse([cx - R, cy - R, cx + R, cy + R], fill=disc)
        for rr in (int(R * 0.78), int(R * 0.58)):
            draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                         outline=ring, width=2)
        r0 = max(4, int(R * 0.16))
        draw.ellipse([cx - r0, cy - r0, cx + r0, cy + r0],
                     fill=mix(acc, card, 0.15))

        # Status text, centred under the disc
        text = self._idle_literal if getattr(self, "_idle_literal", None) \
            else self.t(getattr(self, "_idle_key", "thumb_ready"))
        text = _strip_emoji(text)
        if text:
            try:
                fnt = _pil_font(fs)
                txt_clr = mix(card, (255, 255, 255) if dark else (0, 0, 0), 0.45)
                draw.multiline_text((cx, cy + R + gap), text, font=fnt,
                                    fill=txt_clr, anchor="ma", align="center")
            except Exception:
                pass

        # Rounded corners composited over the window bg (same as the cover)
        ss = 2
        mask = Image.new("L", (fw * ss, fh * ss), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, fw * ss - 1, fh * ss - 1], radius=18 * ss, fill=255)
        mask = mask.resize((fw, fh), _LANCZOS)
        base = Image.new("RGBA", (fw, fh), (*bg, 255))
        base.paste(img, (0, 0), mask)

        photo = ImageTk.PhotoImage(base.convert("RGB"))
        self._thumb_photo = photo
        self.thumb_img.configure(image=photo)
        self.thumb_img.lift()
        for b in (self.lbl_source_badge, self.lbl_quality_badge,
                  self.lbl_duration):
            try:
                b.lift() if b.cget("text") else b.lower()
            except Exception:
                pass

    def _cancel_cover_fade(self):
        job = getattr(self, "_cover_fade_job", None)
        if job is not None:
            try:
                self.after_cancel(job)
            except Exception:
                pass
            self._cover_fade_job = None

    def _render_cover(self, animate=False):
        """Render the stored raw cover into the preview frame: centre-crop to
        the frame's aspect ratio, resize to fill it completely, and round the
        corners so the artwork looks like one clean card.

        With animate=True the artwork fades in from the background (~170 ms).
        Must be called from the Tk main thread."""
        raw = getattr(self, "_thumb_pil_raw", None)
        if raw is None:
            return
        try:
            if not self.preview_frame.winfo_exists():
                return
            fw = self.preview_frame.winfo_width()
            fh = self.preview_frame.winfo_height()
        except Exception:
            return   # window torn down mid-callback
        if fw < 40 or fh < 40:   # not laid out yet — retry shortly
            self.after(60, lambda: self._render_cover(animate))
            return
        self._cancel_cover_fade()

        # Centre-crop the source to the frame's aspect ratio
        src_ratio = raw.width / raw.height
        dst_ratio = fw / fh
        if src_ratio > dst_ratio:          # source wider → crop sides
            new_w = max(1, int(raw.height * dst_ratio))
            x0 = (raw.width - new_w) // 2
            box = (x0, 0, x0 + new_w, raw.height)
        else:                              # source taller → crop top/bottom
            new_h = max(1, int(raw.width / dst_ratio))
            y0 = (raw.height - new_h) // 2
            box = (0, y0, raw.width, y0 + new_h)
        img = raw.crop(box).resize((fw, fh), _LANCZOS).convert("RGBA")

        # Rounded corners (4x supersampled mask for smooth edges),
        # composited over the window background so the card blends in.
        radius = 18
        ss = 4
        mask = Image.new("L", (fw * ss, fh * ss), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, fw * ss - 1, fh * ss - 1], radius=radius * ss, fill=255)
        mask = mask.resize((fw, fh), _LANCZOS)

        bg_hex = C["bg"][1] if ctk.get_appearance_mode() == "Dark" else C["bg"][0]
        bg_rgb = tuple(int(bg_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        base = Image.new("RGBA", (fw, fh), (*bg_rgb, 255))
        base.paste(img, (0, 0), mask)

        def _show(photo):
            self._thumb_photo = photo
            self.thumb_img.configure(image=photo)
            self.thumb_img.lift()
            self.thumb_label.configure(text="")
            self.thumb_label.lower()
            # Keep populated badges readable on top of the artwork;
            # empty ones stay hidden below it.
            for b in (self.lbl_source_badge, self.lbl_quality_badge,
                      self.lbl_duration):
                try:
                    b.lift() if b.cget("text") else b.lower()
                except Exception:
                    pass

        if not animate:
            _show(ImageTk.PhotoImage(base.convert("RGB")))
            return

        # Fade-in: blend from the plain background to the artwork
        blank  = Image.new("RGBA", (fw, fh), (*bg_rgb, 255))
        steps  = 6
        frames = [ImageTk.PhotoImage(
                      Image.blend(blank, base, (i + 1) / steps).convert("RGB"))
                  for i in range(steps)]

        def _fade(i=0):
            self._cover_fade_job = None
            try:
                _show(frames[i])
            except Exception:
                return
            if i + 1 < len(frames):
                self._cover_fade_job = self.after(28, lambda: _fade(i + 1))
        _fade()

    def _on_cover_resize(self, _event=None):
        """Debounced re-render when the preview frame changes size —
        covers both real artwork and the gradient idle art."""
        job = getattr(self, "_cover_resize_job", None)
        if job:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        target = (self._render_cover
                  if getattr(self, "_thumb_pil_raw", None) is not None
                  else self._render_idle_art)
        self._cover_resize_job = self.after(120, target)

    @staticmethod
    def _fmt_duration(seconds):
        s = int(seconds or 0)
        if s <= 0:
            return ""
        if s >= 3600:
            return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"
        return f"{s // 60}:{s % 60:02d}"

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
        self.lbl_artist.configure(text="")
        self._set_badge(self.lbl_source_badge, "")
        self._set_badge(self.lbl_quality_badge, "")
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
        import yt_dlp     # deferred: keeps app startup fast
        import requests   # deferred for the same reason

        def stale():
            return aid != getattr(self, '_analysis_id', 0)

        self.after(0, lambda: self.btn_search.configure(
            state="disabled", text=self.t("analyzing")))
        self.after(0, lambda: self._hide_thumbnail("loading"))
        self.after(0, lambda: (
            self._set_badge(self.lbl_source_badge, ""),
            self._set_badge(self.lbl_quality_badge, ""),
            self.lbl_artist.configure(text="")))
        try:
            sq      = q if q.startswith("http") else f"ytsearch1:{q}"
            is_list = any(k in sq for k in ("list=", "/playlist?", "/sets/"))

            if is_list:
                with yt_dlp.YoutubeDL({
                    'quiet': True, 'skip_download': True,
                    'extract_flat': 'in_playlist', 'ignoreerrors': True,
                    'socket_timeout': 20,
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

            with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True,
                                   'socket_timeout': 20}) as ydl:
                info = ydl.extract_info(sq, download=False)
                if info and 'entries' in info:
                    entries = [e for e in (info['entries'] or []) if e]
                    if not entries:
                        raise ValueError("No results found")
                    info = entries[0]
            if not info:
                raise ValueError("No results found")

            if stale():
                return

            self.current_video_url   = (info.get('webpage_url')
                                        or info.get('original_url')
                                        or info.get('url') or sq)
            self.current_video_title = info.get('title', 'Unknown')
            self.track_duration      = info.get('duration', 0) or 0
            self.current_video_info  = info

            badge_text, badge_color = self._source_badge(self.current_video_url)
            self.after(0, lambda t=badge_text, c=badge_color:
                       self._set_badge(self.lbl_source_badge, t, c))

            # Real source quality (honest badge — shows actual stream, not requested fmt)
            sq_info = source_quality(info)
            q_clr = {"lossless": "#1DB954", "high": "#1DB954",
                     "medium": "#e67e22", "low": "#e74c3c"}.get(
                         sq_info["tier"], "#666666")
            self.after(0, lambda lbl=sq_info["label"], tier=sq_info["tier_text"], c=q_clr:
                       self._set_badge(
                           self.lbl_quality_badge,
                           f" {tier} · {lbl} " if lbl else f" {tier} ", c))

            vid_id = info.get('id', '')
            ttxt   = self.current_video_title[:90]
            artist = (info.get('artist') or info.get('uploader')
                      or info.get('channel') or "")
            dtxt   = self._fmt_duration(self.track_duration)

            # Highest-resolution art first (big cover card deserves it)
            new_pil_img = None
            for _url in filter(None, [
                f"https://i.ytimg.com/vi/{vid_id}/maxresdefault.jpg" if vid_id else None,
                f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg" if vid_id else None,
                info.get('thumbnail', ''),
                f"https://i.ytimg.com/vi/{vid_id}/mqdefault.jpg" if vid_id else None,
            ]):
                try:
                    _resp = requests.get(_url, timeout=8)
                    if _resp.status_code == 200 and len(_resp.content) > 1000:
                        new_pil_img = Image.open(
                            BytesIO(_resp.content)).convert("RGB")
                        break
                except Exception:
                    continue

            if stale():
                return

            if new_pil_img:
                def _apply_thumb(pil=new_pil_img):
                    if stale():
                        return
                    self._thumb_pil_raw = pil
                    self._render_cover(animate=True)
                self.after(0, _apply_thumb)
            else:
                self.after(0, self._hide_thumbnail)

            self.after(0, lambda t=ttxt, a=artist: (
                self.lbl_title.configure(text=t),
                self.lbl_artist.configure(text=a)))
            if dtxt:
                self.after(0, lambda d=dtxt: self._set_badge(
                    self.lbl_duration, f" ⏱ {d} ", "#1c1c1c"))
            self.after(0, lambda: self.btn_download.configure(
                state="normal", text=self.t("main_btn")))

            threading.Thread(
                target=self.auto_find_lyrics,
                args=(self.current_video_title, self.current_video_url),
                daemon=True).start()

        except Exception as e:
            print(f"[Analyze] Error: {e}")
            self.after(0, lambda: self._hide_thumbnail("analysis_failed"))
        finally:
            self.after(0, lambda: self.btn_search.configure(
                state="normal", text=self.t("search_btn")))

    # ── Playlist ──────────────────────────────────────────────────────────────

    def _process_playlist(self, info, entries):
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
            # fmt / quality are stamped at enqueue time (main thread) so the
            # user's final Format/Quality choice wins — see enqueue_current.
            items.append({
                "url": url, "title": e.get("title", "Unknown")[:80],
                "fmt": None, "quality": None,
                "status": "pending", "progress": 0,
            })

        self._pending_playlist = items
        n = len(items)

        badge_text, badge_color = self._source_badge(pl_url)
        self.after(0, lambda t=badge_text, c=badge_color:
                   self._set_badge(self.lbl_source_badge, t, c))
        # Hide any thumbnail left over from a previous single-track analysis
        self.after(0, lambda n=n: self._hide_thumbnail(literal=f"{n} tracks"))
        self.after(0, lambda t=title[:90]: (
            self.lbl_title.configure(text=f"📋  {t}"),
            self.lbl_artist.configure(text="")))
        qa = self.t("queue_all", "QUEUE ALL")
        self.after(0, lambda n=n, qa=qa: self.btn_download.configure(
            state="normal", text=f"{qa}  ({n})"))

    def _source_badge(self, url):
        if "soundcloud.com" in url:
            return " ● SoundCloud ", "#e84f00"
        if "youtube.com" in url or "youtu.be" in url:
            return " ▶ YouTube ", "#b00000"
        return " ◆ Web ", "#444444"

    # ── Drag & Drop ───────────────────────────────────────────────────────────

    def setup_drag_drop(self):
        # Re-render the big cover whenever its card is resized
        self.preview_frame.bind("<Configure>", self._on_cover_resize)
        try:
            # deferred import: tkinterdnd2 loads a Tcl extension
            from tkinterdnd2 import TkinterDnD, DND_TEXT, DND_FILES
            TkinterDnD._require(self)
            inner = self.url_entry._entry
            inner.drop_target_register(DND_TEXT, DND_FILES)
            inner.dnd_bind("<<Drop>>", self._on_drop)
        except ImportError:
            pass   # drag & drop is optional
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
