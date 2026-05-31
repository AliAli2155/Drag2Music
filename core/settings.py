import json
import os
import customtkinter as ctk
from tkinter import filedialog

from .translations import TRANSLATIONS
from .constants import FORMAT_QUALITIES, THEME_COLORS, C


class SettingsMixin:

    # ── Settings popup ────────────────────────────────────────────────────────

    def _close_settings(self):
        if hasattr(self, '_sp') and self._sp.winfo_exists():
            self._sp.destroy()

    def show_settings_menu(self):
        if hasattr(self, '_sp') and self._sp.winfo_exists():
            self._sp.destroy()
            return

        t = TRANSLATIONS[self.current_lang]

        popup = ctk.CTkToplevel(self)
        popup.wm_overrideredirect(True)
        popup.configure(fg_color=C["panel"])
        self._sp = popup

        inner = ctk.CTkFrame(popup, corner_radius=12,
                             fg_color=C["panel"],
                             border_width=1, border_color=C["border"])
        inner.pack(fill="both", expand=True)

        ctk.CTkLabel(inner, text=t["settings_title"],
                     font=("Arial", 15, "bold"),
                     text_color=C["bright"]).pack(pady=(16, 8), padx=16)
        ctk.CTkFrame(inner, height=1, fg_color=C["border"]).pack(fill="x", padx=14)

        ctk.CTkButton(
            inner, text=t["settings_clear"],
            height=38, corner_radius=10,
            fg_color=C["btn_conv"], border_width=1, border_color=C["border"],
            text_color="#e74c3c", hover_color=("#fde8e8", "#200e0e"),
            command=lambda: (self.clear_history(), self._close_settings())
        ).pack(fill="x", padx=16, pady=(10, 4))

        ctk.CTkFrame(inner, height=1, fg_color=C["border"]).pack(fill="x", padx=14, pady=8)
        ctk.CTkLabel(inner, text=t["mode_section"],
                     font=("Arial", 11, "bold"), text_color=C["dim"]).pack()
        mode_btn = ctk.CTkSegmentedButton(
            inner, values=["🌙 Dark", "☀️ Light"],
            command=self._set_app_appearance_mode)
        mode_btn.pack(fill="x", padx=16, pady=(6, 0))
        mode_btn.set("🌙 Dark" if self.current_mode == "Dark" else "☀️ Light")

        ctk.CTkFrame(inner, height=1, fg_color=C["border"]).pack(fill="x", padx=14, pady=8)
        ctk.CTkLabel(inner, text=t["settings_theme"],
                     font=("Arial", 11, "bold"), text_color=C["dim"]).pack()
        for n, h in THEME_COLORS:
            ctk.CTkButton(
                inner, text=n, fg_color=h, text_color="black",
                height=32, corner_radius=8,
                command=lambda c=h: (self.apply_theme_color(c), self._close_settings())
            ).pack(fill="x", padx=24, pady=2)

        ctk.CTkFrame(inner, height=8, fg_color="transparent").pack()

        popup.update_idletasks()
        pw  = 270
        ph  = popup.winfo_reqheight()
        bsx = self.btn_settings.winfo_rootx()
        bsy = self.btn_settings.winfo_rooty()
        bh  = self.btn_settings.winfo_height()
        bw  = self.btn_settings.winfo_width()
        popup.geometry(f"{pw}x{ph}+{bsx + bw - pw}+{bsy + bh + 4}")

        _alive = [True]

        def _outside(event):
            if not _alive[0]:
                return
            try:
                if not (popup.winfo_rootx() <= event.x_root <= popup.winfo_rootx() + pw
                        and popup.winfo_rooty() <= event.y_root <= popup.winfo_rooty() + ph):
                    self._close_settings()
            except Exception:
                pass

        def _on_destroy(_):
            _alive[0] = False   # disables handler without touching other bindings

        self.after(200, lambda: self.bind_all('<Button-1>', _outside, add=True))
        popup.bind('<Destroy>', _on_destroy)

    def _set_app_appearance_mode(self, value):
        self.current_mode = "Dark" if value == "🌙 Dark" else "Light"
        self.after(10, lambda m=self.current_mode: (
            ctk.set_appearance_mode(m),
            self.save_data_to_disk()
        ))

    # ── Theme ─────────────────────────────────────────────────────────────────

    def apply_theme_color(self, color):
        self.current_theme_color = color

        for name in ("lbl_fetch", "btn_settings"):
            w = getattr(self, name, None)
            if w:
                try:
                    w.configure(text_color=color)
                except Exception:
                    pass

        for name in ("btn_search", "btn_path", "btn_download", "btn_conv_select"):
            w = getattr(self, name, None)
            if w:
                try:
                    w.configure(fg_color=color)
                except Exception:
                    pass

        for name in ("progress_bar", "progress_bar_pl"):
            w = getattr(self, name, None)
            if w:
                try:
                    w.configure(progress_color=color)
                except Exception:
                    pass

        w = getattr(self, "tabs", None)
        if w:
            try:
                w.configure(segmented_button_selected_color=color)
            except Exception:
                pass

        self.save_data_to_disk()

    # ── UI helpers ────────────────────────────────────────────────────────────

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

        def _safe(widget_name, **kw):
            w = getattr(self, widget_name, None)
            if w is not None:
                try:
                    w.configure(**kw)
                except Exception:
                    pass

        _safe("url_entry",          placeholder_text=t["search_placeholder"])
        _safe("btn_search",         text=t["search_btn"])
        _safe("btn_path",           text=t.get("path_btn", "📁  Change"))
        _safe("lbl_format_dl",      text=t.get("format_label", "Format"))
        _safe("lbl_quality_dl",     text=t["quality_label"])
        _safe("lyrics_frame",       label_text=t["lyrics_label"])
        _safe("lbl_collection",     text=t["collection_label"])
        _safe("lbl_conv_title",     text=t["conv_title"])
        _safe("lbl_conv_subtitle",  text=t["conv_subtitle"])
        _safe("lbl_conv_target",    text=t["conv_target_label"])
        _safe("lbl_conv_quality_label", text=t["conv_quality_label"])
        _safe("btn_conv_run",       text=t["conv_run"])

        if self._pending_playlist is None:
            _safe("btn_download", text=t["main_btn"])
        if not self.current_video_url:
            _safe("thumb_label", text=t["thumb_ready"])
            _safe("lbl_lyrics",  text=t["lyrics_placeholder"],
                  text_color=C["very_dim"])
        if not self.selected_local_file:
            _safe("btn_conv_select", text=t["conv_select"])

        self.refresh_library_ui()

    # ── Library UI ────────────────────────────────────────────────────────────

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

                fmt     = item.get("format", "?")
                is_audio = fmt in {"MP3", "AAC", "OGG", "WAV", "FLAC", "OPUS"}
                tag_clr = self.current_theme_color if is_audio else "#3498db"

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

    # ── Data persistence ──────────────────────────────────────────────────────

    def load_data_from_disk(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_data_to_disk(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "history":  self.download_history,
                    "language": self.current_lang,
                    "theme":    self.current_theme_color,
                    "mode":     self.current_mode,
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Data] Save error: {e}")

    def clear_history(self):
        self.download_history = []
        self.save_data_to_disk()
        self.refresh_library_ui()
