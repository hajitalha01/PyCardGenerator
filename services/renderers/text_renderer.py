"""Text rendering for card fields.

Handles every text-related visual property: font family,
size, bold, italic, underline, alignment, rotation, opacity,
foreground and background colours, word wrapping, and auto
font-size reduction to fit the field rectangle.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from models.field import TemplateField
from utils.logger import setup_logger

logger = setup_logger(__name__)

# ------------------------------------------------------------------
# Font resolution
# ------------------------------------------------------------------

_WINDOWS_FONT_DIRS: tuple[str, ...] = (
    r"C:\Windows\Fonts",
    r"C:\Windows\WinSxS\amd64_microsoft-windows-f..onecore-fonts_31bf3856ad364e35_10.0.26100.1_none_eca354117831f639",
)

# Map font family names to filename stems (case-insensitive).
_FONT_ALIASES: dict[str, str] = {
    "arial": "arial",
    "arial black": "ariblk",
    "calibri": "calibri",
    "cambria": "cambria",
    "candara": "candara",
    "comic sans ms": "comic",
    "consolas": "consolas",
    "constantia": "constan",
    "corbel": "corbel",
    "courier new": "cour",
    "georgia": "georgia",
    "impact": "impact",
    "lucida console": "lucon",
    "lucida sans unicode": "l_10646",
    "microsoft sans serif": "micross",
    "palatino linotype": "pala",
    "segoe ui": "segoeui",
    "tahoma": "tahoma",
    "times new roman": "times",
    "trebuchet ms": "trebuc",
    "verdana": "verdana",
}

# Suffixes for font variants.
_BOLD_SUFFIX: str = "bd"
_ITALIC_SUFFIX: str = "i"
_BOLD_ITALIC_SUFFIX: str = "bi"


def _find_font_path(
    family: str, bold: bool = False, italic: bool = False
) -> str | None:
    """Locate a TrueType font file for the given family and style.

    Searches ``_WINDOWS_FONT_DIRS`` and also checks every directory
    listed in the ``PILLOW_FONTS`` environment variable.

    Args:
        family: Font family name (e.g. ``'Arial'``).
        bold:   Whether to use the bold variant.
        italic: Whether to use the italic variant.

    Returns:
        The absolute font file path, or ``None`` if not found.
    """
    stem: str | None = _FONT_ALIASES.get(family.strip().lower())
    if stem is None:
        return None

    if bold and italic:
        candidates: list[str] = [
            f"{stem}{_BOLD_ITALIC_SUFFIX}.ttf",
            f"{stem}{_BOLD_ITALIC_SUFFIX}.ttc",
        ]
    elif bold:
        candidates = [
            f"{stem}{_BOLD_SUFFIX}.ttf",
            f"{stem}{_BOLD_SUFFIX}.ttc",
        ]
    elif italic:
        candidates = [
            f"{stem}{_ITALIC_SUFFIX}.ttf",
            f"{stem}{_ITALIC_SUFFIX}.ttc",
        ]
    else:
        candidates = [f"{stem}.ttf", f"{stem}.ttc"]

    search_dirs: list[str] = list(_WINDOWS_FONT_DIRS)
    extra: str | None = os.environ.get("PILLOW_FONTS")
    if extra:
        search_dirs.append(extra)

    for directory in search_dirs:
        base: Path = Path(directory)
        for filename in candidates:
            full: Path = base / filename
            if full.is_file():
                return str(full)

    return None


def _get_font(
    family: str, size: int, bold: bool = False, italic: bool = False
) -> ImageFont.FreeTypeFont:
    """Return a TrueType font for the requested face and style.

    Falls back to Pillow's default bitmap font when the requested
    family cannot be found on disk.

    Args:
        family: Font family name.
        size:   Font size in points.
        bold:   Apply bold weight.
        italic: Apply italic slant.

    Returns:
        A Pillow ``FreeTypeFont`` instance.
    """
    path: str | None = _find_font_path(family, bold, italic)
    if path:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            logger.warning("Failed to load font %s, falling back", path)

    logger.debug("Font '%s' (bold=%s italic=%s) not found, using default", family, bold, italic)
    return ImageFont.load_default()


# ------------------------------------------------------------------
# Text layout helpers
# ------------------------------------------------------------------


def _word_wrap(
    text: str, font: ImageFont.FreeTypeFont, max_width: int
) -> list[str]:
    """Split *text* into lines that each fit within *max_width*.

    Args:
        text: Input text (may contain ``\\n``).
        font: The font used for measurement.
        max_width: Maximum line width in pixels.

    Returns:
        A list of wrapped lines.
    """
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        words: list[str] = paragraph.split()
        current: list[str] = []
        for word in words:
            trial: str = " ".join(current + [word]) if current else word
            w: int = font.getbbox(trial)[2]
            if w <= max_width or not current:
                current.append(word)
            else:
                lines.append(" ".join(current))
                current = [word]
        if current:
            lines.append(" ".join(current))
    return lines


def _measure_lines(
    lines: list[str], font: ImageFont.FreeTypeFont
) -> tuple[int, int]:
    """Measure total width and height of wrapped lines.

    Args:
        lines: List of text lines.
        font:  The font for measurement.

    Returns:
        ``(max_width, total_height)`` in pixels.
    """
    max_w: int = 0
    line_h: int = font.getbbox("Ag")[3] + 2  # vertical advance + small gap
    for line in lines:
        w: int = font.getbbox(line)[2] if line else 0
        if w > max_w:
            max_w = w
    return max_w, line_h * len(lines)


def _auto_resize_font(
    text: str,
    font_family: str,
    bold: bool,
    italic: bool,
    start_size: int,
    max_width: int,
    max_height: int,
) -> tuple[int, ImageFont.FreeTypeFont]:
    """Reduce font size until the text fits the given rectangle.

    Args:
        text: The text to measure.
        font_family: Font family name.
        bold: Apply bold weight.
        italic: Apply italic slant.
        start_size: Initial font size in points.
        max_width: Maximum allowed width in pixels.
        max_height: Maximum allowed height in pixels.

    Returns:
        ``(final_size, font)`` that fits the rectangle.
    """
    size: int = start_size
    font: ImageFont.FreeTypeFont = _get_font(font_family, size, bold, italic)

    while size > 4:
        lines: list[str] = _word_wrap(text, font, max_width)
        tw: int
        th: int
        tw, th = _measure_lines(lines, font)
        if tw <= max_width and th <= max_height:
            return size, font
        size -= 1
        font = _get_font(font_family, size, bold, italic)

    return size, font


# ------------------------------------------------------------------
# Main rendering function
# ------------------------------------------------------------------


def render_text(
    canvas: Image.Image,
    field: TemplateField,
    user_value: str,
    px_per_mm: float,
) -> None:
    """Render a text field onto the card canvas.

    Handles background colour, word wrapping, auto-resize, text
    alignment, rotation, and opacity.

    Args:
        canvas: The target RGBA canvas (modified in place).
        field: The field definition with all visual properties.
        user_value: The text content to render.
        px_per_mm: Pixels-per-millimetre conversion factor.
    """
    if not field.visible:
        return

    # Convert mm to px
    x: int = round(field.x * px_per_mm)
    y: int = round(field.y * px_per_mm)
    w: int = round(field.width * px_per_mm)
    h: int = round(field.height * px_per_mm)

    if w <= 0 or h <= 0:
        return

    text: str = user_value or field.default_value or ""
    if not text:
        return

    # --- Background fill ---
    if field.background_color and field.background_color != "#FFFFFF":
        bg_rgb: tuple[int, int, int] = _hex_to_rgb(field.background_color)
        bg_opacity: int = round(255 * field.opacity)
        bg_layer: Image.Image = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        bg_draw: ImageDraw.ImageDraw = ImageDraw.Draw(bg_layer)
        bg_draw.rectangle([x, y, x + w, y + h], fill=(*bg_rgb, bg_opacity))
        canvas.alpha_composite(bg_layer)

    # --- Font ---
    font: ImageFont.FreeTypeFont = _get_font(
        field.font_family,
        field.font_size,
        field.bold,
        field.italic,
    )

    # --- Auto-resize ---
    font_size: int
    font_size, font = _auto_resize_font(
        text,
        field.font_family,
        field.bold,
        field.italic,
        field.font_size,
        w - 8,   # 4 px padding each side
        h - 8,
    )

    # --- Word wrap ---
    lines: list[str] = _word_wrap(text, font, w - 8)

    # --- Measure ---
    line_h: int = font.getbbox("Ag")[3] + 2
    text_h: int = len(lines) * line_h

    # --- Alignment and vertical centring ---
    align: str = field.alignment or "left"
    text_color: tuple[int, int, int] = _hex_to_rgb(field.font_color)
    opacity_scale: int = round(255 * field.opacity)

    # Create a temporary layer for the text so we can composite with opacity
    text_layer: Image.Image = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    text_draw: ImageDraw.ImageDraw = ImageDraw.Draw(text_layer)

    y_offset: int = y + (h - text_h) // 2

    for line in lines:
        line_w: int = font.getbbox(line)[2] if line else 0

        if align == "center":
            lx: int = x + (w - line_w) // 2
        elif align == "right":
            lx: int = x + w - line_w - 4
        else:
            lx = x + 4  # left

        if line:
            text_draw.text(
                (lx, y_offset),
                line,
                font=font,
                fill=(*text_color, opacity_scale),
            )

        y_offset += line_h

    # --- Underline ---
    if field.underline:
        y_offset = y + (h - text_h) // 2
        for line in lines:
            line_w = font.getbbox(line)[2] if line else 0
            if align == "center":
                lx = x + (w - line_w) // 2
            elif align == "right":
                lx = x + w - line_w - 4
            else:
                lx = x + 4

            underline_y: int = y_offset + line_h - 2
            text_draw.line(
                [(lx, underline_y), (lx + line_w, underline_y)],
                fill=(*text_color, opacity_scale),
                width=max(1, round(font_size / 12)),
            )
            y_offset += line_h

    # --- Rotation ---
    if field.rotation:
        text_layer = text_layer.rotate(
            field.rotation,
            center=(x + w // 2, y + h // 2),
            resample=Image.Resampling.BICUBIC,
            expand=False,
        )

    # --- Composite ---
    canvas.alpha_composite(text_layer)


# ------------------------------------------------------------------
# Colour helper
# ------------------------------------------------------------------

_HEX_COLOR_CACHE: dict[str, tuple[int, int, int]] = {}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert a hex colour string to an ``(R, G, B)`` tuple.

    Args:
        hex_color: Hex string (e.g. ``'#FF00AA'`` or ``'#000'``).

    Returns:
        An ``(r, g, b)`` tuple with values 0-255.
    """
    if hex_color in _HEX_COLOR_CACHE:
        return _HEX_COLOR_CACHE[hex_color]

    h: str = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    rgb: tuple[int, ...] = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
    _HEX_COLOR_CACHE[hex_color] = rgb  # type: ignore[assignment]
    return rgb  # type: ignore[return-value]


class TextRenderer:
    """Renders text fields onto card canvases.

    Handles font selection, word wrapping, auto-resize, text
    alignment, underline, rotation, opacity, and background fill.
    """

    @staticmethod
    def render_text(
        canvas: Image.Image,
        field: TemplateField,
        user_value: str,
        px_per_mm: float,
    ) -> None:
        """Render a text field onto the card canvas.

        Args:
            canvas: The target RGBA canvas (modified in place).
            field: The field definition with all visual properties.
            user_value: The text content to render.
            px_per_mm: Pixels-per-millimetre conversion factor.
        """
        render_text(canvas, field, user_value, px_per_mm)
