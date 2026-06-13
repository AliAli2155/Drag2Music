import json
import os
import customtkinter as ctk
from tkinter import filedialog

from .translations import TRANSLATIONS
from .constants import FORMAT_QUALITIES, THEME_COLORS, LOUDNESS_PRESETS, C, FONT


class SettingsMixin:

    # ── Settings popup ────────────────────────────────────────────────────────

    def _close_settings(self):
        sp = getattr(self, '_sp', None)
        if sp is None:
            return
        try:
            if not sp.winfo_exists():
                return
        except Exception:
            return
        if getattr(sp, '_closing', False):
            return
        sp._closing = True

        def _fade_out(step=4):
            try:
                if not sp.winfo_exists():
                    return
                if step <= 0:
                    sp.destroy()
                    return
                sp.attributes("-alpha", step / 5)
                sp.after(16, lambda: _fade_out(step - 1))
            except Exception:
                try:
                    sp.destroy()
                except Exception:
                    pass
        _fade_out()

    def show_settings_menu(self):
        sp = getattr(self, '_sp', None)
        if sp is not None:
            try:
                if sp.winfo_exists():
                    self._close_settings()   # toggle: fade out and dismiss
                    return
            except Exception:
                pass

        t = TRANSLATIONS[self.current_lang]

        popup = ctk.CTkToplevel(self)
        popup.wm_overrideredirect(True)
        popup.configure(fg_color=C["panel"])
        # Border-less toplevels can end up under the main window — keep the
        # menu above everything until it is dismissed. Start fully transparent
        # so it can fade in once positioned.
        try:
            popup.attributes("-topmost", True)
            popup.attributes("-alpha", 0.0)
        except Exception:
            pass
        self._sp = popup

        inner = ctk.CTkFrame(popup, corner_radius=12,
                             fg_color=C["panel"],
                             border_width=1, border_color=C["border"])
        inner.pack(fill="both", expand=True)

        ctk.CTkLabel(inner, text=t["settings_title"],
                     font=(FONT, 15, "bold"),
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
                     font=(FONT, 11, "bold"), text_color=C["dim"]).pack()
        mode_btn = ctk.CTkSegmentedButton(
            inner, values=["🌙 Dark", "☀️ Light"],
            command=self._set_app_appearance_mode)
        mode_btn.pack(fill="x", padx=16, pady=(6, 0))
        mode_btn.set("🌙 Dark" if self.current_mode == "Dark" else "☀️ Light")

        ctk.CTkFrame(inner, height=1, fg_color=C["border"]).pack(fill="x", padx=14, pady=8)
        ctk.CTkLabel(inner, text=t.get("loudness_section", "Audio Normalization"),
                     font=(FONT, 11, "bold"), text_color=C["dim"]).pack()
        loud_menu = ctk.CTkOptionMenu(
            inner, values=list(LOUDNESS_PRESETS.keys()),
            height=34, corner_radius=10, font=(FONT, 11),
            command=self._set_loudness_choice)
        loud_menu.pack(fill="x", padx=16, pady=(6, 0))
        loud_menu.set(getattr(self, "loudness_choice", "Off"))
        ctk.CTkLabel(
            inner,
            text=t.get("loudness_hint",
                       "Levels tracks for DJ sets · 44.1 kHz · audio only"),
            font=(FONT, 9), text_color=C["very_dim"],
            wraplength=230).pack(padx=16, pady=(3, 0))

        ctk.CTkFrame(inner, height=1, fg_color=C["border"]).pack(fill="x", padx=14, pady=8)
        ctk.CTkLabel(inner, text=t["settings_theme"],
                     font=(FONT, 11, "bold"), text_color=C["dim"]).pack()
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
        sw  = self.winfo_screenwidth()
        sh  = self.winfo_screenheight()
        # The settings button lives at the bottom of the sidebar: open the
        # popup to its right, bottom-aligned, clamped to the screen.
        x = bsx + bw + 10
        if x + pw > sw - 8:
            x = max(8, bsx - pw - 10)
        y = max(8, min(bsy + bh - ph, sh - ph - 8))
        popup.geometry(f"{pw}x{ph}+{x}+{y}")

        def _fade_in(step=1):
            try:
                if not popup.winfo_exists() or getattr(popup, '_closing', False):
                    return
                popup.attributes("-alpha", min(1.0, step / 5))
                if step < 5:
                    popup.after(16, lambda: _fade_in(step + 1))
            except Exception:
                pass
        _fade_in()

        _alive   = [True]
        _bind_id = [None]

        def _outside(event):
            if not _alive[0]:
                return
            try:
                if not (popup.winfo_rootx() <= event.x_root <= popup.winfo_rootx() + pw
                        and popup.winfo_rooty() <= event.y_root <= popup.winfo_rooty() + ph):
                    self._close_settings()
            except Exception:
                pass

        def _bind():
            if _alive[0]:
                _bind_id[0] = self.bind_all('<Button-1>', _outside, add=True)

        def _on_destroy(_):
            # Remove the global binding — otherwise each popup open leaks one.
            _alive[0] = False
            fid = _bind_id[0]
            if fid:
                _bind_id[0] = None
                try:
                    # bind_all lives on the 'all' bindtag: strip just our handler
                    script = str(self.tk.call('bind', 'all', '<Button-1>'))
                    kept = '\n'.join(l for l in script.splitlines() if fid not in l)
                    self.tk.call('bind', 'all', '<Button-1>', kept)
                    self.deletecommand(fid)
                except Exception:
                    pass

        self.after(200, _bind)
        popup.bind('<Destroy>', _on_destroy)

    def _set_loudness_choice(self, value):
        self.loudness_choice = value
        self.save_data_to_disk()

    def _set_app_appearance_mode(self, value):
        self.current_mode = "Dark" if value == "🌙 Dark" else "Light"

        def _apply(m=self.current_mode):
            try:
                if not self.winfo_exists():
                    return
            except Exception:
                return
            ctk.set_appearance_mode(m)
            self.save_data_to_disk()
            # Swap the window icon to contrast with the new theme
            try:
                self._apply_window_icon()
            except Exception:
                pass
            # PIL-rendered elements use the mode's background colour —
            # refresh them all for the new mode.
            self._sync_thumb_bg()
            self._render_cover()
            try:
                self._render_idle_art()
                self._draw_sidebar_grad()
                self.refresh_library_ui()
            except Exception:
                pass
            for name in ("progress_bar", "progress_bar_pl"):
                w = getattr(self, name, None)
                if w:
                    try:
                        w._redraw()
                    except Exception:
                        pass
        self.after(10, _apply)

    # ── Theme ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _darken(hex_color, f=0.78):
        """Return a darker shade of a #rrggbb colour (for hover states)."""
        try:
            h = hex_color.lstrip('#')
            r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
            return f"#{int(r*f):02x}{int(g*f):02x}{int(b*f):02x}"
        except Exception:
            return hex_color

    def apply_theme_color(self, color, animate=True):
        """Set the accent colour; animates a smooth blend from the previous
        accent (~210 ms) when the UI is already built."""
        old = getattr(self, "current_theme_color", None)
        self.current_theme_color = color

        job = getattr(self, "_accent_anim_job", None)
        if job is not None:
            try:
                self.after_cancel(job)
            except Exception:
                pass
            self._accent_anim_job = None

        if (not animate or not old or old == color
                or not hasattr(self, "nav_buttons")):
            self._apply_accent(color)
            self.save_data_to_disk()
            return

        steps = 8

        def _tick(i=1):
            self._accent_anim_job = None
            try:
                self._apply_accent(self._mix_hex(old, color, i / steps))
            except Exception:
                return
            if i < steps:
                self._accent_anim_job = self.after(26, lambda: _tick(i + 1))
            else:
                self.save_data_to_disk()
        _tick()

    def _apply_accent(self, color):
        hover = self._darken(color)

        for name in ("lbl_music", "btn_settings"):
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
                    w.configure(fg_color=color, hover_color=hover)
                except Exception:
                    pass

        for name in ("progress_bar", "progress_bar_pl"):
            w = getattr(self, name, None)
            if w:
                try:
                    w.configure(progress_color=color)
                except Exception:
                    pass

        # Sidebar: active nav button follows the accent
        if hasattr(self, "nav_buttons"):
            try:
                self._restyle_nav(color, hover)
            except Exception:
                pass

        # Dropdowns / segmented controls follow the accent too
        w = getattr(self, "conv_target", None)
        if w:
            try:
                w.configure(selected_color=color, selected_hover_color=hover)
            except Exception:
                pass
        for name in ("mode_menu", "quality_combo"):
            w = getattr(self, name, None)
            if w:
                try:
                    w.configure(border_color=color, button_color=color,
                                button_hover_color=hover)
                except Exception:
                    pass

        # Gradient elements follow the accent
        try:
            self._draw_sidebar_grad()
        except Exception:
            pass
        try:
            self._render_idle_art()   # no-op when a cover is displayed
        except Exception:
            pass
        # Library format tags follow the accent (canvas redraw is cheap)
        try:
            self.refresh_library_ui()
        except Exception:
            pass

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
            self.save_data_to_disk()   # persist across sessions

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
        _safe("cancel_btn",         text=t.get("cancel_download", "✕  Cancel"))
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
            try:
                self._render_idle_art()   # placeholder text in new language
            except Exception:
                pass
            _safe("lbl_lyrics",  text=t["lyrics_placeholder"],
                  text_color=C["very_dim"])
        if not self.selected_local_file:
            _safe("btn_conv_select", text=t["conv_select"])

        if hasattr(self, "nav_buttons"):
            self._set_nav_texts()

        # Library cards contain no translated text — only the empty-state
        # placeholder needs a refresh. Skipping the full rebuild keeps
        # language switching instant even with a 150-card history.
        if not self.download_history:
            self.refresh_library_ui()

    # ── Library UI ────────────────────────────────────────────────────────────

    def refresh_library_ui(self):
        """Mark the library stale; rebuild immediately only when visible.
        Keeps startup and language/theme switches instant."""
        self._lib_dirty = True
        if getattr(self, "_active_page", "") == "library":
            self._build_library_now()

    def _ensure_library_rendered(self):
        if getattr(self, "_lib_dirty", True):
            self._build_library_now()

    @staticmethod
    def _fmt_size(nbytes):
        try:
            nbytes = int(nbytes)
        except (TypeError, ValueError):
            return ""
        if nbytes >= 1024 ** 3:
            return f"{nbytes / 1024 ** 3:.2f} GB"
        if nbytes >= 1024 ** 2:
            return f"{nbytes / 1024 ** 2:.1f} MB"
        return f"{nbytes / 1024:.0f} KB"

    def _build_library_now(self):
        """Push the newest 150 entries to the canvas-based list (instant)."""
        self._lib_dirty = False

        count = len(self.download_history)
        lbl_count = getattr(self, "lbl_lib_count", None)
        if lbl_count is not None:
            try:
                lbl_count.configure(text=f"{count} ♪" if count else "")
            except Exception:
                pass

        rows = []
        for item in reversed(self.download_history[-150:]):
            fmt = item.get("format", "?")
            # Detail line: quality · size · duration · source — old entries
            # may miss fields, show whatever is available.
            meta = []
            if item.get("quality"):
                meta.append(str(item["quality"]))
            size_s = self._fmt_size(item.get("size"))
            if size_s:
                meta.append(size_s)
            dur = item.get("duration")
            if dur:
                d = int(dur)
                meta.append(f"{d // 3600}:{(d % 3600) // 60:02d}:{d % 60:02d}"
                            if d >= 3600 else f"{d // 60}:{d % 60:02d}")
            if item.get("source"):
                meta.append(str(item["source"]))
            when = item.get("time", "")
            if item.get("date"):
                when = f"{item['date']}  {when}"
            rows.append({
                "tag":       fmt,
                "tag_audio": fmt in {"MP3", "AAC", "OGG", "WAV",
                                     "FLAC", "OPUS"},
                "name":      item.get("name", "?"),
                "meta":      "  ·  ".join(meta),
                "when":      when,
            })

        try:
            self.lib_scroll.set_items(rows, self.current_theme_color,
                                      self.t("library_empty"))
            self.lib_scroll.yview_moveto(0)
        except Exception as e:
            print(f"[Library] render error: {e}")

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
        # Atomic write: a crash mid-write can never corrupt the user's data.
        tmp = self.history_file + ".tmp"
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump({
                    "history":       self.download_history,
                    "language":      self.current_lang,
                    "theme":         self.current_theme_color,
                    "mode":          self.current_mode,
                    "loudness":      getattr(self, "loudness_choice", "Off"),
                    "sample_rate":   getattr(self, "target_sr", 44100),
                    "download_path": self.download_path,
                }, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.history_file)
        except Exception as e:
            print(f"[Data] Save error: {e}")
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass

    def clear_history(self):
        self.download_history = []
        self.save_data_to_disk()
        self.refresh_library_ui()
