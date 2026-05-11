import customtkinter as ctk
from .translations import LANGUAGES
from .constants import FORMAT_QUALITIES, C


class UISetupMixin:

    def setup_ui(self):
        self.main_scroll = ctk.CTkScrollableFrame(
            self, fg_color=C["bg"], corner_radius=0)
        self.main_scroll.grid(row=0, column=0, sticky="nsew")
        self.main_scroll.grid_columnconfigure(0, weight=1)

        # ── Top Bar ──────────────────────────────────────────
        self.top_bar = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, sticky="ew", padx=30, pady=(15, 5))
        self.btn_settings = ctk.CTkButton(
            self.top_bar, text="⚙", font=("Arial", 18), width=42, height=42,
            corner_radius=12, command=self.show_settings_menu)
        self.btn_settings.pack(side="right", padx=5)
        self.lang_combo = ctk.CTkComboBox(
            self.top_bar, values=LANGUAGES, width=130, height=42,
            command=self.change_language_event)
        self.lang_combo.pack(side="right", padx=5)
        self.lang_combo.set(self.current_lang)

        # ── Logo ─────────────────────────────────────────────
        logo_row = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        logo_row.grid(row=1, column=0, pady=(0, 4))
        self.lbl_logo_tune = ctk.CTkLabel(
            logo_row, text="Tune", font=("Arial", 44, "bold"), text_color=C["tune"])
        self.lbl_logo_tune.pack(side="left")
        self.lbl_fetch = ctk.CTkLabel(logo_row, text="Fetch", font=("Arial", 44, "bold"))
        self.lbl_fetch.pack(side="left")
        self.lbl_logo_studio = ctk.CTkLabel(
            logo_row, text=" Studio", font=("Arial", 18), text_color=C["studio"])
        self.lbl_logo_studio.pack(side="left", pady=(14, 0))

        # ── Player Bar ───────────────────────────────────────
        self.audio_panel = ctk.CTkFrame(
            self.main_scroll, height=112, corner_radius=22,
            fg_color=C["panel"], border_width=1, border_color=C["border"])
        self.audio_panel.grid(row=2, column=0, sticky="ew", padx=30, pady=8)
        self.audio_panel.grid_propagate(False)
        self.audio_panel.grid_columnconfigure(1, weight=1)
        self.audio_panel.grid_rowconfigure(0, weight=1)

        left_ctrl = ctk.CTkFrame(self.audio_panel, fg_color="transparent")
        left_ctrl.grid(row=0, column=0, padx=(18, 6), sticky="ns")
        left_ctrl.grid_rowconfigure(0, weight=1)
        left_ctrl.grid_columnconfigure(0, weight=1)

        btn_row = ctk.CTkFrame(left_ctrl, fg_color="transparent")
        btn_row.grid(row=0, column=0)

        self.btn_prev = ctk.CTkButton(
            btn_row, text="⏮", width=32, height=32, corner_radius=16,
            fg_color=C["btn_sec"], hover_color=C["btn_sec_hov"],
            text_color=C["mid"], font=("Arial", 13), command=lambda: None)
        self.btn_prev.pack(side="left", padx=(0, 6))

        self.btn_play_main = ctk.CTkButton(
            btn_row, text="▶", width=50, height=50, corner_radius=25,
            text_color="black", font=("Arial", 17, "bold"), command=self.toggle_playback)
        self.btn_play_main.pack(side="left", padx=3)

        self.btn_next = ctk.CTkButton(
            btn_row, text="⏭", width=32, height=32, corner_radius=16,
            fg_color=C["btn_sec"], hover_color=C["btn_sec_hov"],
            text_color=C["mid"], font=("Arial", 13), command=lambda: None)
        self.btn_next.pack(side="left", padx=(6, 0))

        center = ctk.CTkFrame(self.audio_panel, fg_color="transparent")
        center.grid(row=0, column=1, sticky="nsew", padx=10)
        center.grid_columnconfigure(1, weight=1)
        center.grid_rowconfigure(0, weight=1)
        center.grid_rowconfigure(3, weight=1)

        self.lbl_now_playing = ctk.CTkLabel(
            center, text="No track selected",
            font=("Arial", 12, "bold"), text_color=C["dim"], anchor="center")
        self.lbl_now_playing.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 7))

        self.lbl_elapsed = ctk.CTkLabel(
            center, text="00:00",
            font=("Arial", 11), text_color=C["dim"], width=44, anchor="e")
        self.lbl_elapsed.grid(row=2, column=0, padx=(0, 6))

        self.playback_slider = ctk.CTkSlider(
            center, from_=0, to=100, height=12, command=self._on_slider_drag)
        self.playback_slider.grid(row=2, column=1, sticky="ew")
        self.playback_slider.set(0)

        self.lbl_remaining = ctk.CTkLabel(
            center, text="-00:00",
            font=("Arial", 11), text_color=C["dim"], width=50, anchor="w")
        self.lbl_remaining.grid(row=2, column=2, padx=(6, 0))

        right_vol = ctk.CTkFrame(self.audio_panel, fg_color="transparent")
        right_vol.grid(row=0, column=2, padx=(6, 20), sticky="ns")
        right_vol.grid_rowconfigure(0, weight=1)
        right_vol.grid_columnconfigure(0, weight=1)

        vol_inner = ctk.CTkFrame(right_vol, fg_color="transparent")
        vol_inner.grid(row=0, column=0)
        self.lbl_vol_icon = ctk.CTkLabel(
            vol_inner, text="🔊", font=("Arial", 15), text_color=C["dim"])
        self.lbl_vol_icon.pack(side="left", padx=(0, 6))
        self.volume_slider = ctk.CTkSlider(
            vol_inner, from_=0, to=1, width=88, command=self.change_volume)
        self.volume_slider.pack(side="left")
        self.volume_slider.set(0.7)

        # ── Tabs ─────────────────────────────────────────────
        self.tabs = ctk.CTkTabview(self.main_scroll, corner_radius=18)
        self.tabs.grid(row=3, column=0, sticky="nsew", padx=30, pady=6)
        self.tab_down = self.tabs.add("📥 Download")
        self.tab_conv = self.tabs.add("🔄 Converter")
        self.tab_play = self.tabs.add("🎶 Library")

        self.setup_download_tab()
        self.setup_converter_tab()
        self.setup_library_tab()
        self._setup_scroll_isolation()

    def setup_download_tab(self):
        self.tab_down.grid_columnconfigure(0, weight=1)

        sf = ctk.CTkFrame(self.tab_down, fg_color="transparent")
        sf.grid(row=0, column=0, sticky="ew", pady=(10, 6), padx=10)
        sf.grid_columnconfigure(0, weight=1)
        self.url_entry = ctk.CTkEntry(
            sf, height=50, corner_radius=14, border_width=1,
            border_color=C["border3"], fg_color=C["card"], font=("Arial", 13))
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.url_entry.bind("<Return>", lambda *_: self.start_analysis_thread())
        self.btn_search = ctk.CTkButton(
            sf, text="🔍 Analyze", width=126, height=50,
            corner_radius=14, font=("Arial", 13, "bold"),
            command=self.start_analysis_thread)
        self.btn_search.grid(row=0, column=1)

        mf = ctk.CTkFrame(self.tab_down, fg_color="transparent")
        mf.grid(row=1, column=0, sticky="nsew", pady=6, padx=10)
        mf.grid_columnconfigure(0, weight=1)
        mf.grid_columnconfigure(1, weight=1)

        self.preview_frame = ctk.CTkFrame(
            mf, height=290, corner_radius=20,
            fg_color=C["card"], border_width=1, border_color=C["border2"])
        self.preview_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.preview_frame.grid_propagate(False)
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.preview_frame.grid_rowconfigure(0, weight=1)

        self.thumb_label = ctk.CTkLabel(
            self.preview_frame, text="Ready to analyze\n🎵",
            text_color=C["very_dim"], font=("Arial", 15))
        self.thumb_label.grid(row=0, column=0)

        self.lbl_title = ctk.CTkLabel(
            self.preview_frame, text="",
            font=("Arial", 13, "bold"), wraplength=340, text_color=C["bright"])
        self.lbl_title.place(relx=0.5, rely=0.88, anchor="center")

        self.lyrics_frame = ctk.CTkScrollableFrame(
            mf, height=290, corner_radius=20,
            fg_color=C["card"], border_color=C["border2"], border_width=1,
            label_text="📜 Lyrics  •  auto")
        self.lyrics_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.lyrics_frame.grid_columnconfigure(0, weight=1)
        self.lbl_lyrics = ctk.CTkLabel(
            self.lyrics_frame,
            text="Analyze a song to load lyrics automatically...",
            wraplength=400, text_color=C["very_dim"], justify="left", font=("Arial", 14))
        self.lbl_lyrics.pack(pady=20, padx=16, fill="x", expand=True)

        of = ctk.CTkFrame(self.tab_down, fg_color="transparent")
        of.grid(row=2, column=0, sticky="ew", pady=6, padx=10)
        of.grid_columnconfigure((0, 1), weight=1)

        self.lbl_format_dl = ctk.CTkLabel(
            of, text="Format", font=("Arial", 11), text_color=C["dim"])
        self.lbl_format_dl.grid(row=0, column=0, sticky="w", padx=6, pady=(0, 3))
        self.lbl_quality_dl = ctk.CTkLabel(
            of, text="Quality", font=("Arial", 11), text_color=C["dim"])
        self.lbl_quality_dl.grid(row=0, column=1, sticky="w", padx=6, pady=(0, 3))

        self.mode_menu = ctk.CTkOptionMenu(
            of, values=list(FORMAT_QUALITIES.keys()),
            height=46, corner_radius=12, font=("Arial", 13),
            command=self.update_quality_options)
        self.mode_menu.grid(row=1, column=0, sticky="ew", padx=(0, 5))

        self.quality_combo = ctk.CTkComboBox(
            of, height=46, corner_radius=12, font=("Arial", 13))
        self.quality_combo.grid(row=1, column=1, sticky="ew", padx=(5, 0))
        self.update_quality_options(list(FORMAT_QUALITIES.keys())[0])

        self.path_frame = ctk.CTkFrame(
            self.tab_down, height=52, corner_radius=14,
            fg_color=C["card"], border_width=1, border_color=C["border2"])
        self.path_frame.grid(row=3, column=0, sticky="ew", pady=6, padx=10)
        self.path_frame.grid_columnconfigure(0, weight=1)
        self.path_entry = ctk.CTkEntry(
            self.path_frame, border_width=0, fg_color="transparent",
            font=("Arial", 12), text_color=C["path_txt"])
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=14, ipady=2)
        self.update_path_display()
        self.btn_path = ctk.CTkButton(
            self.path_frame, text="📁 Change", width=148, height=38,
            corner_radius=10, command=self.select_folder)
        self.btn_path.grid(row=0, column=1, padx=8)

        self.btn_download = ctk.CTkButton(
            self.tab_down, text="⬇  ADD TO LIBRARY",
            height=68, corner_radius=34,
            font=("Arial", 20, "bold"), state="disabled",
            command=self.start_download_thread)
        self.btn_download.grid(row=4, column=0, sticky="ew", pady=(12, 6), padx=60)

        self.dl_progress = ctk.CTkProgressBar(self.tab_down, height=8, corner_radius=4)
        self.dl_progress.set(0)
        self.dl_progress.grid(row=5, column=0, sticky="ew", padx=60, pady=(4, 2))
        self.dl_progress.grid_remove()

        self.dl_status_lbl = ctk.CTkLabel(
            self.tab_down, text="", font=("Arial", 11), text_color=C["dim"])
        self.dl_status_lbl.grid(row=6, column=0, pady=(0, 12))
        self.dl_status_lbl.grid_remove()

    def setup_library_tab(self):
        self.tab_play.grid_columnconfigure(0, weight=1)
        hdr = ctk.CTkFrame(self.tab_play, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 4))
        self.lbl_collection = ctk.CTkLabel(
            hdr, text="MY COLLECTION",
            font=("Arial", 14, "bold"), text_color=C["dim"])
        self.lbl_collection.pack(side="left")
        self.lib_scroll = ctk.CTkScrollableFrame(
            self.tab_play, height=500, fg_color="transparent", border_width=0)
        self.lib_scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 16))
        self.refresh_library_ui()

    def setup_converter_tab(self):
        self.tab_conv.grid_columnconfigure(0, weight=1)

        self.lbl_conv_title = ctk.CTkLabel(
            self.tab_conv, text="Local File Converter",
            font=("Arial", 22, "bold"), text_color=C["bright"])
        self.lbl_conv_title.pack(pady=(28, 4))

        self.lbl_conv_subtitle = ctk.CTkLabel(
            self.tab_conv, text="Convert any media file to a different format",
            font=("Arial", 13), text_color=C["dim"])
        self.lbl_conv_subtitle.pack(pady=(0, 18))

        self.btn_conv_select = ctk.CTkButton(
            self.tab_conv, text="📁  Select File to Convert",
            height=54, corner_radius=14, font=("Arial", 14, "bold"),
            command=self.select_local_file)
        self.btn_conv_select.pack(pady=6, padx=70, fill="x")

        fmt_row = ctk.CTkFrame(self.tab_conv, fg_color="transparent")
        fmt_row.pack(pady=14)
        self.lbl_conv_target = ctk.CTkLabel(
            fmt_row, text="Target Format:", font=("Arial", 13), text_color=C["dim"])
        self.lbl_conv_target.pack(side="left", padx=(0, 10))
        self.conv_target = ctk.CTkSegmentedButton(
            fmt_row, values=["MP3", "AAC", "WAV", "FLAC", "OGG", "MP4", "MKV"],
            command=self._on_conv_fmt_change)
        self.conv_target.pack(side="left")
        self.conv_target.set("MP3")

        self.conv_qual_frame = ctk.CTkFrame(self.tab_conv, fg_color="transparent")
        self.conv_qual_frame.pack(pady=4)
        self.lbl_conv_quality_label = ctk.CTkLabel(
            self.conv_qual_frame, text="Quality:",
            font=("Arial", 13), text_color=C["dim"])
        self.lbl_conv_quality_label.pack(side="left", padx=(0, 8))
        self.conv_quality_combo = ctk.CTkComboBox(
            self.conv_qual_frame,
            values=["320 kbps", "256 kbps", "192 kbps", "128 kbps"],
            width=210, height=42, corner_radius=12)
        self.conv_quality_combo.pack(side="left")
        self.conv_quality_combo.set("320 kbps")

        self.conv_status_label = ctk.CTkLabel(
            self.tab_conv, text="", text_color=C["mid"], font=("Arial", 12))
        self.conv_status_label.pack(pady=8)

        self.btn_conv_run = ctk.CTkButton(
            self.tab_conv, text="▶  START CONVERSION",
            height=56, corner_radius=28, font=("Arial", 15, "bold"),
            fg_color=C["btn_conv"], border_width=1, border_color=C["btn_conv_brd"],
            text_color=C["bright"],
            command=self.start_conversion_thread)
        self.btn_conv_run.pack(pady=14, padx=80, fill="x")

    def _on_conv_fmt_change(self, value):
        if value in {"MP3", "AAC", "WAV", "FLAC", "OGG"}:
            self.conv_qual_frame.pack(pady=4)
        else:
            self.conv_qual_frame.pack_forget()

    def _setup_scroll_isolation(self):
        def _lock(inner):
            return lambda _: inner._parent_canvas.bind_all(
                "<MouseWheel>", inner._mouse_button_scroll)

        def _unlock():
            return lambda _: self.main_scroll._parent_canvas.bind_all(
                "<MouseWheel>", self.main_scroll._mouse_button_scroll)

        for frame in (self.lyrics_frame, self.lib_scroll):
            frame.bind("<Enter>", _lock(frame))
            frame.bind("<Leave>", _unlock())
