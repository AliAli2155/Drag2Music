# -*- coding: utf-8 -*-
# ── PyInstaller frozen-bundle ffmpeg path injection ──────────────────────────
import sys as _sys, os as _os
if getattr(_sys, 'frozen', False):
    _base = _sys._MEIPASS
    if _sys.platform == 'win32':
        _ffmpeg = _os.path.join(_base, 'ffmpeg_bins', 'windows', 'ffmpeg.exe')
    elif _sys.platform == 'darwin':
        _ffmpeg = _os.path.join(_base, 'ffmpeg_bins', 'macos', 'ffmpeg')
    else:
        _ffmpeg = _os.path.join(_base, 'ffmpeg_bins', 'linux', 'ffmpeg')
    _os.environ['PATH'] = _os.path.dirname(_ffmpeg) + _os.pathsep + _os.environ.get('PATH', '')
    _os.environ['FFMPEG_BINARY'] = _ffmpeg
del _sys, _os
# ─────────────────────────────────────────────────────────────────────────────
import customtkinter as ctk
import sys, os, json, requests, threading
from tkinter import filedialog
from PIL import Image
from io import BytesIO
import pygame
import yt_dlp

from core.translations import TRANSLATIONS
from core.constants import FORMAT_QUALITIES, THEME_COLORS, C
from core.ui_setup import UISetupMixin
from core.player import PlayerMixin
from core.downloader import DownloaderMixin
from core.lyrics import LyricsMixin
from core.converter import ConverterMixin

try:
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.mixer.init()
except Exception:
    pass


