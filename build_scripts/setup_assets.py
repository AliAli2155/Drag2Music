#!/usr/bin/env python3
"""
Generate placeholder icon assets for TuneFetch.
Copies TuneFetch.ico (project root) → assets/icon.ico
Generates assets/icon.png (512x512 green gradient)
Generates assets/icon.icns (macOS, requires Pillow)

Run once before building:
    python build_scripts/setup_assets.py
"""
import os
import sys
import shutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR   = os.path.join(PROJECT_ROOT, "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)


def copy_ico() -> None:
    src = os.path.join(PROJECT_ROOT, "TuneFetch.ico")
    dst = os.path.join(ASSETS_DIR, "icon.ico")
    if os.path.exists(dst):
        print(f"  icon.ico already exists — skipping.")
        return
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"  Copied TuneFetch.ico → assets/icon.ico")
    else:
        _generate_ico_with_pillow(dst)


def _generate_ico_with_pillow(dst: str) -> None:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("  WARNING: Pillow not installed, cannot generate icon.ico placeholder.")
        print("  Place a valid icon.ico in the assets/ folder manually.")
        return
    img = _make_icon_image(256)
    img.save(dst, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"  Generated placeholder → {dst}")


def generate_png() -> None:
    dst = os.path.join(ASSETS_DIR, "icon.png")
    if os.path.exists(dst):
        print(f"  icon.png already exists — skipping.")
        return
    try:
        from PIL import Image
        img = _make_icon_image(512)
        img.save(dst, format="PNG")
        print(f"  Generated placeholder → {dst}")
    except ImportError:
        print("  WARNING: Pillow not installed, cannot generate icon.png.")
        print("  Place a valid 512x512 icon.png in the assets/ folder manually.")


def generate_icns() -> None:
    dst = os.path.join(ASSETS_DIR, "icon.icns")
    if os.path.exists(dst):
        print(f"  icon.icns already exists — skipping.")
        return
    src_png = os.path.join(ASSETS_DIR, "icon.png")
    if not os.path.exists(src_png):
        generate_png()
    if not os.path.exists(src_png):
        print("  WARNING: Cannot generate icon.icns without icon.png.")
        return

    # On macOS, use iconutil via a temp iconset
    if sys.platform == "darwin":
        import subprocess, tempfile
        iconset = tempfile.mkdtemp(suffix=".iconset")
        try:
            from PIL import Image
            base = Image.open(src_png).convert("RGBA")
            sizes = [16, 32, 64, 128, 256, 512]
            for s in sizes:
                img = base.resize((s, s), Image.LANCZOS)
                img.save(os.path.join(iconset, f"icon_{s}x{s}.png"))
                img2 = base.resize((s * 2, s * 2), Image.LANCZOS)
                img2.save(os.path.join(iconset, f"icon_{s}x{s}@2x.png"))
            subprocess.run(["iconutil", "-c", "icns", iconset, "-o", dst], check=True)
            print(f"  Generated → {dst}")
        except Exception as e:
            print(f"  WARNING: iconutil failed: {e}")
            print("  Place a valid icon.icns in assets/ manually.")
        finally:
            import shutil as _sh
            _sh.rmtree(iconset, ignore_errors=True)
    else:
        try:
            from PIL import Image
            base = Image.open(src_png).convert("RGBA")
            sizes = [(s, s) for s in [16, 32, 48, 64, 128, 256, 512]]
            base.save(dst, format="ICNS", sizes=sizes)
            print(f"  Generated placeholder → {dst}")
        except Exception as e:
            print(f"  WARNING: Could not generate icon.icns: {e}")
            print("  Place a valid icon.icns in assets/ manually.")


def _make_icon_image(size: int):
    """Create a simple TuneFetch branding icon."""
    from PIL import Image, ImageDraw, ImageFont
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Background circle
    margin = size // 16
    draw.ellipse([margin, margin, size - margin, size - margin], fill=(29, 185, 84, 255))
    # Inner circle
    inner = size // 4
    draw.ellipse([inner, inner, size - inner, size - inner], fill=(0, 0, 0, 180))
    # Music note dot
    dot_r = size // 10
    cx, cy = size // 2, size // 2
    draw.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=(29, 185, 84, 255))
    return img


def main() -> None:
    print("Setting up TuneFetch assets...")
    copy_ico()
    generate_png()
    generate_icns()
    print("Asset setup complete.")


if __name__ == "__main__":
    main()
