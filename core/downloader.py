import threading
import datetime
import yt_dlp
from plyer import notification
from .constants import THUMBNAIL_EMBED_FMTS


class DownloaderMixin:

    def start_download_thread(self):
        self.btn_download.configure(state="disabled", text=self.t("processing"))
        self.dl_progress.set(0)
        self.dl_progress.grid()
        self.dl_status_lbl.configure(text=self.t("dl_starting"))
        self.dl_status_lbl.grid()
        threading.Thread(target=self.run_download, daemon=True).start()

    def _dl_hook(self, d):
        if d['status'] == 'downloading':
            total    = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            done     = d.get('downloaded_bytes', 0)
            speed    = d.get('speed') or 0
            eta      = d.get('eta') or 0
            pct      = done / total if total else 0
            self.after(0, lambda p=pct: self.dl_progress.set(p))
            speed_str = self._fmt_speed(speed)
            pct_str   = f"{pct * 100:.0f}%  " if total else ""
            eta_str   = f"  •  ETA {eta}s" if eta else ""
            status    = f"{pct_str}{speed_str}{eta_str}"
            self.after(0, lambda s=status: self.dl_status_lbl.configure(text=s))
        elif d['status'] == 'finished':
            self.after(0, lambda: self.dl_progress.set(1.0))
            self.after(0, lambda: self.dl_status_lbl.configure(text=self.t("dl_embedding")))

    @staticmethod
    def _fmt_speed(bps: float) -> str:
        if bps <= 0:
            return ""
        if bps >= 1_048_576:
            return f"{bps / 1_048_576:.1f} MB/s"
        return f"{bps / 1024:.0f} KB/s"

    def run_download(self):
        mode    = self.mode_menu.get()
        quality = self.quality_combo.get()
        fmt     = mode.split()[-1].upper()

        vid_info  = getattr(self, 'current_video_info', {})
        meta_args = []
        for ffkey, val in [
            ('title',  vid_info.get('title', '')),
            ('artist', vid_info.get('uploader') or vid_info.get('channel') or ''),
            ('album',  vid_info.get('album') or vid_info.get('playlist_title') or ''),
            ('date',   (vid_info.get('upload_date') or '')[:4]),
        ]:
            if val:
                meta_args += ['-metadata', f'{ffkey}={val}']

        base_opts = {
            'outtmpl':            f'{self.download_path}/%(title)s.%(ext)s',
            'quiet':              True,
            'progress_hooks':     [self._dl_hook],
            'writethumbnail':     fmt in THUMBNAIL_EMBED_FMTS,
            'postprocessor_args': {'default': meta_args} if meta_args else {},
        }

        if fmt in ("MP3", "AAC", "OGG", "OPUS"):
            codec_map = {"MP3": "mp3", "AAC": "aac", "OGG": "vorbis", "OPUS": "opus"}
            kbps = quality.split()[0]
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
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'wav'}],
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
                'postprocessors': [{'key': 'EmbedThumbnail', 'already_have_thumbnail': False}],
            })
        elif fmt in ("WEBM", "AVI"):
            res_map = {"1080p FHD": "1080", "720p HD": "720",
                       "480p SD": "480", "360p": "360"}
            res = res_map.get(quality, "720")
            base_opts.update({
                'format':              f'bestvideo[height<={res}]+bestaudio/best',
                'merge_output_format': fmt.lower(),
                'postprocessors':      [],
            })

        success = False
        try:
            with yt_dlp.YoutubeDL(base_opts) as ydl:
                ydl.download([self.current_video_url])

            success = True
            self.download_history.append({
                "name":   self.current_video_title,
                "time":   datetime.datetime.now().strftime("%H:%M"),
                "format": fmt,
            })
            self.save_data_to_disk()
            self.after(0, self.refresh_library_ui)
            short_title = self.current_video_title[:60]
            self.after(0, lambda: self.dl_progress.set(1.0))
            self.after(0, lambda t=short_title: self.dl_status_lbl.configure(
                text=f"{self.t('dl_done')}: {t}", text_color=self.current_theme_color))
            notification.notify(
                title="TuneFetch ✅",
                message=f"{self.current_video_title[:80]}\n{fmt} • {quality}")
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda m=err_msg: self.dl_status_lbl.configure(
                text=f"❌ {m}", text_color="#e74c3c"))
            notification.notify(title="TuneFetch ❌", message=f"Failed: {err_msg[:80]}")
        finally:
            self.after(0, lambda: self.btn_download.configure(
                state="normal", text=self.t("main_btn")))
            if success:
                self.after(4000, self._hide_progress)

    def _hide_progress(self):
        self.dl_progress.grid_remove()
        self.dl_status_lbl.configure(text="")
        self.dl_status_lbl.grid_remove()

