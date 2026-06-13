import os
import glob
import time
import queue
import datetime
import threading


class DownloadCancelled(Exception):
    """Raised from the yt-dlp progress hook to abort an in-flight download."""
    pass

from .constants import THUMBNAIL_EMBED_FMTS, AUDIO_FMTS, LOUDNESS_PRESETS, TARGET_SAMPLE_RATE, C
from .audio_quality import ytdlp_audio_filter_args


def _notify(title, message):
    """Desktop notification; plyer is imported lazily (startup cost)."""
    try:
        from plyer import notification
        notification.notify(title=title, message=message)
    except Exception:
        pass


class DownloaderMixin:

    # ── Queue entry point ─────────────────────────────────────────────────────

    def enqueue_current(self):
        if self._pending_playlist is None and not self.current_video_url:
            return
        self._cancel_event.clear()
        self._cancel_partials.clear()
        self._show_cancel_button()
        self.btn_download.configure(state="disabled")

        # Read the format widgets here, on the main thread — the user's final
        # choice wins even for playlists analyzed earlier.
        fmt     = self.mode_menu.get().split()[-1].upper()
        quality = self.quality_combo.get()

        with self._queue_lock:
            if self._pending_playlist is not None:
                for item in self._pending_playlist:
                    item["fmt"]     = fmt
                    item["quality"] = quality
                    self.queue_items.append(item)
                    self.dl_queue.put(item)
                self._pending_playlist = None
            else:
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

            # Items may be enqueued while the worker runs — keep totals live.
            total = max(total, done + 1 + self.dl_queue.qsize())

            item["status"]   = "downloading"
            item["progress"] = 0
            self.after(0, self._refresh_queue_ui)

            try:
                self._cancel_partials.clear()
                self._run_queued_download(item)
                item["status"]   = "done"
                item["progress"] = 100
                self.download_history.append(self._history_entry(item))
                self.save_data_to_disk()
                self.after(0, self.refresh_library_ui)
                if item.get("pp_warning"):
                    done_msg = self.t("dl_done_nocover",
                                      "✅  Downloaded · cover art skipped")
                else:
                    done_msg = self.t("dl_done", "✅  Downloaded")
                self.after(0, lambda m=done_msg: self.lbl_speed.configure(
                    text=m, text_color=self.current_theme_color))
                _notify("Drag2Music ✅",
                        f"{item['title'][:80]}\n{item['fmt']} • {item['quality']}")
            except DownloadCancelled:
                self._cleanup_partial_files()
                self.after(0, self._on_download_cancelled)
                break
            except Exception as e:
                if self._cancel_event.is_set():
                    self._cleanup_partial_files()
                    self.after(0, self._on_download_cancelled)
                    break
                print(f"[Queue] Download error for '{item.get('title')}': {e}")
                item["status"] = "error"
                self.after(0, lambda: self.lbl_speed.configure(
                    text=self.t("download_error",
                                "❌ Download failed — check the URL or your connection"),
                    text_color="#E5484D"))

            done += 1
            if total > 1:
                self.after(0, lambda d=done, t=total: self._pl_bar_show(d, t))

            self.after(0, self._refresh_queue_ui)
            self.dl_queue.task_done()

        self.queue_worker_running = False
        self.after(0, lambda: self.progress_bar.set(0))
        self.after(0, self._pl_bar_hide)
        self.after(0, self._hide_cancel_button)

        def _finish_ui():
            # Re-enable the download button so the same track can be re-queued.
            if self.current_video_url or self._pending_playlist is not None:
                try:
                    self.btn_download.configure(state="normal")
                except Exception:
                    pass
        self.after(0, _finish_ui)

    # ── Download logic ────────────────────────────────────────────────────────

    @staticmethod
    def _source_name(url):
        u = url or ""
        if "soundcloud.com" in u:
            return "SoundCloud"
        if "youtube.com" in u or "youtu.be" in u:
            return "YouTube"
        return "Web"

    def _history_entry(self, item):
        """Full info record for the library: format, quality, size, duration,
        source, file path and timestamp."""
        now = datetime.datetime.now()
        entry = {
            "name":    item.get("title", "?"),
            "time":    now.strftime("%H:%M"),
            "date":    now.strftime("%d.%m.%Y"),
            "format":  item.get("fmt", "?"),
            "quality": item.get("quality", ""),
            "source":  self._source_name(item.get("url", "")),
        }
        dur = item.get("duration")
        if dur:
            try:
                entry["duration"] = int(dur)
            except (TypeError, ValueError):
                pass
        fp = item.get("filepath")
        if fp:
            entry["path"] = fp
            try:
                if os.path.exists(fp):
                    entry["size"] = os.path.getsize(fp)
            except OSError:
                pass
        return entry

    def _run_queued_download(self, item):
        import yt_dlp   # deferred: keeps app startup fast
        os.makedirs(self.download_path, exist_ok=True)
        fmt        = item["fmt"]
        quality    = item["quality"]
        ffmpeg_dir = os.environ.get('FFMPEG_DIR', '')

        def _pp_hook(d, item=item):
            # Runs after each post-processor: the last 'filepath' reported is
            # the final file on disk — feeds size/duration into the library.
            try:
                if d.get('status') == 'finished':
                    info = d.get('info_dict') or {}
                    fp = info.get('filepath')
                    if fp:
                        item['filepath'] = fp
                    dur = info.get('duration')
                    if dur:
                        item['duration'] = dur
            except Exception:
                pass

        base_opts = {
            'outtmpl':                       os.path.join(self.download_path, '%(title)s.%(ext)s'),
            'quiet':                         True,
            'progress_hooks':                [self._ydl_hook],
            'postprocessor_hooks':           [_pp_hook],
            'writethumbnail':                fmt in THUMBNAIL_EMBED_FMTS,
            'noprogress':       True,
            'ignoreerrors':     False,
            'noplaylist':       True,
            'retries':          5,
            'fragment_retries': 5,
            'socket_timeout':   20,
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
        elif fmt == "MP4":
            res_map = {"4K (2160p)": "2160", "1080p FHD": "1080",
                       "720p HD": "720", "480p SD": "480", "360p": "360"}
            res = res_map.get(quality, "1080")
            base_opts.update({
                # Prefer h264+aac (always muxes into mp4); at high resolutions
                # YouTube only serves vp9/av01, so fall back to best video with
                # m4a audio, then to anything (opus needs -strict -2 below).
                'format': (f'bestvideo[height<={res}][vcodec^=avc1]+bestaudio[ext=m4a]/'
                           f'bestvideo[height<={res}]+bestaudio[ext=m4a]/'
                           f'bestvideo[height<={res}]+bestaudio/best'),
                'merge_output_format': 'mp4',
                'postprocessor_args': {'merger': ['-strict', '-2']},
                'postprocessors': [
                    {'key': 'EmbedThumbnail', 'already_have_thumbnail': False}],
            })
        elif fmt == "MKV":
            res_map = {"4K (2160p)": "2160", "1080p FHD": "1080",
                       "720p HD": "720", "480p SD": "480", "360p": "360"}
            res = res_map.get(quality, "1080")
            base_opts.update({
                'format':              f'bestvideo[height<={res}]+bestaudio/best',
                'merge_output_format': 'mkv',
                'postprocessors': [
                    {'key': 'EmbedThumbnail', 'already_have_thumbnail': False}],
            })
        elif fmt in ("WEBM", "AVI"):
            # yt-dlp can only merge into mkv/mp4/webm/ogg/flv — 'avi' is not a
            # valid merge container, and forcing 'webm' fails when the source
            # streams are h264/aac.  Merge to mkv, then convert to the target.
            res_map = {"1080p FHD": "1080", "720p HD": "720",
                       "480p SD": "480",  "360p": "360"}
            res = res_map.get(quality, "720")
            base_opts.update({
                'format':              f'bestvideo[height<={res}]+bestaudio/best',
                'merge_output_format': 'mkv',
                'postprocessors': [
                    {'key': 'FFmpegVideoConvertor',
                     'preferedformat': fmt.lower()}],
            })

        # ── Quality & format consistency (DJ): loudness norm + fixed sample rate ──
        # Applied inside the ExtractAudio encode (one generation, before thumbnail
        # embed). Driven by the user's setting; audio formats only.
        if fmt in AUDIO_FMTS:
            target_lufs = LOUDNESS_PRESETS.get(getattr(self, "loudness_choice", "Off"))
            # Off = leave audio untouched (no loudnorm, no resample)
            target_sr   = getattr(self, "target_sr", TARGET_SAMPLE_RATE) \
                          if target_lufs is not None else None
            ppa = ytdlp_audio_filter_args(target_lufs=target_lufs, sample_rate=target_sr)
            if ppa:
                base_opts["postprocessor_args"] = ppa

        with yt_dlp.YoutubeDL(base_opts) as ydl:
            try:
                ydl.download([item["url"]])
            except Exception as e:
                if self._cancel_event.is_set():
                    raise DownloadCancelled() from e
                # Post-processing failures (e.g. cover-art embed) happen AFTER
                # the media file is fully downloaded and merged — the file is
                # fine, so report success with a note instead of a scary error.
                if "postprocessing" in str(e).lower():
                    print(f"[Queue] Post-processing warning (file kept): {e}")
                    item["pp_warning"] = True
                    return
                raise

    # ── Progress hooks ────────────────────────────────────────────────────────

    def _ydl_hook(self, d):
        # Track this download's temp/partial path so cleanup can remove it on cancel.
        _tmp = d.get('tmpfilename') or d.get('filename')
        if _tmp:
            self._cancel_partials.add(_tmp)
        if self._cancel_event.is_set():
            raise DownloadCancelled()

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
            info = d.get('info_dict') or {}
            for it in self.queue_items:
                if it.get("status") == "downloading":
                    it["progress"] = 100
                    # fallbacks — postprocessor hooks overwrite with finals
                    fn = d.get('filename')
                    if fn:
                        it.setdefault('filepath', fn)
                    if info.get('duration'):
                        it.setdefault('duration', info['duration'])
                    break
            self._last_progress_ui = 0.0
            self.after(0, lambda: self._update_progress_ui(100, 0))

    def _pl_bar_show(self, done: int, total: int):
        try:
            self.lbl_pl_progress.grid()
            self.lbl_pl_progress.configure(
                text=f"{self.t('playlist_label', 'Playlist')}  {done} / {total}",
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
                    text=spd,
                    text_color=self.current_theme_color)
            elif pct >= 100:
                self.lbl_speed.configure(
                    text=self.t("dl_processing", "Processing..."),
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

    def _cleanup_partial_files(self):
        """Delete partial/temp files left behind by an aborted download."""
        for base in list(self._cancel_partials):
            for cand in (base, base + '.part', base + '.ytdl'):
                try:
                    if os.path.exists(cand):
                        os.remove(cand)
                except OSError:
                    pass
            stem, _ = os.path.splitext(base)
            for cand in (glob.glob(glob.escape(stem) + '*.part') +
                         glob.glob(glob.escape(stem) + '*.ytdl')):
                try:
                    os.remove(cand)
                except OSError:
                    pass
        self._cancel_partials.clear()

    def cancel_download(self):
        """User-triggered: abort the active download and stop the queue."""
        if self._cancel_event.is_set():
            return
        self._cancel_event.set()
        try:
            while True:
                self.dl_queue.get_nowait()
                self.dl_queue.task_done()
        except queue.Empty:
            pass
        with self._queue_lock:
            self.queue_items.clear()
        self.cancel_btn.configure(
            text=self.t("cancelling", "Cancelling…"), state="disabled")

    def _on_download_cancelled(self):
        try:
            self.progress_bar.set(0)
            self.lbl_speed.configure(
                text=self.t("download_cancelled", "Download cancelled"),
                text_color="#E5484D")
        except Exception:
            pass
        self._hide_cancel_button()
        if self.current_video_url or self._pending_playlist is not None:
            try:
                self.btn_download.configure(state="normal")
            except Exception:
                pass
