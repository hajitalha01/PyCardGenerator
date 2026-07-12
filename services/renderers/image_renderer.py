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
        image_path: str | None, size: tuple[int, int]
    ) -> Image.Image:
        """Load a background image or create a blank white canvas.

        Args:
            image_path: Path to the background image, or ``None``
                to create a white canvas.
            size: Desired ``(width, height)`` in pixels.

        Returns:
            An RGBA ``Image`` filled with the background content.
        """
        if image_path and Path(image_path).is_file():
            bg: Image.Image = Image.open(image_path).convert("RGBA")
            bg = bg.resize(size, Image.Resampling.LANCZOS)
            logger.debug("Loaded background image: %s", image_path)
        else:
            bg = Image.new("RGBA", size, (255, 255, 255, 255))
            logger.debug("Created blank white canvas (%d x %d)", *size)
        return bg

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
        image: Image.Image, output_path: str, quality: int = 95
    ) -> str:
        """Save an RGBA image to disk as PNG.

        Args:
            image: The image to save.
            output_path: Destination file path.
            quality: JPEG quality (used only for JPEG output).

        Returns:
            The ``output_path`` that was written to.
        """
        ext: str = Path(output_path).suffix.lower()
        if ext in (".jpg", ".jpeg"):
            image = image.convert("RGB")
            image.save(output_path, quality=quality)
        else:
            image.save(output_path)
        logger.debug("Saved image: %s", output_path)
        return output_path
