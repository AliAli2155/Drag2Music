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
GRAD_TOP = (34, 224, 101)   # bright green (top)
GRAD_BOT = (12, 140, 58)    # deep green   (bottom)
NOTE_CLR = (255, 255, 255)  # white music note


def _make_icon_image(size: int):
    """Master Drag2Music icon: rounded green-gradient square with a white
    pair of beamed eighth notes. Rendered supersampled, then downscaled so
    edges stay smooth at every output size."""
    from PIL import Image, ImageDraw

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

    draw = ImageDraw.Draw(img)
    white = (*NOTE_CLR, 255)

    def px(fx, fy):
        return (int(fx * S), int(fy * S))

    # ── Beamed eighth notes (the universal "music" mark) ─────────────────────
    # Heads (slightly squashed ellipses → tilted note-head look)
    hw, hh = 0.118, 0.092
    lcx, lcy = 0.355, 0.700      # left head centre
    rcx, rcy = 0.645, 0.628      # right head centre
    sw = 0.044                   # stem width
    beam_t = 0.082               # beam thickness

    # Stems (right edge of each head, rising to the beam)
    l_stem_x = lcx + hw - sw
    r_stem_x = rcx + hw - sw
    draw.rectangle([*px(l_stem_x, 0.300), *px(l_stem_x + sw, lcy)], fill=white)
    draw.rectangle([*px(r_stem_x, 0.250), *px(r_stem_x + sw, rcy)], fill=white)

    # Beam (slanted bar joining the two stem tops)
    draw.polygon([
        px(l_stem_x,        0.300),
        px(r_stem_x + sw,   0.250),
        px(r_stem_x + sw,   0.250 + beam_t),
        px(l_stem_x,        0.300 + beam_t),
    ], fill=white)

    # Heads on top so the stem bottoms tuck in cleanly
    for hx, hy in ((lcx, lcy), (rcx, rcy)):
        draw.ellipse([*px(hx - hw, hy - hh), *px(hx + hw, hy + hh)], fill=white)

    return img.resize((size, size), Image.LANCZOS)


def generate_png(dst=None, size=512):
    dst = dst or os.path.join(ASSETS_DIR, "icon.png")
    _make_icon_image(size).save(dst, format="PNG")
    print(f"  Generated {os.path.relpath(dst, PROJECT_ROOT)} ({size}px)")
    return dst


def generate_ico(dst):
    master = _make_icon_image(256)
    sizes  = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    master.save(dst, format="ICO", sizes=sizes)
    print(f"  Generated {os.path.relpath(dst, PROJECT_ROOT)} (multi-size)")


def generate_icns(dst):
    src_png = os.path.join(ASSETS_DIR, "icon.png")
    if not os.path.exists(src_png):
        generate_png(src_png)

    if sys.platform == "darwin":
        # Highest fidelity: build a proper .iconset via iconutil
        import subprocess, tempfile, shutil as _sh
        from PIL import Image
        iconset = tempfile.mkdtemp(suffix=".iconset")
        try:
            base = _make_icon_image(1024).convert("RGBA")
            for s in (16, 32, 64, 128, 256, 512):
                base.resize((s, s), Image.LANCZOS).save(
                    os.path.join(iconset, f"icon_{s}x{s}.png"))
                base.resize((s * 2, s * 2), Image.LANCZOS).save(
                    os.path.join(iconset, f"icon_{s}x{s}@2x.png"))
            subprocess.run(["iconutil", "-c", "icns", iconset, "-o", dst],
                           check=True)
            print(f"  Generated {os.path.relpath(dst, PROJECT_ROOT)} (iconutil)")
        except Exception as e:
            print(f"  WARNING: iconutil failed: {e}; falling back to Pillow.")
            _icns_pillow(dst)
        finally:
            _sh.rmtree(iconset, ignore_errors=True)
    else:
        _icns_pillow(dst)


def _icns_pillow(dst):
    try:
        from PIL import Image
        base  = _make_icon_image(1024).convert("RGBA")
        sizes = [(s, s) for s in (16, 32, 48, 64, 128, 256, 512)]
        base.save(dst, format="ICNS", sizes=sizes)
        print(f"  Generated {os.path.relpath(dst, PROJECT_ROOT)} (Pillow)")
    except Exception as e:
        print(f"  WARNING: Could not generate icon.icns: {e}")


def main() -> None:
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("ERROR: Pillow is required (pip install Pillow).")
        sys.exit(1)

    print("Generating Drag2Music icons from master...")
    generate_ico(os.path.join(PROJECT_ROOT, "Drag2Music.ico"))
    generate_ico(os.path.join(ASSETS_DIR, "icon.ico"))
    generate_png(os.path.join(ASSETS_DIR, "icon.png"), 512)
    generate_icns(os.path.join(ASSETS_DIR, "icon.icns"))
    print("Icon setup complete — identical artwork on all platforms.")


if __name__ == "__main__":
    main()
