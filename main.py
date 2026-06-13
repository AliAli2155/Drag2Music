# -*- coding: utf-8 -*-
# ── ffmpeg path injection (frozen bundle + dev mode, all platforms) ───────────
import sys as _sys, os as _os

def _ensure_executable(path):
    if _os.path.exists(path) and _sys.platform != 'win32':
        try:
            _os.chmod(path, _os.stat(path).st_mode | 0o111)
        except Exception:
            pass

if getattr(_sys, 'frozen', False):
    _base = _sys._MEIPASS
    if _sys.platform == 'win32':
        _ffmpeg = _os.path.join(_base, 'ffmpeg_bins', 'windows', 'ffmpeg.exe')
    elif _sys.platform == 'darwin':
        _ffmpeg = _os.path.join(_base, 'ffmpeg_bins', 'macos', 'ffmpeg')
    else:
        _ffmpeg = _os.path.join(_base, 'ffmpeg_bins', 'linux', 'ffmpeg')
    _ensure_executable(_ffmpeg)
    _os.environ['PATH']          = _os.path.dirname(_ffmpeg) + _os.pathsep + _os.environ.get('PATH', '')
    _os.environ['FFMPEG_BINARY'] = _ffmpeg
    _os.environ['FFMPEG_DIR']    = _os.path.dirname(_ffmpeg)
else:
    _proj = _os.path.dirname(_os.path.abspath(__file__))
    _plat = ('windows' if _sys.platform == 'win32'
             else 'macos' if _sys.platform == 'darwin' else 'linux')
    _exe  = 'ffmpeg.exe' if _sys.platform == 'win32' else 'ffmpeg'
    for _c in [_os.path.join(_proj, 'ffmpeg_bins', _plat, _exe),
               _os.path.join(_proj, _exe)]:
        if _os.path.exists(_c):
            _ensure_executable(_c)
            _os.environ['PATH']          = _os.path.dirname(_c) + _os.pathsep + _os.environ.get('PATH', '')
            _os.environ['FFMPEG_BINARY'] = _c
            _os.environ['FFMPEG_DIR']    = _os.path.dirname(_c)
            break

del _sys, _os, _ensure_executable
# ─────────────────────────────────────────────────────────────────────────────

import sys, os, queue, threading
import customtkinter as ctk

from core.translations import TRANSLATIONS
from core.constants    import C
from core.ui_setup     import UISetupMixin
from core.analyzer     import AnalyzerMixin
from core.downloader   import DownloaderMixin
from core.settings     import SettingsMixin
from core.lyrics       import LyricsMixin
from core.converter    import ConverterMixin


class Drag2Music(UISetupMixin, AnalyzerMixin, DownloaderMixin,
                 SettingsMixin, LyricsMixin, ConverterMixin, ctk.CTk):

    def __init__(self):
        self.history_file = os.path.join(os.path.expanduser("~"), ".drag2music_history.json")
        # One-time migration from the old TuneFetch history file (preserves user data).
        _old_history = os.path.join(os.path.expanduser("~"), ".tunefetch_history.json")
        if not os.path.exists(self.history_file) and os.path.exists(_old_history):
            try:
                os.rename(_old_history, self.history_file)
            except OSError:
                pass
        self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")

        from core.translations import LANGUAGES as _LANGS
        saved_data = self.load_data_from_disk()
        _saved_path = saved_data.get("download_path", "")
        if _saved_path and os.path.isdir(_saved_path):
            self.download_path = _saved_path
        self.download_history    = saved_data.get("history", [])
        _lang                    = saved_data.get("language", "English")
        self.current_lang        = _lang if _lang in _LANGS else "English"
        self.current_theme_color = saved_data.get("theme", "#1DB954")
        _mode                    = saved_data.get("mode", "Dark")
        self.current_mode        = _mode if _mode in ("Dark", "Light") else "Dark"
        ctk.set_appearance_mode(self.current_mode)

        from core.constants import LOUDNESS_PRESETS as _LP, TARGET_SAMPLE_RATE as _SR
        _loud                    = saved_data.get("loudness", "Off")
        self.loudness_choice     = _loud if _loud in _LP else "Off"
        self.target_sr           = saved_data.get("sample_rate", _SR)

        self.current_video_url   = ""
        self.current_video_title = ""
        self.current_video_info  = {}
        self.track_duration      = 0
        self.selected_local_file = ""

        self.dl_queue             = queue.Queue()
        self.queue_items          = []
        self._queue_lock          = threading.Lock()
        self.queue_worker_running = False
        self._pending_playlist    = None
        self._last_progress_ui    = 0.0

        # ── cancellation state ───────────────────────────────────────────────────
        self._cancel_event    = threading.Event()  # set -> abort active download + stop queue
        self._cancel_partials = set()              # filesystem paths to remove on cancel

        super().__init__()

        # Stay hidden while widgets are built and painted — the window then
        # appears fully drawn instead of assembling piece by piece.
        self.withdraw()

        self.title("Drag2Music: Infinity Studio")

        # Fit on small screens (e.g. 1366x768 laptops): scale the whole UI
        # down proportionally, then centre the window.
        _W, _H = 1200, 780
        try:
            _sw, _sh = self.winfo_screenwidth(), self.winfo_screenheight()
            _scale = min(1.0, (_sw - 40) / _W, (_sh - 90) / _H)
            if _scale < 0.999:
                ctk.set_widget_scaling(_scale)
                ctk.set_window_scaling(_scale)
            _x = max(0, (_sw - int(_W * _scale)) // 2)
            _y = max(0, (_sh - int(_H * _scale)) // 2 - 20)
            self.geometry(f"{_W}x{_H}+{_x}+{_y}")
        except Exception:
            self.geometry(f"{_W}x{_H}")
        self.minsize(1060, 700)
        self.resizable(True, True)
        self.configure(fg_color=C["bg"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._apply_window_icon()

        self.setup_ui()
        self.update_ui_language()
        self.apply_theme_color(self.current_theme_color)
        self.setup_drag_drop()

        # Reveal once the first full paint is done (one extra idle cycle).
        self.update_idletasks()
        self.after(30, self.deiconify)

    def t(self, key, fallback=None):
        return TRANSLATIONS[self.current_lang].get(key, fallback if fallback is not None else key)

    def _apply_window_icon(self):
        """Pick the titlebar/taskbar icon that contrasts with the theme:
        Dark mode → white line-art icon, Light mode → black line-art icon.
        Safe to call repeatedly (e.g. whenever the appearance mode changes)."""
        here = sys._MEIPASS if getattr(sys, 'frozen', False) \
            else os.path.dirname(os.path.abspath(__file__))
        variant = "white" if getattr(self, "current_mode", "Dark") == "Dark" else "black"
        if sys.platform == 'win32':
            for ico in (os.path.join(here, 'assets', f'icon-{variant}.ico'),
                        os.path.join(here, 'assets', 'icon.ico'),
                        os.path.join(here, 'Drag2Music.ico')):
                if os.path.exists(ico):
                    try:
                        self.iconbitmap(ico)
                    except Exception:
                        pass
                    break
        else:
            # .ico is Windows-only; macOS/Linux titlebar icons use iconphoto
            for png in (os.path.join(here, 'assets', f'icon-{variant}.png'),
                        os.path.join(here, 'assets', 'icon.png')):
                if os.path.exists(png):
                    try:
                        import tkinter as _tk
                        self._app_icon = _tk.PhotoImage(file=png)
                        self.iconphoto(True, self._app_icon)
                    except Exception:
                        pass
                    break


if __name__ == "__main__":
    Drag2Music().mainloop()
