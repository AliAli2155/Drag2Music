import os, subprocess, threading
from tkinter import filedialog


class ConverterMixin:

    def select_local_file(self):
        f = filedialog.askopenfilename(filetypes=[
            ("Audio/Video", "*.mp3 *.wav *.flac *.aac *.ogg *.opus *.m4a *.mp4 *.mkv *.webm *.avi"),
            ("All Files", "*.*"),
        ])
        if f:
            self.selected_local_file = f
            name = os.path.basename(f)
            self.btn_conv_select.configure(
                text=f"📄  {name[:52]}" if len(name) <= 52 else f"📄  {name[:49]}…")

    def start_conversion_thread(self):
        if not self.selected_local_file:
            self.conv_status_label.configure(
                text=self.t("conv_select_first"), text_color="#e74c3c")
            return
        self.btn_conv_run.configure(state="disabled", text=self.t("conv_converting_btn"))
        self.conv_status_label.configure(
            text=self.t("conv_converting"), text_color=self.current_theme_color)
        threading.Thread(target=self.run_conversion, daemon=True).start()

    def run_conversion(self):
        try:
            target_fmt = self.conv_target.get().lower()
            src  = self.selected_local_file
            base = os.path.splitext(os.path.basename(src))[0]
            out  = os.path.join(self.download_path, f"{base}_converted.{target_fmt}")

            _fb = os.environ.get('FFMPEG_BINARY', '').strip()
            ffmpeg = _fb if _fb and os.path.exists(_fb) else 'ffmpeg'
            cmd    = [ffmpeg, "-y", "-i", src]

            quality_raw = self.conv_quality_combo.get()
            quality_kbps = quality_raw.split()[0] if quality_raw.split() else "192"

            if target_fmt == "mp3":
                cmd += ["-codec:a", "libmp3lame", "-b:a", f"{quality_kbps}k"]
            elif target_fmt == "aac":
                cmd += ["-codec:a", "aac", "-b:a", f"{quality_kbps}k"]
            elif target_fmt == "ogg":
                cmd += ["-codec:a", "libvorbis"]
            elif target_fmt == "flac":
                cmd += ["-codec:a", "flac"]
            elif target_fmt == "wav":
                cmd += ["-codec:a", "pcm_s16le"]
            elif target_fmt in ("mp4", "mkv"):
                cmd += ["-codec:v", "copy", "-codec:a", "aac"]
            cmd.append(out)

            os.makedirs(self.download_path, exist_ok=True)
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(result.stderr[-200:] if result.stderr else "ffmpeg error")

            out_name = os.path.basename(out)
            self.after(0, lambda n=out_name: self.conv_status_label.configure(
                text=f"{self.t('conv_saved')}: {n}",
                text_color=self.current_theme_color))
        except Exception as e:
            err = str(e)[:120]
            print(f"[Converter] Error: {err}")
            self.after(0, lambda m=err: self.conv_status_label.configure(
                text=f"{self.t('conv_error')}: {m}", text_color="#e74c3c"))
        self.after(0, lambda: self.btn_conv_run.configure(
            state="normal", text=self.t("conv_run")))
