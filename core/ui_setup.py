import tkinter as tk
import customtkinter as ctk
from .translations import LANGUAGES
from .constants import FORMAT_QUALITIES, C, FONT

try:
    from PIL import Image, ImageDraw
    try:
        _BILINEAR = Image.Resampling.BILINEAR
    except AttributeError:
        _BILINEAR = Image.BILINEAR
    _PIL_OK = True
except Exception:
    _PIL_OK = False


class GradientProgressBar(tk.Canvas):
    """Pill-shaped progress bar with a gradient fill and centred % text.

    Gradient runs from a lighter tint of the accent colour on the left to
    the accent on the right.  Uses PIL (already a project dependency) for
    smooth rendering; falls back to a flat bar if PIL is unavailable.
    Width is responsive via <Configure>.
    """

    _HEIGHT  = 26
    # Matches C["bg"] — the bar always sits on the window background.
    _DARK_BG = (13, 13, 13)
    _LITE_BG = (240, 242, 245)
    _DARK_TRACK = (26, 26, 28)
    _LITE_TRACK = (218, 221, 225)

    def __init__(self, master, height=None, **kwargs):
        h = height if height is not None else self._HEIGHT
        super().__init__(master, width=1, height=h,
                         highlightthickness=0, bd=0, **kwargs)
        self._cw     = 1
        self._ch     = h
        self._prog   = 0.0
        self._color  = "#1DB954"
        self._photo  = None
        self._img_id = None
        self._txt_id = None
        self._anim_job    = None
        self._anim_target = 0.0
        self._sync_bg()
        self.bind("<Configure>", self._on_configure)
        # Raw tk.Canvas widgets are invisible to CTk's theme engine — register
        # with the tracker so Dark/Light switches recolor the bar instantly.
        self._appearance_cb = lambda _mode: self._redraw()
        try:
            ctk.AppearanceModeTracker.add(self._appearance_cb, self)
            self.bind("<Destroy>", self._on_destroy_cleanup, add=True)
        except Exception:
            self._appearance_cb = None

    def _on_destroy_cleanup(self, _event=None):
        self._cancel_anim()
        if self._appearance_cb is not None:
            try:
                ctk.AppearanceModeTracker.remove(self._appearance_cb)
            except Exception:
                pass
            self._appearance_cb = None

    # ── Smooth progress animation ─────────────────────────────────────────────

    def _cancel_anim(self):
        if self._anim_job is not None:
            try:
                self.after_cancel(self._anim_job)
            except Exception:
                pass
            self._anim_job = None

    def _anim_tick(self):
        self._anim_job = None
        try:
            diff = self._anim_target - self._prog
            if diff <= 0.003:
                self.set_progress(self._anim_target)
                return
            self.set_progress(self._prog + diff * 0.30)   # ease-out
            self._anim_job = self.after(30, self._anim_tick)
        except tk.TclError:
            self._anim_job = None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _is_dark(self):
        return ctk.get_appearance_mode() == "Dark"

    def _bg_rgb(self):
        return self._DARK_BG if self._is_dark() else self._LITE_BG

    def _track_rgb(self):
        return self._DARK_TRACK if self._is_dark() else self._LITE_TRACK

    def _sync_bg(self):
        r, g, b = self._bg_rgb()
        super().configure(bg=f"#{r:02x}{g:02x}{b:02x}")

    @staticmethod
    def _hex_rgb(h):
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def _lighten(rgb, f=0.55):
        r, g, b = rgb
        return (int(r + (255-r)*f), int(g + (255-g)*f), int(b + (255-b)*f))

    # ── Resize / redraw ───────────────────────────────────────────────────────

    def _on_configure(self, event):
        w = max(event.width, 20)
        h = max(event.height, 10)
        if w == self._cw and h == self._ch and self._img_id is not None:
            return
        self._cw, self._ch = w, h
        self._sync_bg()
        # Debounce: interactive resizes (maximize/restore) fire dozens of
        # Configure events — render once when the size settles.
        job = getattr(self, "_conf_job", None)
        if job is not None:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        self._conf_job = self.after(40, self._conf_redraw)

    def _conf_redraw(self):
        self._conf_job = None
        try:
            self._redraw()
        except tk.TclError:
            pass

    def _make_photo(self):
        if not _PIL_OK:
            return None
        w, h  = self._cw, self._ch
        r     = h // 2
        track = self._track_rgb()
        acc   = self._hex_rgb(self._color)
        lt    = self._lighten(acc)

        img   = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw  = ImageDraw.Draw(img)
        draw.rounded_rectangle([0, 0, w-1, h-1], radius=r, fill=(*track, 255))

        fw = int(self._prog * w)
        if fw > 1:
            src = Image.new("RGBA", (2, 1))
            src.putpixel((0, 0), (*lt,  255))
            src.putpixel((1, 0), (*acc, 255))
            grad = src.resize((fw, h), _BILINEAR)
            mask = Image.new("L", (fw, h), 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                [0, 0, fw-1, h-1], radius=min(r, max(1, fw//2)), fill=255)
            img.paste(grad, (0, 0), mask)

        from PIL.ImageTk import PhotoImage
        return PhotoImage(img)

    def _redraw(self):
        if self._cw < 2:
            return
        self._sync_bg()   # follow Dark/Light mode changes
        photo = self._make_photo()
        if photo:
            self._photo = photo
            if self._img_id is None:
                self._img_id = self.create_image(0, 0, anchor="nw", image=photo)
            else:
                self.itemconfigure(self._img_id, image=photo)
        else:
            self.delete("all")
            self._img_id = None
            self._txt_id = None   # delete("all") removed the text item too
            fw = int(self._prog * self._cw)
            if fw > 0:
                self.create_rectangle(0, 0, fw, self._ch,
                                      fill=self._color, outline="")

        pct = f"{int(self._prog * 100)}%" if self._prog > 0 else ""
        sz  = max(9, self._ch // 3)
        # Readable in both modes: white once the fill reaches the centre,
        # otherwise mode-appropriate contrast over the empty track.
        if self._prog >= 0.5:
            txt_clr = "white"
        else:
            txt_clr = "white" if self._is_dark() else "#343a40"
        if self._txt_id is None:
            self._txt_id = self.create_text(
                self._cw // 2, self._ch // 2, text=pct,
                fill=txt_clr, font=(FONT, sz, "bold"), anchor="center")
        else:
            self.coords(self._txt_id, self._cw // 2, self._ch // 2)
            self.itemconfigure(self._txt_id, text=pct, fill=txt_clr,
                               font=(FONT, sz, "bold"))
        self.tag_raise(self._txt_id)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_progress(self, fraction):
        self._prog = max(0.0, min(1.0, float(fraction)))
        self._redraw()

    def set(self, fraction):
        """Eases toward higher targets; resets (lower values) jump instantly."""
        t = max(0.0, min(1.0, float(fraction)))
        if t <= self._prog + 0.001:
            self._cancel_anim()
            self.set_progress(t)
            return
        self._anim_target = t
        if self._anim_job is None:
            self._anim_tick()

    def set_color(self, color):
        self._color = color
        self._redraw()

    def configure(self, cnf=None, **kwargs):
        if 'progress_color' in kwargs:
            self.set_color(kwargs.pop('progress_color'))
        if cnf or kwargs:
            super().configure(cnf or {}, **kwargs)

    def reset(self):
        self.set_progress(0.0)


class GradientButton(tk.Canvas):
    """Pill-shaped call-to-action button with an accent gradient fill.

    API-compatible with the CTkButton calls used in this codebase:
    configure(text=..., state=..., fg_color=..., hover_color=...), cget("text").
    Renders with PIL; falls back to a flat fill without it.
    """

    _DARK_BG  = (13, 13, 13)
    _LITE_BG  = (240, 242, 245)
    _DARK_DIS = (34, 34, 34)      # disabled fill
    _LITE_DIS = (222, 226, 230)

    def __init__(self, master, text="", command=None, height=48,
                 font=None, state="normal", **_ignored):
        super().__init__(master, width=10, height=height,
                         highlightthickness=0, bd=0)
        self._text     = text
        self._command  = command
        self._state    = state
        self._color    = "#1DB954"
        self._font     = font or (FONT, 14, "bold")
        self._cw, self._ch = 1, height
        self._hover    = False
        self._pressed  = False
        self._photo    = None
        self._img_id   = None
        self._txt_id   = None
        self._conf_job = None
        self._sync_bg()
        self.bind("<Configure>", self._on_configure)
        self.bind("<Enter>",  lambda _e: self._set_hover(True))
        self.bind("<Leave>",  lambda _e: self._set_hover(False))
        self.bind("<ButtonPress-1>",   self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._appearance_cb = lambda _m: self._redraw()
        try:
            ctk.AppearanceModeTracker.add(self._appearance_cb, self)
            self.bind("<Destroy>", self._cleanup, add=True)
        except Exception:
            self._appearance_cb = None

    # ── plumbing ──────────────────────────────────────────────────────────────

    def _cleanup(self, _e=None):
        if self._conf_job is not None:
            try:
                self.after_cancel(self._conf_job)
            except Exception:
                pass
            self._conf_job = None
        if self._appearance_cb is not None:
            try:
                ctk.AppearanceModeTracker.remove(self._appearance_cb)
            except Exception:
                pass
            self._appearance_cb = None

    def _is_dark(self):
        return ctk.get_appearance_mode() == "Dark"

    def _sync_bg(self):
        r, g, b = self._DARK_BG if self._is_dark() else self._LITE_BG
        super().configure(bg=f"#{r:02x}{g:02x}{b:02x}")

    @staticmethod
    def _hex_rgb(h):
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def _shade(rgb, f):
        return tuple(max(0, min(255, int(c * f))) for c in rgb)

    @staticmethod
    def _tint(rgb, f=0.35):
        r, g, b = rgb
        return (int(r + (255-r)*f), int(g + (255-g)*f), int(b + (255-b)*f))

    def _on_configure(self, event):
        w, h = max(event.width, 20), max(event.height, 20)
        if w == self._cw and h == self._ch and self._img_id is not None:
            return
        self._cw, self._ch = w, h
        self._sync_bg()
        if self._conf_job is not None:
            try:
                self.after_cancel(self._conf_job)
            except Exception:
                pass
        self._conf_job = self.after(40, self._conf_redraw)

    def _conf_redraw(self):
        self._conf_job = None
        try:
            self._redraw()
        except tk.TclError:
            pass

    # ── interaction ───────────────────────────────────────────────────────────

    def _set_hover(self, on):
        self._hover = on
        if not on:
            self._pressed = False
        if self._state == "normal":
            self._redraw()

    def _on_press(self, _e):
        if self._state == "normal":
            self._pressed = True
            self._redraw()

    def _on_release(self, e):
        was = self._pressed
        self._pressed = False
        if self._state != "normal":
            return
        self._redraw()
        inside = 0 <= e.x <= self._cw and 0 <= e.y <= self._ch
        if was and inside and self._command:
            self._command()

    # ── drawing ───────────────────────────────────────────────────────────────

    def _make_photo(self):
        if not _PIL_OK:
            return None
        w, h = self._cw, self._ch
        r    = h // 2
        if self._state == "disabled":
            fill_l = fill_r = self._DARK_DIS if self._is_dark() else self._LITE_DIS
        else:
            acc = self._hex_rgb(self._color)
            if self._pressed:
                acc = self._shade(acc, 0.72)
            elif self._hover:
                acc = self._shade(acc, 0.86)
            fill_l, fill_r = self._tint(acc), acc

        img  = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        src  = Image.new("RGBA", (2, 1))
        src.putpixel((0, 0), (*fill_l, 255))
        src.putpixel((1, 0), (*fill_r, 255))
        grad = src.resize((w, h), _BILINEAR)
        mask = Image.new("L", (w * 2, h * 2), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, w*2 - 1, h*2 - 1], radius=r * 2, fill=255)
        mask = mask.resize((w, h), _BILINEAR)
        img.paste(grad, (0, 0), mask)
        from PIL.ImageTk import PhotoImage
        return PhotoImage(img)

    def _redraw(self):
        if self._cw < 2:
            return
        self._sync_bg()
        photo = self._make_photo()
        if photo:
            self._photo = photo
            if self._img_id is None:
                self._img_id = self.create_image(0, 0, anchor="nw", image=photo)
            else:
                self.itemconfigure(self._img_id, image=photo)
        else:
            self.delete("all")
            self._img_id = self._txt_id = None
            self.create_rectangle(0, 0, self._cw, self._ch,
                                  fill=self._color, outline="")
        if self._state == "disabled":
            txt_clr = "#666666" if self._is_dark() else "#9aa1a8"
        else:
            txt_clr = "white"
        if self._txt_id is None:
            self._txt_id = self.create_text(
                self._cw // 2, self._ch // 2, text=self._text,
                fill=txt_clr, font=self._font, anchor="center")
        else:
            self.coords(self._txt_id, self._cw // 2, self._ch // 2)
            self.itemconfigure(self._txt_id, text=self._text, fill=txt_clr)
        self.tag_raise(self._txt_id)

    # ── CTkButton-compatible API ──────────────────────────────────────────────

    def configure(self, cnf=None, **kwargs):
        redraw = False
        if "text" in kwargs:
            self._text = kwargs.pop("text")
            redraw = True
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            redraw = True
        if "fg_color" in kwargs:
            c = kwargs.pop("fg_color")
            if isinstance(c, str) and c.startswith("#"):
                self._color = c
                redraw = True
        if "command" in kwargs:
            self._command = kwargs.pop("command")
        for k in ("hover_color", "text_color", "corner_radius", "font"):
            kwargs.pop(k, None)
        if cnf or kwargs:
            super().configure(cnf or {}, **kwargs)
        if redraw:
            self._redraw()

    def cget(self, key):
        if key == "text":
            return self._text
        if key == "state":
            return self._state
        if key == "fg_color":
            return self._color
        return super().cget(key)


class LibraryList(tk.Canvas):
    """The whole download library drawn on one canvas.

    Hundreds of CTk widgets in a scrollable frame are slow to create and
    unreliable to repaint; one canvas with text/polygon items renders the
    same list in milliseconds and scrolls natively.
    """

    ROW_H = 64
    PAD   = 4

    def __init__(self, master, **kwargs):
        super().__init__(master, highlightthickness=0, bd=0, **kwargs)
        self._items      = []
        self._accent     = "#1DB954"
        self._empty_text = ""
        self._width      = 1
        self._conf_job   = None
        self._sync_bg()
        self.bind("<Configure>", self._on_configure)
        self._appearance_cb = lambda _m: self._redraw()
        try:
            ctk.AppearanceModeTracker.add(self._appearance_cb, self)
            self.bind("<Destroy>", self._cleanup, add=True)
        except Exception:
            self._appearance_cb = None

    def _cleanup(self, _e=None):
        if self._appearance_cb is not None:
            try:
                ctk.AppearanceModeTracker.remove(self._appearance_cb)
            except Exception:
                pass
            self._appearance_cb = None

    def _is_dark(self):
        return ctk.get_appearance_mode() == "Dark"

    def _c(self, key):
        return C[key][1] if self._is_dark() else C[key][0]

    def _sync_bg(self):
        try:
            super().configure(bg=self._c("bg"))
        except Exception:
            pass

    def _on_configure(self, event):
        if event.width == self._width:
            return
        self._width = event.width
        if self._conf_job is not None:
            try:
                self.after_cancel(self._conf_job)
            except Exception:
                pass
        self._conf_job = self.after(40, self._conf_redraw)

    def _conf_redraw(self):
        self._conf_job = None
        try:
            self._redraw()
        except tk.TclError:
            pass

    def _round_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r, x2, y2,
               x2-r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y1+r, x1, y1]
        return self.create_polygon(pts, smooth=True, **kw)

    # ── public API ────────────────────────────────────────────────────────────

    def set_items(self, items, accent, empty_text):
        """items: list of dicts with tag / tag_audio / name / meta / when."""
        self._items      = items
        self._accent     = accent
        self._empty_text = empty_text
        self._redraw()

    def _redraw(self):
        self.delete("all")
        self._sync_bg()
        w = max(self._width, 200)

        if not self._items:
            self.create_text(
                w // 2, 120, text=self._empty_text, justify="center",
                fill=self._c("very_dim"), font=(FONT, 14))
            self.configure(scrollregion=(0, 0, w, 260))
            return

        card  = self._c("card")
        brd   = self._c("border2")
        mid   = self._c("mid")
        dim   = self._c("dim")
        tagbg = self._c("tag_bg")

        y = self.PAD
        for it in self._items:
            x1, x2 = self.PAD, w - self.PAD
            self._round_rect(x1, y, x2, y + self.ROW_H - 6, 14,
                             fill=card, outline=brd)
            tag_clr = self._accent if it.get("tag_audio") else "#3498db"
            cx = x1 + 14
            self._round_rect(cx, y + 17, cx + 52, y + 41, 7, fill=tagbg,
                             outline="")
            self.create_text(cx + 26, y + 29, text=it.get("tag", "?"),
                             fill=tag_clr, font=(FONT, 9, "bold"))
            tx = cx + 64
            self.create_text(tx, y + 19, text=it.get("name", ""),
                             anchor="w", fill=mid, font=(FONT, 12, "bold"))
            self.create_text(tx, y + 41, text=it.get("meta", ""),
                             anchor="w", fill=dim, font=(FONT, 10))
            self.create_text(x2 - 16, y + 29, text=it.get("when", ""),
                             anchor="e", fill=dim, font=(FONT, 10))
            y += self.ROW_H

        self.configure(scrollregion=(0, 0, w, y + self.PAD))


class UISetupMixin:

    SIDEBAR_W = 224
    COVER_H   = 296   # big cover card height (px)

    @staticmethod
    def _mix_hex(c1, c2, t):
        """Linear blend between two #rrggbb colours, t in [0, 1]."""
        try:
            a = tuple(int(c1.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            b = tuple(int(c2.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            m = tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))
            return f"#{m[0]:02x}{m[1]:02x}{m[2]:02x}"
        except Exception:
            return c2

    def setup_ui(self):
        self.main_frame = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_scroll = self.main_frame

        self._build_sidebar()

        # ── Stacked pages (replaces the old CTkTabview) ───────
        container = ctk.CTkFrame(self.main_frame, fg_color="transparent",
                                 corner_radius=0)
        container.grid(row=0, column=1, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)
        self._page_container = container

        self.pages = {}
        for name in ("download", "converter", "library"):
            # Transparent is safe here: _select_page grid_remove()s hidden
            # pages, so only one page is ever mapped at a time.
            page = ctk.CTkFrame(container, fg_color="transparent",
                                corner_radius=0)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[name] = page

        # Aliases kept for the other mixins
        self.tab_down = self.pages["download"]
        self.tab_conv = self.pages["converter"]
        self.tab_play = self.pages["library"]

        self.setup_download_tab()
        self.setup_converter_tab()
        self.setup_library_tab()
        self._setup_scroll_isolation()

        self._select_page("download")

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        sb = ctk.CTkFrame(self.main_frame, width=self.SIDEBAR_W,
                          fg_color=C["panel"], corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsw")
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)
        sb.grid_rowconfigure(4, weight=1)   # spacer pushes footer down
        self.sidebar = sb

        # Logo
        logo = ctk.CTkFrame(sb, fg_color="transparent")
        logo.grid(row=0, column=0, sticky="ew", padx=20, pady=(24, 2))
        self.lbl_logo_tune = ctk.CTkLabel(
            logo, text="Drag2", font=(FONT, 26, "bold"), text_color=C["tune"])
        self.lbl_logo_tune.pack(side="left")
        self.lbl_music = ctk.CTkLabel(
            logo, text="Music", font=(FONT, 26, "bold"))
        self.lbl_music.pack(side="left")

        sub = ctk.CTkFrame(sb, fg_color="transparent")
        sub.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 6))
        ctk.CTkLabel(sub, text="Studio", font=(FONT, 12),
                     text_color=C["studio"]).pack(side="left")
        self.lbl_made_by = ctk.CTkLabel(
            sub, text="  ·  Made by Ali A.",
            font=(FONT, 10), text_color=C["dim"])
        self.lbl_made_by.pack(side="left")

        # Thin accent gradient divider under the logo
        self.sidebar_grad = tk.Canvas(sb, height=3, highlightthickness=0, bd=0)
        self.sidebar_grad.grid(row=2, column=0, sticky="ew",
                               padx=20, pady=(0, 14))
        self.sidebar_grad.bind(
            "<Configure>", lambda _e: self._draw_sidebar_grad())

        # Navigation
        nav = ctk.CTkFrame(sb, fg_color="transparent")
        nav.grid(row=3, column=0, sticky="ew", padx=12)
        nav.grid_columnconfigure(0, weight=1)
        self.nav_buttons = {}
        for i, name in enumerate(("download", "converter", "library")):
            btn = ctk.CTkButton(
                nav, text="", height=44, corner_radius=12,
                font=(FONT, 13, "bold"), anchor="w",
                fg_color="transparent", hover_color=C["nav_hover"],
                text_color=C["mid"],
                command=lambda n=name: self._select_page(n))
            btn.grid(row=i, column=0, sticky="ew", pady=3)
            self.nav_buttons[name] = btn
        self._set_nav_texts()

        # Footer: language + settings
        foot = ctk.CTkFrame(sb, fg_color="transparent")
        foot.grid(row=5, column=0, sticky="ew", padx=14, pady=(8, 18))
        foot.grid_columnconfigure(0, weight=1)

        self.lang_combo = ctk.CTkComboBox(
            foot, values=LANGUAGES, height=36, corner_radius=10,
            font=(FONT, 12), command=self.change_language_event)
        self.lang_combo.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.lang_combo.set(self.current_lang)

        self.btn_settings = ctk.CTkButton(
            foot, text="⚙", font=(FONT, 16), width=40, height=36,
            corner_radius=10,
            fg_color=C["btn_sec"], hover_color=C["btn_sec_hov"],
            command=self.show_settings_menu)
        self.btn_settings.grid(row=0, column=1)

    def _draw_sidebar_grad(self):
        """Horizontal accent→panel gradient divider under the logo."""
        cv = getattr(self, "sidebar_grad", None)
        if cv is None or not _PIL_OK:
            return
        try:
            w = max(cv.winfo_width(), 2)
            h = max(cv.winfo_height(), 2)
            dark  = ctk.get_appearance_mode() == "Dark"
            panel = C["panel"][1] if dark else C["panel"][0]
            acc   = getattr(self, "current_theme_color", "#1DB954")
            cv.configure(bg=panel)
            a = tuple(int(acc.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            p = tuple(int(panel.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            src = Image.new("RGB", (2, 1))
            src.putpixel((0, 0), a)
            src.putpixel((1, 0), p)
            from PIL.ImageTk import PhotoImage
            self._sidebar_grad_photo = PhotoImage(src.resize((w, h), _BILINEAR))
            cv.delete("all")
            cv.create_image(0, 0, anchor="nw", image=self._sidebar_grad_photo)
        except Exception:
            pass

    def _set_nav_texts(self):
        t = self.t if callable(getattr(self, 't', None)) else (lambda k, f=None: f or k)
        self.nav_buttons["download"].configure(
            text="   " + t("tab_download", "📥 Download"))
        self.nav_buttons["converter"].configure(
            text="   " + t("tab_converter", "🔄 Converter"))
        self.nav_buttons["library"].configure(
            text="   " + t("tab_library", "🎶 Library"))

    def _select_page(self, name):
        job = getattr(self, "_nav_anim_job", None)
        if job is not None:
            try:
                self.after_cancel(job)
            except Exception:
                pass
            self._nav_anim_job = None

        first_select = not hasattr(self, "_active_page")
        self._active_page = name
        # grid_remove/grid instead of tkraise: raising stacked frames is not
        # reliable across Tk builds — unmapping the others guarantees only
        # the active page is ever visible.
        for n, pg in self.pages.items():
            if n == name:
                pg.grid()
            else:
                pg.grid_remove()
        if name == "library":
            # Lazy: the library list is only (re)built when actually shown
            self._ensure_library_rendered()
        accent = getattr(self, "current_theme_color", "#1DB954")
        for n, btn in self.nav_buttons.items():
            if n != name:
                btn.configure(fg_color="transparent", text_color=C["mid"],
                              hover_color=C["nav_hover"])

        active = self.nav_buttons[name]
        if first_select:   # startup: no animation
            active.configure(fg_color=accent, text_color="white",
                             hover_color=accent)
            return

        # Fade the accent in from the sidebar colour (~110 ms)
        dark      = ctk.get_appearance_mode() == "Dark"
        start     = C["panel"][1] if dark else C["panel"][0]
        txt_start = C["mid"][1] if dark else C["mid"][0]
        steps     = 5

        def _tick(i=1):
            self._nav_anim_job = None
            try:
                active.configure(
                    fg_color=self._mix_hex(start, accent, i / steps),
                    text_color=self._mix_hex(txt_start, "#ffffff", i / steps),
                    hover_color=accent)
            except Exception:
                return
            if i < steps:
                self._nav_anim_job = self.after(22, lambda: _tick(i + 1))
        _tick()

    def _restyle_nav(self, color, hover):
        """Called by apply_theme_color when the accent changes."""
        active = getattr(self, "_active_page", "download")
        for n, btn in self.nav_buttons.items():
            if n == active:
                btn.configure(fg_color=color, hover_color=color)

    # ── Download Page ─────────────────────────────────────────────────────────

    def setup_download_tab(self):
        p = self.tab_down
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(1, weight=1)
        PADX = 24

        # ── Search ───────────────────────────────────────────
        sf = ctk.CTkFrame(p, fg_color="transparent")
        sf.grid(row=0, column=0, sticky="ew", padx=PADX, pady=(20, 12))
        sf.grid_columnconfigure(0, weight=1)
        self.url_entry = ctk.CTkEntry(
            sf, height=46, corner_radius=14, border_width=1,
            border_color=C["border3"], fg_color=C["card"], font=(FONT, 13),
            placeholder_text="Search song or paste YouTube / SoundCloud URL...")
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.url_entry.bind("<Return>", lambda *_: self.start_analysis_thread())
        self.btn_search = ctk.CTkButton(
            sf, text="🔍  Analyze", width=128, height=46,
            corner_radius=14, font=(FONT, 13, "bold"),
            command=self.start_analysis_thread)
        self.btn_search.grid(row=0, column=1, padx=(0, 6))
        self.btn_clear = ctk.CTkButton(
            sf, text="✕", width=46, height=46,
            corner_radius=14, font=(FONT, 14, "bold"),
            fg_color=C["btn_sec"], hover_color=C["btn_sec_hov"],
            text_color=C["dim"], command=self.clear_search)
        self.btn_clear.grid(row=0, column=2)

        # ── Big cover + Lyrics ────────────────────────────────
        # Both cards share row 0 so they are exactly the same height and
        # bottom-aligned; the title / artist caption lives in row 1, below
        # the cover only, so it never makes the cards uneven.
        mf = ctk.CTkFrame(p, fg_color="transparent")
        mf.grid(row=1, column=0, sticky="nsew", padx=PADX, pady=(0, 10))
        mf.grid_columnconfigure(0, weight=11, uniform="media")
        mf.grid_columnconfigure(1, weight=9,  uniform="media")
        mf.grid_rowconfigure(0, weight=1)   # cards expand; row 1 (caption) natural

        self.preview_frame = ctk.CTkFrame(
            mf, height=self.COVER_H, corner_radius=18,
            fg_color=C["card"], border_width=1, border_color=C["border2"])
        self.preview_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.preview_frame.grid_propagate(False)
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.preview_frame.grid_rowconfigure(0, weight=1)

        self.thumb_label = ctk.CTkLabel(
            self.preview_frame, text="🎵\nReady to analyze",
            text_color=C["very_dim"], font=(FONT, 15))
        self.thumb_label.grid(row=0, column=0)

        # Image label fills the whole card; analyzer renders a
        # rounded-corner, centre-cropped cover into it.
        self.thumb_img = tk.Label(
            self.preview_frame, borderwidth=0, highlightthickness=0)
        self._sync_thumb_bg()
        self.thumb_img.place(relx=0.5, rely=0.5, anchor="center")
        self.thumb_img.lower()

        self.lbl_source_badge = ctk.CTkLabel(
            self.preview_frame, text="",
            font=(FONT, 10, "bold"), text_color="white",
            fg_color="transparent", corner_radius=6, height=22)
        self.lbl_source_badge.place(x=12, y=12)

        # Real source-quality badge (top-right): honest codec/bitrate
        self.lbl_quality_badge = ctk.CTkLabel(
            self.preview_frame, text="",
            font=(FONT, 10, "bold"), text_color="white",
            fg_color="transparent", corner_radius=6, height=22)
        self.lbl_quality_badge.place(relx=1.0, x=-12, y=12, anchor="ne")

        # Duration badge (bottom-right)
        self.lbl_duration = ctk.CTkLabel(
            self.preview_frame, text="",
            font=(FONT, 10, "bold"), text_color="white",
            fg_color="transparent", corner_radius=6, height=22)
        self.lbl_duration.place(relx=1.0, rely=1.0, x=-12, y=-12, anchor="se")

        # Lyrics card — shares row 0, so it matches the cover card height exactly
        self.lyrics_frame = ctk.CTkScrollableFrame(
            mf, corner_radius=18,
            fg_color=C["card"], border_color=C["border2"], border_width=1,
            label_text="📜 Lyrics", label_font=(FONT, 12, "bold"))
        self.lyrics_frame.grid(row=0, column=1, sticky="nsew")
        self.lyrics_frame.grid_columnconfigure(0, weight=1)

        # Title / artist caption: row 1, under the cover card only
        meta = ctk.CTkFrame(mf, fg_color="transparent")
        meta.grid(row=1, column=0, sticky="ew", padx=(2, 10), pady=(8, 0))
        meta.grid_columnconfigure(0, weight=1)
        self.lbl_title = ctk.CTkLabel(
            meta, text="", font=(FONT, 15, "bold"),
            wraplength=520, justify="left", anchor="w",
            text_color=C["bright"])
        self.lbl_title.grid(row=0, column=0, sticky="ew")
        self.lbl_artist = ctk.CTkLabel(
            meta, text="", font=(FONT, 12), anchor="w",
            text_color=C["dim"])
        self.lbl_artist.grid(row=1, column=0, sticky="ew")
        self.lbl_lyrics = ctk.CTkLabel(
            self.lyrics_frame,
            text="Analyze a song to load lyrics automatically...",
            wraplength=400, text_color=C["very_dim"], justify="left",
            font=(FONT, 12))
        self.lbl_lyrics.pack(pady=12, padx=12, fill="x", expand=True)

        # ── Format / Quality / Path  (compact single card) ───
        controls = ctk.CTkFrame(p, fg_color=C["card"],
                                corner_radius=16, border_width=1,
                                border_color=C["border2"])
        controls.grid(row=2, column=0, sticky="ew", padx=PADX, pady=(0, 10))
        controls.grid_columnconfigure(1, weight=1)
        controls.grid_columnconfigure(3, weight=1)

        # Row A: Format + Quality
        self.lbl_format_dl = ctk.CTkLabel(
            controls, text="Format", font=(FONT, 11), text_color=C["dim"])
        self.lbl_format_dl.grid(
            row=0, column=0, sticky="w", padx=(16, 8), pady=(12, 2))

        # CTkComboBox instead of CTkOptionMenu: the option menu's first redraw
        # lazily loads CTk's shape font and freezes the UI for ~2 s.
        self.mode_menu = ctk.CTkComboBox(
            controls, values=list(FORMAT_QUALITIES.keys()),
            height=36, corner_radius=10, font=(FONT, 12), state="readonly",
            command=self.update_quality_options)
        self.mode_menu.grid(row=0, column=1, sticky="ew",
                            padx=(0, 18), pady=(12, 2))
        self.mode_menu.set(list(FORMAT_QUALITIES.keys())[0])

        self.lbl_quality_dl = ctk.CTkLabel(
            controls, text="Quality", font=(FONT, 11), text_color=C["dim"])
        self.lbl_quality_dl.grid(
            row=0, column=2, sticky="w", padx=(0, 8), pady=(12, 2))
        self.quality_combo = ctk.CTkComboBox(
            controls, height=36, corner_radius=10, font=(FONT, 12))
        self.quality_combo.grid(row=0, column=3, sticky="ew",
                                padx=(0, 16), pady=(12, 2))
        self.update_quality_options(list(FORMAT_QUALITIES.keys())[0])

        # Thin divider
        ctk.CTkFrame(controls, height=1,
                     fg_color=C["border"]).grid(
            row=1, column=0, columnspan=4, sticky="ew",
            padx=14, pady=(6, 4))

        # Row B: Path
        path_inner = ctk.CTkFrame(controls, fg_color="transparent")
        path_inner.grid(row=2, column=0, columnspan=4,
                        sticky="ew", padx=12, pady=(0, 10))
        path_inner.grid_columnconfigure(0, weight=1)

        self.path_frame = path_inner          # alias used in update_path_display
        self.path_entry = ctk.CTkEntry(
            path_inner, border_width=0, fg_color="transparent",
            font=(FONT, 12), text_color=C["mid"])
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(6, 8))
        self.update_path_display()
        self.btn_path = ctk.CTkButton(
            path_inner, text="📁  Change", width=130, height=32,
            corner_radius=9, font=(FONT, 11, "bold"),
            command=self.select_folder)
        self.btn_path.grid(row=0, column=1)

        # ── Download + Cancel buttons ─────────────────────────
        btn_row = ctk.CTkFrame(p, fg_color="transparent")
        btn_row.grid(row=3, column=0, sticky="ew", padx=PADX, pady=(0, 6))
        btn_row.grid_columnconfigure(0, weight=1)
        self._btn_row = btn_row

        self.btn_download = GradientButton(
            btn_row, text="⬇   ADD TO LIBRARY",
            height=48, font=(FONT, 14, "bold"), state="disabled",
            command=self.enqueue_current)
        self.btn_download.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.cancel_btn = ctk.CTkButton(
            btn_row,
            text=self.t("cancel_download", "Cancel"),
            command=self.cancel_download,
            fg_color=C.get("error", "#E5484D"),
            hover_color=C.get("error_hover", "#C62828"),
            width=170, height=48, corner_radius=24,
            font=(FONT, 13, "bold"),
        )
        self.cancel_btn.grid(row=0, column=1, padx=(8, 0))
        self.cancel_btn.grid_remove()  # hidden until a download starts

        # ── Progress ─────────────────────────────────────────
        prog = ctk.CTkFrame(p, fg_color="transparent")
        prog.grid(row=4, column=0, sticky="ew", padx=PADX, pady=(2, 10))
        prog.grid_columnconfigure(0, weight=1)

        self.progress_bar = GradientProgressBar(prog)
        self.progress_bar.grid(row=0, column=0, sticky="ew")

        self.lbl_speed = ctk.CTkLabel(
            prog, text=" ", font=(FONT, 10), text_color="#888", height=14)
        self.lbl_speed.grid(row=1, column=0, pady=(2, 0))

        self.progress_bar_pl = GradientProgressBar(prog)
        self.progress_bar_pl.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        self.progress_bar_pl.grid_remove()

        self.lbl_pl_progress = ctk.CTkLabel(
            prog, text="", font=(FONT, 10), text_color=C["dim"], height=14)
        self.lbl_pl_progress.grid(row=3, column=0, pady=(1, 0))
        self.lbl_pl_progress.grid_remove()

    def _sync_thumb_bg(self):
        """Match the raw tk image label's bg to the window background —
        the rendered cover's rounded corners are composited over the same
        colour, so everything blends into one seamless card."""
        try:
            bg = C["bg"][1] if ctk.get_appearance_mode() == "Dark" else C["bg"][0]
            self.thumb_img.configure(bg=bg)
        except Exception:
            pass

    def _show_cancel_button(self):
        self.cancel_btn.configure(
            text=self.t("cancel_download", "Cancel"), state="normal")
        self.btn_download.grid_configure(columnspan=1)
        self.cancel_btn.grid()

    def _hide_cancel_button(self):
        self.cancel_btn.grid_remove()
        self.btn_download.grid_configure(columnspan=2)

    # ── Library Page ──────────────────────────────────────────────────────────

    def setup_library_tab(self):
        self.tab_play.grid_columnconfigure(0, weight=1)
        self.tab_play.grid_rowconfigure(1, weight=1)
        hdr = ctk.CTkFrame(self.tab_play, fg_color="transparent")
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew",
                 padx=24, pady=(22, 8))
        self.lbl_collection = ctk.CTkLabel(
            hdr, text="MY COLLECTION",
            font=(FONT, 14, "bold"), text_color=C["dim"])
        self.lbl_collection.pack(side="left")
        self.lbl_lib_count = ctk.CTkLabel(
            hdr, text="", font=(FONT, 12), text_color=C["very_dim"])
        self.lbl_lib_count.pack(side="right")

        self.lib_scroll = LibraryList(self.tab_play)
        self.lib_scroll.grid(row=1, column=0, sticky="nsew",
                             padx=(20, 4), pady=(0, 16))
        self._lib_sb = ctk.CTkScrollbar(
            self.tab_play, command=self.lib_scroll.yview)
        self._lib_sb.grid(row=1, column=1, sticky="ns", padx=(0, 8),
                          pady=(0, 16))
        self.lib_scroll.configure(yscrollcommand=self._lib_sb.set)
        self.refresh_library_ui()

    # ── Converter Page ────────────────────────────────────────────────────────

    def setup_converter_tab(self):
        self.tab_conv.grid_columnconfigure(0, weight=1)
        self.tab_conv.grid_rowconfigure(0, weight=1)

        card = ctk.CTkFrame(self.tab_conv, corner_radius=20,
                            fg_color=C["card"], border_width=1,
                            border_color=C["border2"])
        card.grid(row=0, column=0, padx=48, pady=40, sticky="ew")

        self.lbl_conv_title = ctk.CTkLabel(
            card, text="Local File Converter",
            font=(FONT, 21, "bold"), text_color=C["bright"])
        self.lbl_conv_title.pack(pady=(32, 4))
        self.lbl_conv_subtitle = ctk.CTkLabel(
            card,
            text="Convert any audio or video file to a different format",
            font=(FONT, 12), text_color=C["dim"])
        self.lbl_conv_subtitle.pack(pady=(0, 20))
        self.btn_conv_select = ctk.CTkButton(
            card, text="📁   Select File to Convert",
            height=52, corner_radius=14, font=(FONT, 13, "bold"),
            command=self.select_local_file)
        self.btn_conv_select.pack(pady=4, padx=56, fill="x")
        fmt_row = ctk.CTkFrame(card, fg_color="transparent")
        fmt_row.pack(pady=14)
        self.lbl_conv_target = ctk.CTkLabel(
            fmt_row, text="Target Format:", font=(FONT, 12),
            text_color=C["dim"])
        self.lbl_conv_target.pack(side="left", padx=(0, 10))
        self.conv_target = ctk.CTkSegmentedButton(
            fmt_row,
            values=["MP3", "AAC", "WAV", "FLAC", "OGG", "MP4", "MKV"],
            command=self._on_conv_fmt_change)
        self.conv_target.pack(side="left")
        self.conv_target.set("MP3")
        self.conv_qual_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.conv_qual_frame.pack(pady=4)
        self.lbl_conv_quality_label = ctk.CTkLabel(
            self.conv_qual_frame, text="Quality:",
            font=(FONT, 12), text_color=C["dim"])
        self.lbl_conv_quality_label.pack(side="left", padx=(0, 8))
        self.conv_quality_combo = ctk.CTkComboBox(
            self.conv_qual_frame,
            values=["320 kbps", "256 kbps", "192 kbps", "128 kbps"],
            width=200, height=40, corner_radius=10)
        self.conv_quality_combo.pack(side="left")
        self.conv_quality_combo.set("320 kbps")
        self.conv_status_label = ctk.CTkLabel(
            card, text="", text_color=C["mid"], font=(FONT, 11))
        self.conv_status_label.pack(pady=6)
        self.btn_conv_run = ctk.CTkButton(
            card, text="▶   START CONVERSION",
            height=54, corner_radius=27, font=(FONT, 14, "bold"),
            fg_color=C["btn_conv"], border_width=1,
            border_color=C["btn_conv_brd"],
            text_color=C["bright"], command=self.start_conversion_thread)
        self.btn_conv_run.pack(pady=(14, 32), padx=56, fill="x")

    def _on_conv_fmt_change(self, value):
        if value in {"MP3", "AAC", "WAV", "FLAC", "OGG"}:
            # 'before' keeps the row in its original spot when re-shown
            # (a bare pack() would drop it below the START button).
            self.conv_qual_frame.pack(pady=4, before=self.conv_status_label)
        else:
            self.conv_qual_frame.pack_forget()

    # ── Scroll isolation ──────────────────────────────────────────────────────

    def _setup_scroll_isolation(self):
        import sys as _sys

        def _make_scroll(canvas):
            if _sys.platform == "darwin":
                # macOS reports small deltas (already in "lines")
                return lambda e: canvas.yview_scroll(-int(e.delta) or 0, "units")
            # Windows reports multiples of 120
            def _fn(e):
                step = int(-1 * (e.delta / 120))
                if step == 0 and e.delta:
                    step = -1 if e.delta > 0 else 1
                canvas.yview_scroll(step, "units")
            return _fn

        def _bind_inner(frame):
            # CTkScrollableFrame exposes its canvas; LibraryList IS a canvas
            canvas = getattr(frame, "_parent_canvas", frame)
            if _sys.platform.startswith("linux"):
                # X11 delivers wheel events as Button-4 / Button-5
                up = lambda _e: canvas.yview_scroll(-1, "units")
                dn = lambda _e: canvas.yview_scroll(1, "units")
                frame.bind("<Enter>", lambda _:
                           (canvas.bind_all("<Button-4>", up),
                            canvas.bind_all("<Button-5>", dn)))
                frame.bind("<Leave>", lambda _:
                           (canvas.unbind_all("<Button-4>"),
                            canvas.unbind_all("<Button-5>")))
            else:
                fn = _make_scroll(canvas)
                frame.bind("<Enter>", lambda _:
                           canvas.bind_all("<MouseWheel>", fn))
                frame.bind("<Leave>", lambda _:
                           canvas.unbind_all("<MouseWheel>"))

        for frame in (self.lyrics_frame, self.lib_scroll):
            _bind_inner(frame)
