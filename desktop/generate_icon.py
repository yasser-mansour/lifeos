#!/usr/bin/env python3
"""Generates desktop/AppIcon.iconset from scratch — a solid indigo square
with the same concentric-ring "focus" mark used on the Android launcher
icon (see android/.../drawable/ic_launcher_foreground.xml). Run via
scripts/build_mac_app.sh, not committed as a binary."""

from pathlib import Path

from PIL import Image, ImageDraw

BG = (73, 84, 224, 255)  # #4954E0
MARK = (255, 255, 255, 255)

SIZES = [16, 32, 64, 128, 256, 512, 1024]


def render(size: int) -> Image.Image:
    scale = 4  # supersample for smooth strokes, then downsize
    canvas = size * scale
    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    radius = int(canvas * 0.22)
    draw.rounded_rectangle([0, 0, canvas - 1, canvas - 1], radius=radius, fill=BG)

    cx, cy = canvas * 0.5, canvas * 0.46
    outer_r = canvas * 0.22
    inner_r = canvas * 0.11
    dot_r = canvas * 0.037
    stroke = max(2, int(canvas * 0.045))

    draw.ellipse([cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r], outline=MARK, width=stroke)
    draw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], outline=MARK, width=stroke)
    draw.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=MARK)

    return img.resize((size, size), Image.LANCZOS)


def main():
    out_dir = Path(__file__).parent / "AppIcon.iconset"
    out_dir.mkdir(exist_ok=True)

    mapping = {
        16: ["icon_16x16.png"],
        32: ["icon_16x16@2x.png", "icon_32x32.png"],
        64: ["icon_32x32@2x.png"],
        128: ["icon_128x128.png"],
        256: ["icon_128x128@2x.png", "icon_256x256.png"],
        512: ["icon_256x256@2x.png", "icon_512x512.png"],
        1024: ["icon_512x512@2x.png"],
    }

    for size in SIZES:
        img = render(size)
        for filename in mapping.get(size, []):
            img.save(out_dir / filename)

    print(f"Wrote iconset to {out_dir}")


if __name__ == "__main__":
    main()
