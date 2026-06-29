# -*- coding: utf-8 -*-
"""
core/dj_tools.py — action handlers for the DJ Tools page.

The widgets are built in core/ui_setup.py (setup_djtools_tab); this mixin holds
the logic: pick a file, separate stems, analyze BPM/key, write tags and export
the library as an .m3u8. The heavy work (separation, analysis) is delegated to
the optional DJ Pack worker through core.stems / core.music_analysis, so this
module imports nothing heavy at the top level.
"""

import os
import threading
from tkinter import filedialog

from . import dj_pack
from .constants import STEM_ENGINES, DEFAULT_STEM_ENGINE

_AUDIO_TYPES = [
    ("Audio", "*.mp3 *.wav *.flac *.aac *.ogg *.opus *.m4a"),
    ("All Files", "*.*"),
]


class DJToolsMixin:

    # ── status helpers ────────────────────────────────────────────────────────

    def _dj_status(self, text, color=None):
        try:
            self.lbl_dj_status.configure(
                text=text, text_color=color or self.current_theme_color)
        except Exception:
            pass

    def _dj_busy(self, busy):
        """Enable/disable the action buttons while a job runs."""
        state = "disabled" if busy else "normal"
        for name in ("btn_dj_select", "btn_dj_separate", "btn_dj_analyze",
                     "btn_dj_tag", "btn_dj_export", "btn_dj_pack"):
            w = getattr(self, name, None)
            if w is not None:
                try:
                    w.configure(state=state)
                except Exception:
                    pass
        try:
            if busy:
                self.dj_progress.grid()
                self.dj_progress.configure(mode="indeterminate")
                self.dj_progress.start()
            else:
                self.dj_progress.stop()
                self.dj_progress.configure(mode="determinate")
                self.dj_progress.set(0)
                self.dj_progress.grid_remove()
        except Exception:
            pass

    # ── DJ Pack banner ────────────────────────────────────────────────────────

    def _refresh_dj_pack_ui(self):
        """Show the download banner only when the pack is missing."""
        installed = False
        try:
            installed = dj_pack.is_installed()
        except Exception:
            pass
        frame = getattr(self, "dj_pack_frame", None)
        badge = getattr(self, "lbl_dj_pack_badge", None)
        if installed:
            if frame is not None:
                frame.grid_remove()
            if badge is not None:
                ver = dj_pack.installed_version() or ""
                badge.configure(
                    text=self.t("dj_pack_ready", "DJ Pack ready")
                    + (f" · v{ver}" if ver else ""),
                    text_color=self.current_theme_color)
        else:
            if frame is not None:
                frame.grid()
            if badge is not None:
                badge.configure(text=self.t("dj_pack_missing", "DJ Pack not installed"),
                                text_color=("#6c757d", "#555555"))

    def install_dj_pack(self):
        if not dj_pack.pack_available_for_platform():
            self._dj_status(self.t("dj_pack_unsupported",
                                   "DJ Pack is not available for this platform."),
                            color="#e74c3c")
            return
        try:
            self.btn_dj_pack.configure(
                state="disabled", text=self.t("dj_pack_downloading", "Downloading…"))
            self.dj_pack_progress.grid(row=2, column=0, sticky="ew",
                                       padx=18, pady=(2, 10))
            self.dj_pack_progress.set(0)
        except Exception:
            pass
        threading.Thread(target=self._run_install_dj_pack, daemon=True).start()

    def _run_install_dj_pack(self):
        def _progress(frac, done, total):
            if frac is not None:
                self.after(0, lambda f=frac: self.dj_pack_progress.set(f))
                mb = done / (1024 * 1024)
                tot = total / (1024 * 1024)
                self.after(0, lambda: self._dj_status(
                    f"{self.t('dj_pack_downloading', 'Downloading…')} "
                    f"{mb:.0f} / {tot:.0f} MB"))
        try:
            dj_pack.download_pack(progress=_progress)
            self.after(0, lambda: self._dj_status(
                self.t("dj_pack_installed", "✅ DJ Pack installed")))
        except Exception as e:
            msg = str(e)[:160]
            self.after(0, lambda m=msg: self._dj_status(
                f"{self.t('dj_pack_failed', 'DJ Pack download failed')}: {m}",
                color="#e74c3c"))
        finally:
            self.after(0, self._reset_pack_button)
            self.after(0, self._refresh_dj_pack_ui)

    def _reset_pack_button(self):
        try:
            self.dj_pack_progress.grid_remove()
            self.btn_dj_pack.configure(
                state="normal",
                text=self.t("dj_pack_download_btn", "⬇  Download DJ Pack"))
        except Exception:
            pass

    # ── file picker ───────────────────────────────────────────────────────────

    def select_dj_file(self):
        f = filedialog.askopenfilename(filetypes=_AUDIO_TYPES)
        if not f:
            return
        self.dj_selected_file = f
        self._dj_last_analysis = {}
        name = os.path.basename(f)
        try:
            self.lbl_dj_result.configure(text="—")
            self.btn_dj_select.configure(
                text=f"📄  {name[:52]}" if len(name) <= 52 else f"📄  {name[:49]}…")
        except Exception:
            pass
        self._dj_status(self.t("dj_file_ready", "File ready."))

    def _dj_require(self):
        """Return the selected file path, or None after showing a hint."""
        path = getattr(self, "dj_selected_file", "")
        if not path or not os.path.exists(path):
            self._dj_status(self.t("dj_pick_first", "Select an audio file first."),
                            color="#e74c3c")
            return None
        if not dj_pack.is_installed():
            self._dj_status(self.t("dj_need_pack",
                                   "Install the DJ Pack to use this feature."),
                            color="#e74c3c")
            self._refresh_dj_pack_ui()
            return None
        return path

    # ── stem separation ───────────────────────────────────────────────────────

    def dj_separate_thread(self):
        path = self._dj_require()
        if not path:
            return
        self.stem_engine = self.dj_engine_menu.get()
        try:
            self.save_data_to_disk()
        except Exception:
            pass
        self._dj_busy(True)
        self._dj_status(self.t("dj_separating", "Separating stems… this can take a while."))
        threading.Thread(target=self._run_dj_separate, args=(path,), daemon=True).start()

    def _run_dj_separate(self, path):
        from . import stems
        engine_id, n_stems = STEM_ENGINES.get(
            getattr(self, "stem_engine", DEFAULT_STEM_ENGINE),
            STEM_ENGINES[DEFAULT_STEM_ENGINE])
        outdir = self.download_path
        try:
            files = stems.separate(
                path, engine=engine_id, n_stems=n_stems, outdir=outdir,
                on_line=lambda ln: self.after(0, lambda l=ln: self._dj_status(l)))
            n = len(files)
            self.after(0, lambda: self._dj_status(
                f"{self.t('dj_stems_done', '✅ Stems saved')}: {n} → {outdir}"))
        except dj_pack.DJPackNotInstalled:
            self.after(0, lambda: self._dj_status(
                self.t("dj_need_pack", "Install the DJ Pack to use this feature."),
                color="#e74c3c"))
            self.after(0, self._refresh_dj_pack_ui)
        except Exception as e:
            msg = str(e)[:160]
            self.after(0, lambda m=msg: self._dj_status(
                f"{self.t('dj_stems_failed', 'Separation failed')}: {m}",
                color="#e74c3c"))
        finally:
            self.after(0, lambda: self._dj_busy(False))

    # ── BPM + key analysis ────────────────────────────────────────────────────

    def dj_analyze_thread(self):
        path = self._dj_require()
        if not path:
            return
        self._dj_busy(True)
        self._dj_status(self.t("dj_analyzing", "Analyzing BPM and key…"))
        threading.Thread(target=self._run_dj_analyze, args=(path,), daemon=True).start()

    def _run_dj_analyze(self, path):
        from . import music_analysis
        try:
            res = music_analysis.analyze(
                path, on_line=lambda ln: self.after(0, lambda l=ln: self._dj_status(l)))
            self._dj_last_analysis = res
            self.after(0, lambda r=res: self._show_analysis(r))
        except dj_pack.DJPackNotInstalled:
            self.after(0, lambda: self._dj_status(
                self.t("dj_need_pack", "Install the DJ Pack to use this feature."),
                color="#e74c3c"))
            self.after(0, self._refresh_dj_pack_ui)
        except Exception as e:
            msg = str(e)[:160]
            self.after(0, lambda m=msg: self._dj_status(
                f"{self.t('dj_analyze_failed', 'Analysis failed')}: {m}",
                color="#e74c3c"))
        finally:
            self.after(0, lambda: self._dj_busy(False))

    @staticmethod
    def _analysis_text(res):
        bits = []
        if res.get("bpm"):
            bits.append(f"{float(res['bpm']):.0f} BPM")
        cam = res.get("camelot")
        key = res.get("key")
        if cam and key:
            bits.append(f"{cam} · {key}")
        elif key:
            bits.append(str(key))
        return "   ·   ".join(bits) if bits else "—"

    def _show_analysis(self, res):
        try:
            self.lbl_dj_result.configure(text=self._analysis_text(res))
        except Exception:
            pass
        self._dj_status(self.t("dj_analyze_done",
                               "Done. Use “Write tags” to embed BPM/key."))

    # ── write tags ────────────────────────────────────────────────────────────

    def dj_write_tags(self):
        path = getattr(self, "dj_selected_file", "")
        if not path or not os.path.exists(path):
            self._dj_status(self.t("dj_pick_first", "Select an audio file first."),
                            color="#e74c3c")
            return
        res = getattr(self, "_dj_last_analysis", {}) or {}
        if not (res.get("bpm") or res.get("key")):
            self._dj_status(self.t("dj_analyze_first",
                                   "Analyze the track first."), color="#e74c3c")
            return
        from . import tagger
        ok = tagger.write_tags(path, bpm=res.get("bpm"), key=res.get("key"),
                               camelot=res.get("camelot"))
        if ok:
            self._dj_status(self.t("dj_tags_done", "✅ Tags written to file."))
        else:
            self._dj_status(self.t("dj_tags_failed",
                                   "Could not write tags to this format."),
                            color="#e74c3c")

    # ── auto-analyze after download ───────────────────────────────────────────

    def _maybe_auto_analyze(self, item, entry):
        """Called from the download worker when 'Auto BPM + key' is on.
        Analyzes + tags the freshly downloaded audio file in the background and
        folds bpm/key/camelot back into its library entry. Silent on failure —
        a download must never be reported as broken because analysis couldn't run."""
        from .constants import AUDIO_FMTS
        fmt = (item.get("fmt") or "").upper()
        path = item.get("filepath") or entry.get("path")
        if fmt not in AUDIO_FMTS or not path or not os.path.exists(path):
            return
        if not dj_pack.is_installed():
            return
        threading.Thread(target=self._run_auto_analyze,
                         args=(path, entry), daemon=True).start()

    def _run_auto_analyze(self, path, entry):
        from . import music_analysis, tagger
        try:
            res = music_analysis.analyze(path)
        except Exception as e:
            print(f"[auto-analyze] {os.path.basename(path)}: {e}")
            return
        if res.get("bpm"):
            entry["bpm"] = res["bpm"]
        if res.get("key"):
            entry["key"] = res["key"]
        if res.get("camelot"):
            entry["camelot"] = res["camelot"]
        try:
            tagger.write_tags(path, bpm=res.get("bpm"), key=res.get("key"),
                              camelot=res.get("camelot"))
        except Exception:
            pass
        try:
            self.save_data_to_disk()
            self.after(0, self.refresh_library_ui)
        except Exception:
            pass

    # ── export ────────────────────────────────────────────────────────────────

    def dj_export_m3u8(self):
        from . import dj_export
        if not self.download_history:
            self._dj_status(self.t("dj_export_empty", "Your library is empty."),
                            color="#e74c3c")
            return
        out = filedialog.asksaveasfilename(
            defaultextension=".m3u8",
            initialfile=dj_export.default_export_name(),
            filetypes=[("M3U8 playlist", "*.m3u8"), ("All Files", "*.*")])
        if not out:
            return
        try:
            written, skipped = dj_export.export_m3u8(self.download_history, out)
            msg = f"{self.t('dj_export_done', '✅ Exported')}: {written} ♪"
            if skipped:
                msg += f" · {skipped} {self.t('dj_export_skipped', 'skipped (missing)')}"
            self._dj_status(msg)
        except Exception as e:
            self._dj_status(f"{self.t('dj_export_failed', 'Export failed')}: "
                            f"{str(e)[:120]}", color="#e74c3c")
