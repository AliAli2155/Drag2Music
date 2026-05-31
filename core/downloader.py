import os
import time
import queue
import datetime
import threading
import yt_dlp

from .constants import THUMBNAIL_EMBED_FMTS, C

try:
    from plyer import notification as _plyer_notification
except Exception:
    _plyer_notification = None


class DownloaderMixin:

    # ── Queue entry point ─────────────────────────────────────────────────────

    def enqueue_current(self):
        if self._pending_playlist is None and not self.current_video_url:
            return
        self.btn_download.configure(state="disabled")

        with self._queue_lock:
            if self._pending_playlist is not None:
                for item in self._pending_playlist:
                    self.queue_items.append(item)
                    self.dl_queue.put(item)
                self._pending_playlist = None
            else:
                fmt     = self.mode_menu.get().split()[-1].upper()
                quality = self.quality_combo.get()
                item = {
                    "url": self.current_video_url,
                    "title": self.current_video_title,
                    "fmt": fmt, "quality": quality,
                    "status": "pending", "progress": 0,
                }
                self.queue_items.append(item)
                self.dl_queue.put(item)

        self.after(0, self._refresh_queue_ui)

        if not self.queue_worker_running:
            self.queue_worker_running = True
            threading.Thread(target=self._queue_worker, daemon=True).start()

    # ── Worker thread ─────────────────────────────────────────────────────────

    def _queue_worker(self):
        total = self.dl_queue.qsize()
        done  = 0

        if total > 1:
            self.after(0, lambda t=total: self._pl_bar_show(0, t))

        while True:
            try:
                item = self.dl_queue.get(timeout=3.0)
            except queue.Empty:
                break

            item["status"]   = "downloading"
            item["progress"] = 0
            self.after(0, self._refresh_queue_ui)

            try:
                self._run_queued_download(item)
                item["status"]   = "done"
                item["progress"] = 100
                self.download_history.append({
                    "name":   item["title"],
                    "time":   datetime.datetime.now().strftime("%H:%M"),
                    "format": item["fmt"],
                })
                self.save_data_to_disk()
                self.after(0, self.refresh_library_ui)
                try:
                    if _plyer_notification:
                        _plyer_notification.notify(
                            title="TuneFetch ✅",
                            message=f"{item['title'][:80]}\n{item['fmt']} • {item['quality']}")
                except Exception:
                    pass
            except Exception as e:
                print(f"[Queue] Download error for '{item.get('title')}': {e}")
                item["status"] = "error"

            done += 1
            if total > 1:
                self.after(0, lambda d=done, t=total: self._pl_bar_show(d, t))

            self.after(0, self._refresh_queue_ui)
            self.dl_queue.task_done()

        self.queue_worker_running = False
        self.after(0, lambda: self.progress_bar.set(0))
        self.after(0, lambda: self.lbl_speed.configure(text=" "))
        self.after(0, self._pl_bar_hide)

    # ── Download logic ────────────────────────────────────────────────────────

    def _run_queued_download(self, item):
        os.makedirs(self.download_path, exist_ok=True)
        fmt        = item["fmt"]
        quality    = item["quality"]
        ffmpeg_dir = os.environ.get('FFMPEG_DIR', '')

        base_opts = {
            'outtmpl':                       f'{self.download_path}/%(title)s.%(ext)s',
            'quiet':                         True,
            'progress_hooks':                [self._ydl_hook],
            'writethumbnail':                fmt in THUMBNAIL_EMBED_FMTS,
            'noprogress':    True,
            'ignoreerrors':  True,
            'noplaylist':    True,
        }
        if ffmpeg_dir:
            base_opts['ffmpeg_location'] = ffmpeg_dir

        if fmt in ("MP3", "AAC", "OGG", "OPUS"):
            codec_map = {"MP3": "mp3", "AAC": "aac", "OGG": "vorbis", "OPUS": "opus"}
            kbps = quality.split()[0] if quality else "192"
            base_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [
                    {'key': 'FFmpegExtractAudio',
                     'preferredcodec': codec_map[fmt], 'preferredquality': kbps},
                    {'key': 'EmbedThumbnail', 'already_have_thumbnail': False},
                ],
            })
        elif fmt == "WAV":
            base_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [
                    {'key': 'FFmpegExtractAudio', 'preferredcodec': 'wav'}],
            })
        elif fmt == "FLAC":
            base_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [
                    {'key': 'FFmpegExtractAudio', 'preferredcodec': 'flac'},
                    {'key': 'EmbedThumbnail', 'already_have_thumbnail': False},
                ],
            })
        elif fmt in ("MP4", "MKV"):
            res_map = {"4K (2160p)": "2160", "1080p FHD": "1080",
                       "720p HD": "720", "480p SD": "480", "360p": "360"}
            res = res_map.get(quality, "1080")
            base_opts.update({
                'format':              f'bestvideo[height<={res}]+bestaudio/best',
                'merge_output_format': fmt.lower(),
                'postprocessors': [
                    {'key': 'EmbedThumbnail', 'already_have_thumbnail': False}],
            })
        elif fmt in ("WEBM", "AVI"):
            res_map = {"1080p FHD": "1080", "720p HD": "720",
                       "480p SD": "480",  "360p": "360"}
            res = res_map.get(quality, "720")
            base_opts.update({
                'format':              f'bestvideo[height<={res}]+bestaudio/best',
                'merge_output_format': fmt.lower(),
                'postprocessors':      [],
            })

        with yt_dlp.YoutubeDL(base_opts) as ydl:
            ydl.download([item["url"]])

    # ── Progress hooks ────────────────────────────────────────────────────────

    def _ydl_hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done  = d.get("downloaded_bytes", 0)
            speed = d.get("speed") or 0
            pct   = (done / total * 100) if total > 0 else 0
            for it in self.queue_items:
                if it.get("status") == "downloading":
                    it["progress"] = pct
                    break
            now = time.time()
            if now - self._last_progress_ui < 0.12:
                return
            self._last_progress_ui = now
            self.after(0, lambda p=pct, s=speed: self._update_progress_ui(p, s))
        elif d["status"] == "finished":
            for it in self.queue_items:
                if it.get("status") == "downloading":
                    it["progress"] = 100
                    break
            self._last_progress_ui = 0.0
            self.after(0, lambda: self._update_progress_ui(100, 0))

    def _pl_bar_show(self, done: int, total: int):
        try:
            self.lbl_pl_progress.grid()
            self.lbl_pl_progress.configure(
                text=f"Playlist  {done} / {total}  tracks",
                text_color=self.current_theme_color)
            self.progress_bar_pl.grid()
            self.progress_bar_pl.set(done / total if total else 0)
        except Exception as e:
            print(f"[PL bar] {e}")

    def _pl_bar_hide(self):
        try:
            self.progress_bar_pl.grid_remove()
            self.lbl_pl_progress.grid_remove()
        except Exception:
            pass

    def _update_progress_ui(self, pct, speed_bps):
        try:
            self.progress_bar.set(pct / 100)
            if speed_bps > 0:
                if speed_bps >= 1_048_576:
                    spd = f"{speed_bps / 1_048_576:.1f} MB/s"
                else:
                    spd = f"{speed_bps / 1024:.0f} KB/s"
                self.lbl_speed.configure(
                    text=f"{pct:.0f}%  {spd}",
                    text_color=self.current_theme_color)
            elif pct >= 100:
                self.lbl_speed.configure(
                    text="Processing...",
                    text_color=self.current_theme_color)
        except Exception as e:
            print(f"[UI] Progress update error: {e}")

    def _refresh_queue_ui(self):
        pass   # queue panel removed

    def _clear_done_queue(self):
        with self._queue_lock:
            self.queue_items = [
                it for it in self.queue_items
                if it.get("status") not in ("done", "error")
            ]

    def _draw_ring(self, _pct=0):
        pass

    @staticmethod
    def _fmt_speed(bps: float) -> str:
        if bps <= 0:
            return ""
        if bps >= 1_048_576:
            return f"{bps / 1_048_576:.1f} MB/s"
        return f"{bps / 1024:.0f} KB/s"
