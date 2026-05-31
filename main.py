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


class TuneFetch(UISetupMixin, AnalyzerMixin, DownloaderMixin,
                SettingsMixin, LyricsMixin, ConverterMixin, ctk.CTk):

    def __init__(self):
        self.history_file  = os.path.join(os.path.expanduser("~"), ".tunefetch_history.json")
        self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")

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

        self.dl_queue             = queue.Queue()
        self.queue_items          = []
        self._queue_lock          = threading.Lock()
        self.queue_worker_running = False
        self._pending_playlist    = None
        self._last_progress_ui    = 0.0

        super().__init__()

        self.title("TuneFetch: Infinity Studio")
        self.geometry("1200x780")
        self.resizable(False, False)
        self.configure(fg_color=C["bg"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        _here = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        for _ico in (os.path.join(_here, 'assets', 'icon.ico'),
                     os.path.join(_here, 'TuneFetch.ico')):
            if os.path.exists(_ico):
                try:
                    self.iconbitmap(_ico)
                except Exception:
                    pass
                break

        self.setup_ui()
        self.update_ui_language()
        self.apply_theme_color(self.current_theme_color)
        self.setup_drag_drop()

    def t(self, key):
        return TRANSLATIONS[self.current_lang].get(key, key)


if __name__ == "__main__":
    TuneFetch().mainloop()
