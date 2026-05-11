import os, threading, glob, time
import pygame
import yt_dlp


class PlayerMixin:

    def _on_slider_drag(self, value):
        self.user_seeking = True
        if self.track_duration > 0:
            pos = (value / 100) * self.track_duration
            e   = int(pos)
            rem = max(0, int(self.track_duration - pos))
            self.lbl_elapsed.configure(text=f"{e // 60:02d}:{e % 60:02d}")
            self.lbl_remaining.configure(text=f"-{rem // 60:02d}:{rem % 60:02d}")
        if self._seek_job:
            self.after_cancel(self._seek_job)
        self._seek_job = self.after(250, lambda v=value: self._apply_seek(v))

    def _apply_seek(self, value):
        self.user_seeking = False
        if self.track_duration > 0 and self.is_playing:
            seek_sec = (value / 100) * self.track_duration
            self._seek_offset = seek_sec
            try:
                pygame.mixer.music.play(start=seek_sec)
            except Exception:
                pass

    def toggle_playback(self):
        if not self.current_video_url:
            return

        if self.is_playing:
            pygame.mixer.music.pause()
            self.btn_play_main.configure(text="▶")
            self.is_playing = False
            self.is_paused  = True

        elif self.is_paused and os.path.exists(self.temp_audio):
            pygame.mixer.music.unpause()
            self.btn_play_main.configure(text="⏸")
            self.is_playing = True
            self.is_paused  = False

        else:
            self.is_paused = False
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            self.btn_play_main.configure(text="⏳")
            threading.Thread(target=self.buffer_and_play, daemon=True).start()

    def buffer_and_play(self):
        try:
            for f in glob.glob(self.temp_audio_base + ".*"):
                try:
                    os.remove(f)
                except Exception:
                    pass

            with yt_dlp.YoutubeDL({
                'format': 'bestaudio/best',
                'outtmpl': self.temp_audio_base + '.%(ext)s',
                'quiet': True,
                'postprocessors': [{'key': 'FFmpegExtractAudio',
                                    'preferredcodec': 'mp3', 'preferredquality': '192'}],
            }) as ydl:
                ydl.download([self.current_video_url])

            candidates = glob.glob(self.temp_audio_base + ".*")
            if not candidates:
                raise FileNotFoundError("Temp audio not found")
            self.temp_audio = candidates[0]
            time.sleep(0.3)
            pygame.mixer.music.load(self.temp_audio)
            pygame.mixer.music.play()
            def _on_play_started():
                self.btn_play_main.configure(text="⏸")
                self.is_playing   = True
                self.is_paused    = False
                self._seek_offset = 0.0
            self.after(0, _on_play_started)
        except Exception:
            def _on_play_failed():
                self.btn_play_main.configure(text="▶")
                self.is_playing = False
                self.is_paused  = False
            self.after(0, _on_play_failed)

    def update_playback_timer(self):
        if self.is_playing:
            if pygame.mixer.music.get_busy():
                if not self.user_seeking:
                    pos_sec = self._seek_offset + pygame.mixer.music.get_pos() / 1000.0
                    if self.track_duration > 0:
                        pos_sec = min(pos_sec, self.track_duration)
                    e = int(pos_sec)
                    self.lbl_elapsed.configure(text=f"{e // 60:02d}:{e % 60:02d}")
                    if self.track_duration > 0:
                        rem = max(0, int(self.track_duration - pos_sec))
                        self.lbl_remaining.configure(text=f"-{rem // 60:02d}:{rem % 60:02d}")
                        self.playback_slider.set(
                            min(100, (pos_sec / self.track_duration) * 100))
            else:
                self.is_playing = False
                self.is_paused  = False
                self.btn_play_main.configure(text="▶")
                self.playback_slider.set(0)
                self.lbl_elapsed.configure(text="00:00")
                if self.track_duration > 0:
                    total = int(self.track_duration)
                    self.lbl_remaining.configure(
                        text=f"-{total // 60:02d}:{total % 60:02d}")

        self.after(500, self.update_playback_timer)