class TuneFetch(UISetupMixin, PlayerMixin, DownloaderMixin, LyricsMixin, ConverterMixin, ctk.CTk):

    def __init__(self):
        self.history_file    = os.path.join(os.path.expanduser("~"), ".tunefetch_history.json")
        self.download_path   = os.path.join(os.path.expanduser("~"), "Downloads")
        self.temp_audio_base = os.path.join(os.path.expanduser("~"), "tf_preview")
        self.temp_audio      = self.temp_audio_base + ".mp3"

        from core.translations import LANGUAGES as _LANGS
        saved_data = self.load_data_from_disk()
        self.download_history    = saved_data.get("history", [])
        _lang                    = saved_data.get("language", "English")
        self.current_lang        = _lang if _lang in _LANGS else "English"
        self.current_theme_color = saved_data.get("theme", "#1DB954")
        _mode                    = saved_data.get("mode", "Dark")
        self.current_mode        = _mode if _mode in ("Dark", "Light") else "Dark"
        ctk.set_appearance_mode(self.current_mode)

        self.current_video_url   = ""
        self.current_video_title = ""
        self.current_video_info  = {}
        self.track_duration      = 0
        self.selected_local_file = ""
        self._thumb_ctk_img      = None

        self.is_playing   = False
        self.is_paused    = False
        self.user_seeking = False
        self._seek_job    = None
        self._seek_offset = 0.0

        super().__init__()

        self.title("TuneFetch: Infinity Studio")
        self.geometry("1200x1040")

        # Window icon — works both in dev mode and as frozen bundle
        _here = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        for _ico in (os.path.join(_here, 'assets', 'icon.ico'),
                     os.path.join(_here, 'TuneFetch.ico')):
            if os.path.exists(_ico):
                try:
                    self.iconbitmap(_ico)
                except Exception:
                    pass
                break
        self.minsize(900, 720)
        self.configure(fg_color=C["bg"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_ui()
        self.update_ui_language()
        self.apply_theme_color(self.current_theme_color)
        self.update_playback_timer()

    # ══════════════════ HELPERS ══════════════════

    def t(self, key):
        return TRANSLATIONS[self.current_lang].get(key, key)

    # ══════════════════ ANALYSIS ══════════════════

    def start_analysis_thread(self):
        q = self.url_entry.get().strip()
        if len(q) > 2:
            threading.Thread(target=self.analyze_video, args=(q,), daemon=True).start()

    def analyze_video(self, q):
        self.after(0, lambda: self.btn_search.configure(state="disabled", text=self.t("analyzing")))
        self.after(0, lambda: self.thumb_label.configure(text=self.t("loading"), image=None))
        try:
            sq = q if q.startswith("http") else f"ytsearch1:{q}"
            with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
                info = ydl.extract_info(sq, download=False)
                if 'entries' in info:
                    info = info['entries'][0]

            self.current_video_url   = info['webpage_url']
            self.current_video_title = info['title']
            self.track_duration      = info.get('duration', 0) or 0
            self.current_video_info  = info
            self.is_paused = False

            vid_id    = info.get('id', '')
            thumb_url = (f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"
                         if vid_id else info.get('thumbnail', ''))
            try:
                thumb_data = requests.get(thumb_url, timeout=5).content
            except Exception:
                thumb_data = requests.get(info.get('thumbnail', ''), timeout=8).content
            img = Image.open(BytesIO(thumb_data)).resize((310, 172))
            self._thumb_ctk_img = ctk.CTkImage(img, size=(310, 172))
            ttxt  = info['title'][:65]
            total = int(self.track_duration)
            short = info['title'][:52] + "…" if len(info['title']) > 52 else info['title']

            self.after(0, lambda: self.thumb_label.configure(image=self._thumb_ctk_img, text=""))
            self.after(0, lambda: self.lbl_title.configure(text=ttxt))
            self.after(0, lambda: self.btn_download.configure(state="normal"))
            self.after(0, lambda: self.lbl_elapsed.configure(text="00:00"))
            self.after(0, lambda: self.lbl_remaining.configure(
                text=f"-{total // 60:02d}:{total % 60:02d}"))
            self.after(0, lambda: self.playback_slider.set(0))
            # C["mid"] tuple — CTk picks right color automatically
            self.after(0, lambda: self.lbl_now_playing.configure(
                text=f"♪  {short}", text_color=C["mid"]))

            threading.Thread(
                target=self.auto_find_lyrics,
                args=(info['title'], info['webpage_url']),
                daemon=True).start()
        except Exception:
            self.after(0, lambda: self.thumb_label.configure(
                text=self.t("analysis_failed"), image=None))
        finally:
            self.after(0, lambda: self.btn_search.configure(
                state="normal", text=self.t("search_btn")))

    # ══════════════════ LIBRARY ══════════════════

    def refresh_library_ui(self):
        for w in self.lib_scroll.winfo_children():
            w.destroy()
        if not self.download_history:
            ctk.CTkLabel(
                self.lib_scroll, text=self.t("library_empty"),
                font=("Arial", 14), text_color=C["very_dim"],
                justify="center").pack(pady=70)
        else:
            for item in reversed(self.download_history):
                card = ctk.CTkFrame(
                    self.lib_scroll, height=54, corner_radius=14,
                    fg_color=C["card"], border_width=1, border_color=C["border2"])
                card.pack(fill="x", pady=3, padx=4)
                card.grid_columnconfigure(1, weight=1)

                fmt      = item.get("format", "?")
                is_audio = fmt in {"MP3", "AAC", "OGG", "WAV", "FLAC", "OPUS"}
                tag_clr  = self.current_theme_color if is_audio else "#3498db"

                ctk.CTkLabel(
                    card, text=f" {fmt} ",
                    font=("Arial", 10, "bold"), text_color=tag_clr,
                    fg_color=C["tag_bg"], corner_radius=6,
                    width=44, height=22).grid(row=0, column=0, padx=(12, 8), pady=16)
                ctk.CTkLabel(
                    card, text=item["name"],
                    font=("Arial", 12), text_color=C["mid"],
                    anchor="w").grid(row=0, column=1, sticky="w", padx=4)
                ctk.CTkLabel(
                    card, text=item.get("time", ""),
                    font=("Arial", 10), text_color=C["dim"]).grid(
                    row=0, column=2, padx=(4, 14))

    # ══════════════════ SETTINGS ══════════════════

    def show_settings_menu(self):
        if hasattr(self, "settings_popup") and self.settings_popup.winfo_exists():
            self.settings_popup.destroy()
            return
        t = TRANSLATIONS[self.current_lang]
        self.settings_popup = ctk.CTkToplevel(self)
        self.settings_popup.title(t["settings_title"])
        self.settings_popup.geometry("310x600")
        self.settings_popup.resizable(False, False)
        self.settings_popup.attributes("-topmost", True)
        self.settings_popup.configure(fg_color=C["panel"])

        ctk.CTkLabel(self.settings_popup, text=t["settings_title"],
                     font=("Arial", 18, "bold"),
                     text_color=C["bright"]).pack(pady=(24, 14))
        ctk.CTkFrame(self.settings_popup, height=1,
                     fg_color=C["border"]).pack(fill="x", padx=18)

        ctk.CTkButton(self.settings_popup, text=t["settings_clear"],
                      height=44, corner_radius=12,
                      fg_color=C["btn_conv"], border_width=1, border_color=C["border"],
                      text_color="#e74c3c", hover_color=("#fde8e8", "#200e0e"),
                      command=self.clear_history).pack(fill="x", padx=20, pady=(14, 5))

        ctk.CTkFrame(self.settings_popup, height=1,
                     fg_color=C["border"]).pack(fill="x", padx=18, pady=14)
        ctk.CTkLabel(self.settings_popup, text=t["mode_section"],
                     font=("Arial", 12, "bold"),
                     text_color=C["dim"]).pack()
        mode_btn = ctk.CTkSegmentedButton(
            self.settings_popup, values=["🌙 Dark", "☀️ Light"],
            command=self._set_app_appearance_mode)
        mode_btn.pack(fill="x", padx=20, pady=(8, 0))
        mode_btn.set("🌙 Dark" if self.current_mode == "Dark" else "☀️ Light")

        ctk.CTkFrame(self.settings_popup, height=1,
                     fg_color=C["border"]).pack(fill="x", padx=18, pady=14)
        ctk.CTkLabel(self.settings_popup, text=t["settings_theme"],
                     font=("Arial", 12, "bold"),
                     text_color=C["dim"]).pack()
        for n, h in THEME_COLORS:
            ctk.CTkButton(
                self.settings_popup, text=n, fg_color=h, text_color="black",
                height=36, corner_radius=10,
                command=lambda c=h: self.apply_theme_color(c)).pack(
                fill="x", padx=30, pady=3)

    def _set_app_appearance_mode(self, value):
        self.current_mode = "Dark" if value == "🌙 Dark" else "Light"
        ctk.set_appearance_mode(self.current_mode)
        # C tuples make CTk auto-update all static widgets.
        # Only refresh dynamically-built content (library cards).
        self.lbl_now_playing.configure(
            text_color=C["mid"] if self.current_video_url else C["dim"])
        self.refresh_library_ui()
        self.save_data_to_disk()

    def apply_theme_color(self, color):
        self.current_theme_color = color
        for w in [self.lbl_fetch, self.btn_settings]:
            try:
                w.configure(text_color=color)
            except Exception:
                pass
        for w in [self.btn_play_main, self.btn_search, self.btn_path,
                  self.btn_download, self.btn_conv_select]:
            try:
                w.configure(fg_color=color)
            except Exception:
                pass
        for s in [self.playback_slider, self.volume_slider]:
            try:
                s.configure(progress_color=color, button_color=color,
                            button_hover_color=color)
            except Exception:
                pass
        try:
            self.dl_progress.configure(progress_color=color)
        except Exception:
            pass
        try:
            self.tabs.configure(segmented_button_selected_color=color)
        except Exception:
            pass
        self.save_data_to_disk()

    # ══════════════════ UI HELPERS ══════════════════

    def change_volume(self, v):
        pygame.mixer.music.set_volume(float(v))

    def update_quality_options(self, choice):
        vals = FORMAT_QUALITIES.get(choice, ["Default"])
        self.quality_combo.configure(values=vals)
        self.quality_combo.set(vals[0])

    def update_path_display(self):
        self.path_entry.configure(state="normal")
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, self.download_path)
        self.path_entry.configure(state="readonly")

    def select_folder(self):
        f = filedialog.askdirectory()
        if f:
            self.download_path = f
            self.update_path_display()

    def change_language_event(self, n):
        self.current_lang = n
        self.update_ui_language()
        self.save_data_to_disk()

    def update_ui_language(self):
        t = TRANSLATIONS[self.current_lang]

        self.url_entry.configure(placeholder_text=t["search_placeholder"])
        self.btn_search.configure(text=t["search_btn"])
        self.btn_path.configure(text=t["path_btn"])
        self.btn_download.configure(text=t["main_btn"])
        self.lbl_quality_dl.configure(text=t["quality_label"])

        if not self.current_video_url:
            self.lbl_now_playing.configure(text=t["no_track"])
            self.thumb_label.configure(text=t["thumb_ready"])
            self.lbl_lyrics.configure(text=t["lyrics_placeholder"],
                                      text_color=C["very_dim"])
        self.lyrics_frame.configure(label_text=t["lyrics_label"])

        self.lbl_collection.configure(text=t["collection_label"])
        self.refresh_library_ui()

        self.lbl_conv_title.configure(text=t["conv_title"])
        self.lbl_conv_subtitle.configure(text=t["conv_subtitle"])
        self.lbl_conv_target.configure(text=t["conv_target_label"])
        self.lbl_conv_quality_label.configure(text=t["conv_quality_label"])
        self.btn_conv_run.configure(text=t["conv_run"])
        if not self.selected_local_file:
            self.btn_conv_select.configure(text=t["conv_select"])

    # ══════════════════ DATA ══════════════════

    def load_data_from_disk(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_data_to_disk(self):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump({
                "history":  self.download_history,
                "language": self.current_lang,
                "theme":    self.current_theme_color,
                "mode":     self.current_mode,
            }, f, ensure_ascii=False, indent=2)

    def clear_history(self):
        self.download_history = []
        self.save_data_to_disk()
        self.refresh_library_ui()


if __name__ == "__main__":
    TuneFetch().mainloop()
