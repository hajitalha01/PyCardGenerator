"""Generate application icon (.ico) and placeholder assets.

Creates a professional 256x256 RGBA icon and smaller variants
bundled into a single .ico file, plus .gitkeep placeholders
for empty asset directories so PyInstaller includes them.
"""

import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from utils.resource_path import PathManager

_pm = PathManager()
ASSETS_DIR = _pm.assets_dir
ICONS_DIR = _pm.icons_dir
FONTS_DIR = _pm.fonts_dir
TEMPLATES_DIR = _pm.templates_dir

# ------------------------------------------------------------------
# Icon generation
# ------------------------------------------------------------------


def _create_icon_png(size: int) -> Image.Image:
    """Create a single RGBA PNG frame for the application icon.

    Design: rounded-ID-card shape on a transparent background,
    with a subtle gradient overlay.
    """
    img: Image.Image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(img)

    # Card body dimensions (rounded rect, centred)
    margin: int = max(2, size // 12)
    card_w: int = size - 2 * margin
    card_h: int = int(card_w * 54.0 / 85.6)  # ID-1 aspect ratio
    card_x: int = margin
    card_y: int = (size - card_h) // 2
    radius: int = max(2, size // 14)

    # Shadow
    shadow_offset: int = max(1, size // 40)
    draw.rounded_rectangle(
        [card_x + shadow_offset, card_y + shadow_offset,
         card_x + card_w + shadow_offset, card_y + card_h + shadow_offset],
        radius=radius,
        fill=(0, 0, 0, 40),
    )

    # Card fill — blue gradient (top to bottom)
    for y in range(card_y, card_y + card_h):
        ratio: float = (y - card_y) / card_h
        r: int = int(30 + 25 * ratio)      # 30 → 55
        g: int = int(100 + 55 * (1 - ratio))  # 100 → 45
        b: int = int(180 + 75 * (1 - ratio))  # 180 → 105
        draw.line([(card_x, y), (card_x + card_w, y)], fill=(r, g, b, 255))

    # Card border (rounded)
    draw.rounded_rectangle(
        [card_x, card_y, card_x + card_w, card_y + card_h],
        radius=radius,
        outline=(255, 255, 255, 200),
        width=max(1, size // 80),
    )

    # Chip icon (small gold rectangle, left side)
    chip_w: int = max(4, size // 8)
    chip_h: int = max(6, size // 6)
    chip_x: int = card_x + max(3, size // 16)
    chip_y: int = card_y + max(3, size // 10)
    draw.rounded_rectangle(
        [chip_x, chip_y, chip_x + chip_w, chip_y + chip_h],
        radius=max(1, chip_w // 6),
        fill=(212, 175, 55, 220),  # gold
    )

    # ID circle / photo placeholder (right side)
    photo_size: int = max(8, size // 4)
    photo_x: int = card_x + card_w - photo_size - max(3, size // 16)
    photo_y: int = card_y + (card_h - photo_size) // 2
    draw.ellipse(
        [photo_x, photo_y, photo_x + photo_size, photo_y + photo_size],
        fill=(200, 200, 220, 180),
        outline=(255, 255, 255, 200),
        width=max(1, size // 80),
    )

    # Try to add "ID" text label below the chip
    try:
        font_size: int = max(6, size // 12)
        font: ImageFont.FreeTypeFont = ImageFont.truetype(
            "arial.ttf", font_size
        )
        label: str = "ID"
        bbox = font.getbbox(label)
        tw: int = bbox[2] - bbox[0]
        th: int = bbox[3] - bbox[1]
        lx: int = chip_x + (chip_w - tw) // 2
        ly: int = chip_y + chip_h + max(1, size // 40)
        draw.text((lx, ly), label, font=font, fill=(255, 255, 255, 180))
    except Exception:
        pass  # fallback — no label is fine

    return img


def build_icon() -> None:
    """Generate app.ico with multiple resolutions."""
    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    sizes: list[int] = [16, 24, 32, 48, 64, 128, 256]
    images: list[Image.Image] = [_create_icon_png(s) for s in sizes]

    # Save as .ico using Pillow
    icon_path: Path = ICONS_DIR / "app.ico"
    images[0].save(
        icon_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print(f"Created {icon_path}  ({len(sizes)} resolutions)")


# ------------------------------------------------------------------
# Placeholder .gitkeep files
# ------------------------------------------------------------------


def create_gitkeep() -> None:
    """Write a .gitkeep into each empty asset directory."""
    for directory in (ASSETS_DIR, ICONS_DIR, FONTS_DIR, TEMPLATES_DIR):
        directory.mkdir(parents=True, exist_ok=True)
        keep: Path = directory / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")
            print(f"Created {keep}")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

if __name__ == "__main__":
    build_icon()
    create_gitkeep()
