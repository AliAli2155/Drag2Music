import tkinter as tk
import customtkinter as ctk
from .translations import LANGUAGES
from .constants import FORMAT_QUALITIES, C


class UISetupMixin:

    def setup_ui(self):
        self.main_frame = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_scroll = self.main_frame

        # ── Header ────────────────────────────────────────────
        hdr = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=28, pady=(14, 4))

        self.lbl_logo_tune = ctk.CTkLabel(
            hdr, text="Tune", font=("Arial", 30, "bold"), text_color=C["tune"])
        self.lbl_logo_tune.pack(side="left")
        self.lbl_fetch = ctk.CTkLabel(
            hdr, text="Fetch", font=("Arial", 30, "bold"))
        self.lbl_fetch.pack(side="left")
        ctk.CTkLabel(hdr, text="  Studio", font=("Arial", 13),
                     text_color=C["studio"]).pack(side="left", pady=(9, 0))
        self.lbl_made_by = ctk.CTkLabel(
            hdr, text="  ·  Made by Ali A.",
            font=("Arial", 11), text_color=C["dim"])
        self.lbl_made_by.pack(side="left", pady=(9, 0))

        self.btn_settings = ctk.CTkButton(
            hdr, text="⚙", font=("Arial", 16), width=38, height=38,
            corner_radius=10,
            fg_color=C["btn_sec"], hover_color=C["btn_sec_hov"],
            command=self.show_settings_menu)
        self.btn_settings.pack(side="right")
        self.lang_combo = ctk.CTkComboBox(
            hdr, values=LANGUAGES, width=118, height=38,
            command=self.change_language_event)
        self.lang_combo.pack(side="right", padx=(0, 8))
        self.lang_combo.set(self.current_lang)

        # ── Tabs ─────────────────────────────────────────────
        self.tabs = ctk.CTkTabview(self.main_frame, corner_radius=16)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 8))
        # Tab names use current language at startup (CTkTabview can't rename after creation)
        _t = self.t if callable(getattr(self, 't', None)) else lambda k: k
        self.tab_down = self.tabs.add(_t("tab_download") or "📥 Download")
        self.tab_conv = self.tabs.add(_t("tab_converter") or "🔄 Converter")
        self.tab_play = self.tabs.add(_t("tab_library")  or "🎶 Library")

        self.setup_download_tab()
        self.setup_converter_tab()
        self.setup_library_tab()
        self._setup_scroll_isolation()

    # ── Download Tab ──────────────────────────────────────────────────────────

    def setup_download_tab(self):
        self.tab_down.grid_columnconfigure(0, weight=1)
        p = self.tab_down

        # ── Search ───────────────────────────────────────────
        sf = ctk.CTkFrame(p, fg_color="transparent")
        sf.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        sf.grid_columnconfigure(0, weight=1)
        self.url_entry = ctk.CTkEntry(
            sf, height=44, corner_radius=12, border_width=1,
            border_color=C["border3"], fg_color=C["card"], font=("Arial", 13),
            placeholder_text="Search song or paste YouTube / SoundCloud URL...")
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.url_entry.bind("<Return>", lambda *_: self.start_analysis_thread())
        self.btn_search = ctk.CTkButton(
            sf, text="🔍  Analyze", width=120, height=44,
            corner_radius=12, font=("Arial", 13, "bold"),
            command=self.start_analysis_thread)
        self.btn_search.grid(row=0, column=1, padx=(0, 6))
        self.btn_clear = ctk.CTkButton(
            sf, text="✕", width=44, height=44,
            corner_radius=12, font=("Arial", 14, "bold"),
            fg_color=C["btn_sec"], hover_color=C["btn_sec_hov"],
            text_color=C["dim"], command=self.clear_search)
        self.btn_clear.grid(row=0, column=2)

        # ── Preview + Lyrics ──────────────────────────────────
        mf = ctk.CTkFrame(p, fg_color="transparent")
        mf.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        mf.grid_columnconfigure(0, weight=2)   # cover gets 2/5 width
        mf.grid_columnconfigure(1, weight=3)   # lyrics gets 3/5 width

        # Cover / preview card
        self.preview_frame = ctk.CTkFrame(
            mf, height=120, corner_radius=16,
            fg_color=C["card"], border_width=1, border_color=C["border2"])
        self.preview_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.preview_frame.grid_propagate(False)
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.preview_frame.grid_rowconfigure(0, weight=1)

        self.thumb_label = ctk.CTkLabel(
            self.preview_frame, text="🎵\nReady to analyze",
            text_color=C["very_dim"], font=("Arial", 13))
        self.thumb_label.grid(row=0, column=0)

        self.thumb_img = tk.Label(
            self.preview_frame, bg="#141414",
            borderwidth=0, highlightthickness=0)
        self.thumb_img.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.thumb_img.lower()

        self.lbl_title = ctk.CTkLabel(
            self.preview_frame, text="",
            font=("Arial", 11, "bold"), wraplength=280, text_color=C["bright"])
        self.lbl_title.place(relx=0.5, rely=0.88, anchor="center")

        self.lbl_source_badge = ctk.CTkLabel(
            self.preview_frame, text="",
            font=("Arial", 9, "bold"), text_color="white",
            fg_color="transparent", corner_radius=5, height=18)
        self.lbl_source_badge.place(x=8, y=8)

        # Lyrics card (wider)
        self.lyrics_frame = ctk.CTkScrollableFrame(
            mf, height=120, corner_radius=16,
            fg_color=C["card"], border_color=C["border2"], border_width=1,
            label_text="📜 Lyrics")
        self.lyrics_frame.grid(row=0, column=1, sticky="nsew")
        self.lyrics_frame.grid_columnconfigure(0, weight=1)
        self.lbl_lyrics = ctk.CTkLabel(
            self.lyrics_frame,
            text="Analyze a song to load lyrics automatically...",
            wraplength=480, text_color=C["very_dim"], justify="left",
            font=("Arial", 12))
        self.lbl_lyrics.pack(pady=12, padx=12, fill="x", expand=True)

        # ── Format / Quality / Path  (compact single area) ───
        controls = ctk.CTkFrame(p, fg_color=C["card"],
                                corner_radius=14, border_width=1,
                                border_color=C["border2"])
        controls.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 6))
        controls.grid_columnconfigure(1, weight=1)
        controls.grid_columnconfigure(3, weight=1)

        # Row A: Format + Quality
        self.lbl_format_dl = ctk.CTkLabel(
            controls, text="Format", font=("Arial", 10), text_color=C["dim"])
        self.lbl_format_dl.grid(
            row=0, column=0, sticky="w", padx=(14, 6), pady=(10, 2))

        self.mode_menu = ctk.CTkOptionMenu(
            controls, values=list(FORMAT_QUALITIES.keys()),
            height=36, corner_radius=10, font=("Arial", 12),
            command=self.update_quality_options)
        self.mode_menu.grid(row=0, column=1, sticky="ew",
                            padx=(0, 16), pady=(10, 2))

        self.lbl_quality_dl = ctk.CTkLabel(
            controls, text="Quality", font=("Arial", 10), text_color=C["dim"])
        self.lbl_quality_dl.grid(
            row=0, column=2, sticky="w", padx=(0, 6), pady=(10, 2))
        self.quality_combo = ctk.CTkComboBox(
            controls, height=36, corner_radius=10, font=("Arial", 12))
        self.quality_combo.grid(row=0, column=3, sticky="ew",
                                padx=(0, 14), pady=(10, 2))
        self.update_quality_options(list(FORMAT_QUALITIES.keys())[0])

        # Thin divider
        ctk.CTkFrame(controls, height=1,
                     fg_color=C["border"]).grid(
            row=1, column=0, columnspan=4, sticky="ew",
            padx=12, pady=(4, 4))

        # Row B: Path
        path_inner = ctk.CTkFrame(controls, fg_color="transparent")
        path_inner.grid(row=2, column=0, columnspan=4,
                        sticky="ew", padx=10, pady=(0, 10))
        path_inner.grid_columnconfigure(0, weight=1)

        self.path_frame = path_inner          # alias used in update_path_display
        self.path_entry = ctk.CTkEntry(
            path_inner, border_width=0, fg_color="transparent",
            font=("Arial", 12), text_color=C["mid"])
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(4, 8))
        self.update_path_display()
        self.btn_path = ctk.CTkButton(
            path_inner, text="📁  Change", width=120, height=30,
            corner_radius=8, font=("Arial", 11, "bold"),
            command=self.select_folder)
        self.btn_path.grid(row=0, column=1)

        # ── Download button ───────────────────────────────────
        self.btn_download = ctk.CTkButton(
            p, text="⬇   ADD TO LIBRARY",
            height=46, corner_radius=23,
            font=("Arial", 14, "bold"), state="disabled",
            command=self.enqueue_current)
        self.btn_download.grid(row=3, column=0, sticky="ew",
                               padx=30, pady=(0, 4))

        # ── Progress (inside tab, right below button) ─────────
        prog = ctk.CTkFrame(p, fg_color="transparent")
        prog.grid(row=4, column=0, sticky="ew", padx=12, pady=(4, 2))
        prog.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(
            prog, height=10, corner_radius=5,
            fg_color=("#d0d0d0", "#252525"))
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=0, sticky="ew")

        self.lbl_speed = ctk.CTkLabel(
            prog, text=" ", font=("Arial", 9), text_color="#888")
        self.lbl_speed.grid(row=1, column=0, pady=(1, 0))

        self.progress_bar_pl = ctk.CTkProgressBar(
            prog, height=10, corner_radius=5,
            fg_color=("#d0d0d0", "#252525"))
        self.progress_bar_pl.set(0)
        self.progress_bar_pl.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        self.progress_bar_pl.grid_remove()

        self.lbl_pl_progress = ctk.CTkLabel(
            prog, text="", font=("Arial", 9), text_color=C["dim"])
        self.lbl_pl_progress.grid(row=3, column=0, pady=(1, 0))
        self.lbl_pl_progress.grid_remove()



    # ── Library Tab ───────────────────────────────────────────────────────────

    def setup_library_tab(self):
        self.tab_play.grid_columnconfigure(0, weight=1)
        self.tab_play.grid_rowconfigure(1, weight=1)
        hdr = ctk.CTkFrame(self.tab_play, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 4))
        self.lbl_collection = ctk.CTkLabel(
            hdr, text="MY COLLECTION",
            font=("Arial", 13, "bold"), text_color=C["dim"])
        self.lbl_collection.pack(side="left")
        self.lib_scroll = ctk.CTkScrollableFrame(
            self.tab_play, fg_color="transparent", border_width=0)
        self.lib_scroll.grid(row=1, column=0, sticky="nsew",
                             padx=18, pady=(0, 14))
        self.refresh_library_ui()

    # ── Converter Tab ─────────────────────────────────────────────────────────

    def setup_converter_tab(self):
        self.tab_conv.grid_columnconfigure(0, weight=1)
        self.lbl_conv_title = ctk.CTkLabel(
            self.tab_conv, text="Local File Converter",
            font=("Arial", 20, "bold"), text_color=C["bright"])
        self.lbl_conv_title.pack(pady=(28, 4))
        self.lbl_conv_subtitle = ctk.CTkLabel(
            self.tab_conv,
            text="Convert any audio or video file to a different format",
            font=("Arial", 12), text_color=C["dim"])
        self.lbl_conv_subtitle.pack(pady=(0, 16))
        self.btn_conv_select = ctk.CTkButton(
            self.tab_conv, text="📁   Select File to Convert",
            height=50, corner_radius=12, font=("Arial", 13, "bold"),
            command=self.select_local_file)
        self.btn_conv_select.pack(pady=4, padx=70, fill="x")
        fmt_row = ctk.CTkFrame(self.tab_conv, fg_color="transparent")
        fmt_row.pack(pady=12)
        self.lbl_conv_target = ctk.CTkLabel(
            fmt_row, text="Target Format:", font=("Arial", 12),
            text_color=C["dim"])
        self.lbl_conv_target.pack(side="left", padx=(0, 10))
        self.conv_target = ctk.CTkSegmentedButton(
            fmt_row,
            values=["MP3", "AAC", "WAV", "FLAC", "OGG", "MP4", "MKV"],
            command=self._on_conv_fmt_change)
        self.conv_target.pack(side="left")
        self.conv_target.set("MP3")
        self.conv_qual_frame = ctk.CTkFrame(self.tab_conv, fg_color="transparent")
        self.conv_qual_frame.pack(pady=4)
        self.lbl_conv_quality_label = ctk.CTkLabel(
            self.conv_qual_frame, text="Quality:",
            font=("Arial", 12), text_color=C["dim"])
        self.lbl_conv_quality_label.pack(side="left", padx=(0, 8))
        self.conv_quality_combo = ctk.CTkComboBox(
            self.conv_qual_frame,
            values=["320 kbps", "256 kbps", "192 kbps", "128 kbps"],
            width=200, height=40, corner_radius=10)
        self.conv_quality_combo.pack(side="left")
        self.conv_quality_combo.set("320 kbps")
        self.conv_status_label = ctk.CTkLabel(
            self.tab_conv, text="", text_color=C["mid"], font=("Arial", 11))
        self.conv_status_label.pack(pady=6)
        self.btn_conv_run = ctk.CTkButton(
            self.tab_conv, text="▶   START CONVERSION",
            height=52, corner_radius=26, font=("Arial", 14, "bold"),
            fg_color=C["btn_conv"], border_width=1,
            border_color=C["btn_conv_brd"],
            text_color=C["bright"], command=self.start_conversion_thread)
        self.btn_conv_run.pack(pady=14, padx=70, fill="x")

    def _on_conv_fmt_change(self, value):
        if value in {"MP3", "AAC", "WAV", "FLAC", "OGG"}:
            self.conv_qual_frame.pack(pady=4)
        else:
            self.conv_qual_frame.pack_forget()

    # ── Scroll isolation ──────────────────────────────────────────────────────

    def _setup_scroll_isolation(self):
        def _make_scroll(canvas):
            return lambda e: canvas.yview_scroll(
                int(-1 * (e.delta / 120)), "units")

        def _bind_inner(frame):
            fn = _make_scroll(frame._parent_canvas)
            frame.bind("<Enter>", lambda _:
                       frame._parent_canvas.bind_all("<MouseWheel>", fn))
            frame.bind("<Leave>", lambda _:
                       frame._parent_canvas.unbind_all("<MouseWheel>"))

        for frame in (self.lyrics_frame, self.lib_scroll):
            _bind_inner(frame)
