"""Photo rendering for card fields.

Handles user-supplied photo images: loading, scaling to fit
or fill the field rectangle, aspect-ratio preservation, rounded
corners, and optional borders.  The rendered photo is composited
onto the card canvas at the correct position and opacity.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from models.field import TemplateField
from utils.logger import setup_logger

logger = setup_logger(__name__)


class PhotoRenderer:
    """Renders user photos onto card canvases with optional effects.

    Typical usage::

        renderer = PhotoRenderer()
        renderer.render_photo(canvas, photo_path, field, px_per_mm)
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def render_photo(
        canvas: Image.Image,
        photo_path: str | None,
        field: TemplateField,
        px_per_mm: float,
    ) -> None:
        """Render a user photo onto the card canvas.

        Args:
            canvas: The target RGBA canvas (modified in place).
            photo_path: Path to the user's photo file.
            field: The field definition with position, size, and
                rendering properties.
            px_per_mm: Pixels-per-millimetre conversion factor.
        """
        if not field.visible:
            return
        if not photo_path or not Path(photo_path).is_file():
            logger.debug("No photo available for field '%s'", field.field_name)
            return

        # Convert mm to px
        x: int = round(field.x * px_per_mm)
        y: int = round(field.y * px_per_mm)
        w: int = round(field.width * px_per_mm)
        h: int = round(field.height * px_per_mm)

        if w <= 0 or h <= 0:
            return

        # Load the photo
        try:
            photo: Image.Image = Image.open(photo_path).convert("RGBA")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load photo %s: %s", photo_path, exc)
            return

        # Scale to fill the field (maintaining aspect ratio, cropping)
        processed: Image.Image = PhotoRenderer._fill(photo, w, h)

        # Apply rounded corners
        radius: int = max(1, round(8 * px_per_mm / 11.811))  # ~8 mm radius
        processed = PhotoRenderer._rounded_corners(processed, radius)

        # Apply border
        border_w: int = max(0, round(1 * px_per_mm / 11.811))  # ~1 mm
        if border_w > 0:
            processed = PhotoRenderer._add_border(
                processed, border_w, (255, 255, 255)
            )

        # Compose onto canvas
        if field.opacity < 1.0:
            alpha: Image.Image = processed.split()[3]
            alpha = alpha.point(lambda p: int(p * field.opacity))
            processed.putalpha(alpha)

        canvas.paste(processed, (x, y), processed)
        logger.debug(
            "Rendered photo '%s' at (%d, %d) %dx%d",
            field.field_name, x, y, w, h,
        )

    # ------------------------------------------------------------------
    # Scaling modes
    # ------------------------------------------------------------------

    @staticmethod
    def _fit(image: Image.Image, target_w: int, target_h: int) -> Image.Image:
        """Scale *image* to fit inside *target_w* × *target_h*.

        The entire image is visible; empty space is filled with
        transparency.

        Args:
            image: Source RGBA image.
            target_w: Maximum width in pixels.
            target_h: Maximum height in pixels.

        Returns:
            A centred RGBA image of exactly ``(target_w, target_h)``.
        """
        img_w: int
        img_h: int
        img_w, img_h = image.size

        scale: float = min(target_w / img_w, target_h / img_h)
        new_w: int = max(1, round(img_w * scale))
        new_h: int = max(1, round(img_h * scale))

        scaled: Image.Image = image.resize(
            (new_w, new_h), Image.Resampling.LANCZOS
        )

        canvas: Image.Image = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        ox: int = (target_w - new_w) // 2
        oy: int = (target_h - new_h) // 2
        canvas.paste(scaled, (ox, oy), scaled)
        return canvas

    @staticmethod
    def _fill(image: Image.Image, target_w: int, target_h: int) -> Image.Image:
        """Scale and crop *image* to exactly fill *target_w* × *target_h*.

        The image aspect ratio is preserved; the excess is cropped
        evenly from both sides.

        Args:
            image: Source RGBA image.
            target_w: Desired width in pixels.
            target_h: Desired height in pixels.

        Returns:
            An RGBA image of exactly ``(target_w, target_h)``.
        """
        img_w: int
        img_h: int
        img_w, img_h = image.size

        scale: float = max(target_w / img_w, target_h / img_h)
        new_w: int = max(1, round(img_w * scale))
        new_h: int = max(1, round(img_h * scale))

        scaled: Image.Image = image.resize(
            (new_w, new_h), Image.Resampling.LANCZOS
        )

        left: int = (new_w - target_w) // 2
        top: int = (new_h - target_h) // 2
        cropped: Image.Image = scaled.crop(
            (left, top, left + target_w, top + target_h)
        )
        return cropped

    # ------------------------------------------------------------------
    # Effects
    # ------------------------------------------------------------------

    @staticmethod
    def _rounded_corners(
        image: Image.Image, radius: int
    ) -> Image.Image:
        """Apply rounded corners to an RGBA image.

        Args:
            image: Source RGBA image.
            radius: Corner radius in pixels.

        Returns:
            A new RGBA image with transparent corners.
        """
        if radius <= 0:
            return image

        w: int
        h: int
        w, h = image.size
        mask: Image.Image = Image.new("L", (w, h), 0)
        draw: ImageDraw.ImageDraw = ImageDraw.Draw(mask)
        draw.rounded_rectangle(
            [(0, 0), (w - 1, h - 1)],
            radius=radius,
            fill=255,
        )

        result: Image.Image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        result.paste(image, (0, 0), mask)
        return result

    @staticmethod
    def _add_border(
        image: Image.Image,
        border_width: int,
        border_color: tuple[int, int, int],
    ) -> Image.Image:
        """Add a solid border around an RGBA image.

        The border is drawn inside the image bounds (does not
        increase the image size).

        Args:
            image: Source RGBA image.
            border_width: Border thickness in pixels.
            border_color: ``(R, G, B)`` colour tuple.

        Returns:
            A new RGBA image with the border applied.
        """
        if border_width <= 0:
            return image

        w: int
        h: int
        w, h = image.size
        result: Image.Image = image.copy()

        draw: ImageDraw.ImageDraw = ImageDraw.Draw(result)
        draw.rectangle(
            [0, 0, w - 1, h - 1],
            outline=border_color,
            width=border_width,
        )
        return result
