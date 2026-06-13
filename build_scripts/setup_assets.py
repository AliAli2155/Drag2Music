#!/usr/bin/env python3
"""
Generate the Drag2Music icon for every platform from ONE master image, so the
app looks identical on Windows, macOS and Linux.

Outputs (all derived from the same 1024px master):
    Drag2Music.ico        (project root, multi-size .ico)
    assets/icon.ico       (Windows  — taskbar / titlebar / installer)
    assets/icon.png       (Linux    — iconphoto, 512px)
    assets/icon.icns       (macOS    — .app bundle)

Run once before building, or any time the artwork changes:
    python build_scripts/setup_assets.py
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR   = os.path.join(PROJECT_ROOT, "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

# Brand palette
GRAD_TOP  = (34, 224, 101)   # bright green (top)
GRAD_BOT  = (12, 140, 58)    # deep green   (bottom)
NOTE_CLR  = (255, 255, 255)  # white line-art
DOT_CLR   = (74, 93, 107)    # blue-grey note-head centre (from the reference)


def _qbez(p0, p1, p2, n=28):
    """Quadratic-bezier polyline between three points."""
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        pts.append((
            u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
        ))
    return pts


def _make_icon_image(size: int):
    """Master Drag2Music icon: rounded green-gradient square with a white
    'download music' mark — an eighth note inside an open ring with a
    download arrow. Rendered supersampled, then downscaled for smooth edges."""
    from PIL import Image, ImageDraw
    import math

    SS = 4                       # supersample factor
    S  = size * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # ── Vertical brand gradient ──────────────────────────────────────────────
    grad = Image.new("RGB", (1, S))
    for y in range(S):
        t = y / (S - 1)
        grad.putpixel((0, y), tuple(
            int(GRAD_TOP[i] + (GRAD_BOT[i] - GRAD_TOP[i]) * t) for i in range(3)))
    grad = grad.resize((S, S))

    # ── Rounded-square mask (modern app-icon silhouette) ─────────────────────
    mask = Image.new("L", (S, S), 0)
    m = int(S * 0.045)
    r = int(S * 0.225)
    ImageDraw.Draw(mask).rounded_rectangle([m, m, S - m, S - m],
                                           radius=r, fill=255)
    img.paste(grad, (0, 0), mask)

    draw  = ImageDraw.Draw(img)
    white = (*NOTE_CLR, 255)

    def P(fx, fy):
        return (fx * S, fy * S)

    def cap(p, w):                       # round line cap
        rr = w / 2
        draw.ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr], fill=white)

    def stroke(pts, w):                  # thick rounded polyline
        draw.line(pts, fill=white, width=int(w), joint="curve")
        cap(pts[0], w)
        cap(pts[-1], w)

    # ── Open ring (nearly full circle, opening at the bottom) ─────────────────
    # Drawn as a continuous polyline rather than draw.arc: arc ends slightly
    # short of its rounded cap, which leaves a gap that reads as a stray dot.
    ccx, ccy, rc = 0.490, 0.460, 0.410
    wc  = int(0.058 * S)
    a0, a1 = 92, 372                     # bottom (6 o'clock) → right (~4 o'clock)
    n = 160
    ring_pts = [(ccx * S + rc * S * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
                 ccy * S + rc * S * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
                for i in range(n + 1)]
    stroke(ring_pts, wc)

    # ── Eighth note (inside, centre) ──────────────────────────────────────────
    wn = int(0.046 * S)
    hx, hy, rh = 0.405, 0.595, 0.090
    stem_x = hx + rh * 0.80
    stroke([P(stem_x, 0.290), P(stem_x, hy)], wn)              # stem
    stroke(_qbez(P(stem_x, 0.290), P(0.610, 0.300),
                 P(0.560, 0.450)), wn)                         # flag hook
    draw.ellipse([P(hx - rh, hy - rh)[0], P(hx - rh, hy - rh)[1],
                  P(hx + rh, hy + rh)[0], P(hx + rh, hy + rh)[1]],
                 fill=white)                                   # white head ring
    rd = rh * 0.60                                             # blue-grey centre
    draw.ellipse([P(hx - rd, hy - rd)[0], P(hx - rd, hy - rd)[1],
                  P(hx + rd, hy + rd)[0], P(hx + rd, hy + rd)[1]],
                 fill=(*DOT_CLR, 255))

    # ── Download arrow (in the bottom-right gap) ──────────────────────────────
    wa = int(0.052 * S)
    ax = 0.745
    stroke([P(ax, 0.545), P(ax, 0.820)], wa)                  # shaft
    stroke([P(ax - 0.092, 0.718), P(ax, 0.830),
            P(ax + 0.092, 0.718)], wa)                         # head chevron

    return img.resize((size, size), Image.LANCZOS)


def _load(src, size):
    from PIL import Image
    return Image.open(src).convert("RGBA").resize((size, size), Image.LANCZOS)


def _ico_from(src_png, dst):
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    _load(src_png, 256).save(dst, format="ICO", sizes=sizes)
    print(f"  {os.path.relpath(dst, PROJECT_ROOT)}  <- {os.path.basename(src_png)}")


def _icns_from(src_png, dst):
    from PIL import Image
    base = _load(src_png, 512)
    if sys.platform == "darwin":
        # Highest fidelity: build a proper .iconset via iconutil
        import subprocess, tempfile, shutil as _sh
        iconset = tempfile.mkdtemp(suffix=".iconset")
        try:
            for s in (16, 32, 64, 128, 256, 512):
                base.resize((s, s), Image.LANCZOS).save(
                    os.path.join(iconset, f"icon_{s}x{s}.png"))
                d2 = min(s * 2, 512)
                base.resize((d2, d2), Image.LANCZOS).save(
                    os.path.join(iconset, f"icon_{s}x{s}@2x.png"))
            subprocess.run(["iconutil", "-c", "icns", iconset, "-o", dst],
                           check=True)
            print(f"  {os.path.relpath(dst, PROJECT_ROOT)} (iconutil)")
            return
        except Exception as e:
            print(f"  WARNING: iconutil failed: {e}; using Pillow.")
        finally:
            _sh.rmtree(iconset, ignore_errors=True)
    try:
        base.save(dst, format="ICNS",
                  sizes=[(s, s) for s in (16, 32, 48, 64, 128, 256, 512)])
        print(f"  {os.path.relpath(dst, PROJECT_ROOT)} (Pillow)")
    except Exception as e:
        print(f"  WARNING: could not write {os.path.basename(dst)}: {e}")


def main() -> None:
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("ERROR: Pillow is required (pip install Pillow).")
        sys.exit(1)

    white = os.path.join(ASSETS_DIR, "icon-white.png")
    black = os.path.join(ASSETS_DIR, "icon-black.png")

    # No themed variants supplied → fall back to the procedural design.
    if not (os.path.exists(white) or os.path.exists(black)):
        print("No icon-white/black.png found — generating procedural icon.")
        proc = os.path.join(ASSETS_DIR, "icon-white.png")
        _make_icon_image(512).save(proc)
        white = black = proc

    print("Generating themed icons (Dark uses white, Light uses black) ...")
    for variant, src in (("white", white), ("black", black)):
        if os.path.exists(src):
            _ico_from(src, os.path.join(ASSETS_DIR, f"icon-{variant}.ico"))
            _icns_from(src, os.path.join(ASSETS_DIR, f"icon-{variant}.icns"))

    # Static fallback used by the .exe / installer / .app bundle (can't switch
    # at runtime) — default to the white (dark-theme) mark.
    default = white if os.path.exists(white) else black
    _ico_from(default,  os.path.join(PROJECT_ROOT, "Drag2Music.ico"))
    _ico_from(default,  os.path.join(ASSETS_DIR, "icon.ico"))
    _icns_from(default, os.path.join(ASSETS_DIR, "icon.icns"))
    print("Icon setup complete.")


if __name__ == "__main__":
    main()
