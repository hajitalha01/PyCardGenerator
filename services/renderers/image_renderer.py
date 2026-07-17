"""Image compositing utilities for card rendering.

Responsible for loading background templates, static images,
and organisation logos, then compositing them onto the card
canvas with the correct position, size, opacity, and rotation.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from utils.logger import setup_logger

logger = setup_logger(__name__)


class ImageRenderer:
    """Handles loading, scaling, and compositing of images.

    Every method operates on Pillow ``Image`` objects and returns
    the modified canvas so operations can be chained.
    """

    # ------------------------------------------------------------------
    # Background
    # ------------------------------------------------------------------

    @staticmethod
    def load_background(
        image_path: str | None,
        size: tuple[int, int],
        px_per_mm: float | None = None,
        bg_x_mm: float = 0.0,
        bg_y_mm: float = 0.0,
        bg_w_mm: float | None = None,
        bg_h_mm: float | None = None,
    ) -> Image.Image:
        """Load a background image onto a canvas.

        When *px_per_mm* and *bg_w_mm*/*bg_h_mm* are provided the
        background is placed at the correct millimetre position on a
        white canvas — matching the editor canvas behaviour exactly.
        Otherwise the image is stretched to fill the entire canvas
        (legacy full-bleed behaviour).

        Args:
            image_path: Path to the background image, or ``None``
                to create a white canvas.
            size: Desired ``(width, height)`` in pixels.
            px_per_mm: Pixels-per-millimetre factor.  When provided
                together with *bg_w_mm*/*bg_h_mm* the image is
                positioned at ``(bg_x_mm, bg_y_mm)`` in mm rather
                than filling the full canvas.
            bg_x_mm: Background X offset from card left edge (mm).
            bg_y_mm: Background Y offset from card top edge (mm).
            bg_w_mm: Background render width (mm).  ``None`` =
                full-canvas width.
            bg_h_mm: Background render height (mm).  ``None`` =
                full-canvas height.

        Returns:
            An RGBA ``Image`` filled with the background content.
        """
        canvas: Image.Image = Image.new("RGBA", size, (255, 255, 255, 255))

        if image_path and Path(image_path).is_file():
            bg: Image.Image = Image.open(image_path).convert("RGBA")

            if px_per_mm is not None and bg_w_mm is not None and bg_h_mm is not None:
                # Position-aware placement — matches editor canvas
                bg_w_px: int = round(bg_w_mm * px_per_mm)
                bg_h_px: int = round(bg_h_mm * px_per_mm)
                bg_x_px: int = round(bg_x_mm * px_per_mm)
                bg_y_px: int = round(bg_y_mm * px_per_mm)
                resized: Image.Image = bg.resize(
                    (max(bg_w_px, 1), max(bg_h_px, 1)),
                    Image.Resampling.LANCZOS,
                )
                canvas.paste(resized, (bg_x_px, bg_y_px), resized)
                logger.debug(
                    "Loaded bg '%s' at (%d, %d) size %d x %d",
                    image_path, bg_x_px, bg_y_px, bg_w_px, bg_h_px,
                )
            else:
                # Full-bleed (legacy behaviour)
                resized = bg.resize(size, Image.Resampling.LANCZOS)
                canvas.paste(resized, (0, 0), resized)
                logger.debug("Loaded full-bleed background: %s", image_path)
        else:
            logger.debug("Created blank white canvas (%d x %d)", *size)

        return canvas

    # ------------------------------------------------------------------
    # Image compositing
    # ------------------------------------------------------------------

    @staticmethod
    def paste_image(
        canvas: Image.Image,
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        height: int,
        opacity: float = 1.0,
        rotation: float = 0.0,
    ) -> None:
        """Composite *image* onto *canvas* at the given region.

        The image is resized to ``(width, height)``, rotated if
        needed, and applied with the given opacity.

        Args:
            canvas: The target canvas (modified in place).
            image: Source image to paste.
            x: Destination left coordinate (pixels).
            y: Destination top coordinate (pixels).
            width: Target width in pixels.
            height: Target height in pixels.
            opacity: Opacity factor (``0.0`` = transparent,
                ``1.0`` = opaque).
            rotation: Clockwise rotation in degrees.
        """
        if width <= 0 or height <= 0:
            return

        resized: Image.Image = image.resize(
            (width, height), Image.Resampling.LANCZOS
        )

        if rotation:
            resized = resized.rotate(
                rotation, expand=True, resample=Image.Resampling.BICUBIC
            )

        if opacity < 1.0:
            alpha: Image.Image = resized.split()[3] if resized.mode == "RGBA" else None
            resized = resized.convert("RGBA")
            if alpha is not None:
                resized.putalpha(alpha.point(lambda p: int(p * opacity)))
            else:
                resized.putalpha(
                    Image.new("L", resized.size, int(255 * opacity))
                )

        canvas.paste(resized, (x, y), resized)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @staticmethod
    def load_image(image_path: str) -> Image.Image | None:
        """Load an image file as RGBA.

        Args:
            image_path: Path to the image file.

        Returns:
            An RGBA ``Image``, or ``None`` if the file cannot be loaded.
        """
        try:
            img: Image.Image = Image.open(image_path).convert("RGBA")
            logger.debug("Loaded image: %s", image_path)
            return img
        except FileNotFoundError:
            logger.warning("Image not found: %s", image_path)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load image %s: %s", image_path, exc)
            return None

    @staticmethod
    def save_image(
        image: Image.Image, output_path: str, dpi: int = 600, quality: int = 95
    ) -> str:
        """Save an RGBA image to disk with DPI metadata.

        Args:
            image: The image to save.
            output_path: Destination file path.
            dpi: DPI metadata to embed in the image header.
            quality: JPEG quality (used only for JPEG output).

        Returns:
            The ``output_path`` that was written to.
        """
        ext: str = Path(output_path).suffix.lower()
        if ext in (".jpg", ".jpeg"):
            image = image.convert("RGB")
            image.save(output_path, quality=quality, dpi=(dpi, dpi))
        else:
            image.save(output_path, dpi=(dpi, dpi))
        logger.debug("Saved image: %s (DPI=%d)", output_path, dpi)
        return output_path
