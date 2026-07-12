"""Lightweight renderer for live card previews.

Renders card images at a lower DPI (150 by default) to meet the
<100 ms refresh target.  Returns in-memory ``Image.Image``
objects rather than writing to disk.  Delegates to the same
specialised renderers (TextRenderer, PhotoRenderer, ImageRenderer)
that the full-resolution RenderService uses.
"""

from __future__ import annotations

import io

from PIL import Image
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QPixmap

from fields.field_type import FieldType
from models.field import TemplateField
from models.template import CardTemplate
from services.renderers.image_renderer import ImageRenderer
from services.renderers.photo_renderer import PhotoRenderer
from services.renderers.text_renderer import TextRenderer
from services.preview.preview_cache import PreviewCache
from utils.logger import setup_logger

logger = setup_logger(__name__)


class PreviewRenderer:
    """Renders card sides to in-memory PIL Images at preview DPI.

    Typical usage::

        renderer = PreviewRenderer(dpi=150)

        img = renderer.render_front(template, fields, field_data, photo_path)
        pixmap = renderer.image_to_qpixmap(img)
        canvas.set_pixmap(pixmap)
    """

    def __init__(self, dpi: int = 150) -> None:
        """Initialise the preview renderer.

        Args:
            dpi: Output resolution in dots per inch.  Half of the
                production DPI (300) yields 4× fewer pixels per card
                side, keeping preview updates fast.
        """
        self._dpi: int = dpi
        self._image_renderer: ImageRenderer = ImageRenderer()
        self._photo_renderer: PhotoRenderer = PhotoRenderer()

    # ------------------------------------------------------------------
    # Unit conversion
    # ------------------------------------------------------------------

    @property
    def px_per_mm(self) -> float:
        """Pixels-per-millimetre for the configured DPI."""
        return self._dpi / 25.4

    def _mm_to_px(self, mm: float) -> int:
        """Convert a millimetre value to pixels at the current DPI.

        Args:
            mm: Length in millimetres.

        Returns:
            Equivalent length in pixels (rounded).
        """
        return round(mm * self.px_per_mm)

    def _canvas_size(
        self, template: CardTemplate
    ) -> tuple[int, int]:
        """Compute the output canvas size in pixels.

        Args:
            template: The card template defining physical dimensions.

        Returns:
            ``(width, height)`` in pixels.
        """
        return (
            self._mm_to_px(template.canvas_width),
            self._mm_to_px(template.canvas_height),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render_front(
        self,
        template: CardTemplate,
        fields: list[TemplateField],
        field_data: dict[str, str],
        photo_path: str | None = None,
        cache: PreviewCache | None = None,
    ) -> Image.Image:
        """Render the front side of a card as an in-memory image.

        Args:
            template: The ``CardTemplate`` defining layout and images.
            fields: Every field belonging to this template.
            field_data: ``{field_name: user_value}`` dictionary.
            photo_path: Optional path to the user's photo file.
            cache: Optional ``PreviewCache`` to re-use rendered backgrounds.

        Returns:
            An RGBA ``Image.Image`` of the rendered front side.
        """
        return self._render_side(
            template=template,
            fields=fields,
            field_data=field_data,
            photo_path=photo_path,
            side="front",
            cache=cache,
        )

    def render_back(
        self,
        template: CardTemplate,
        fields: list[TemplateField],
        field_data: dict[str, str],
        photo_path: str | None = None,
        cache: PreviewCache | None = None,
    ) -> Image.Image:
        """Render the back side of a card as an in-memory image.

        Args:
            template: The ``CardTemplate`` defining layout and images.
            fields: Every field belonging to this template.
            field_data: ``{field_name: user_value}`` dictionary.
            photo_path: Optional path to the user's photo file.
            cache: Optional ``PreviewCache`` to re-use rendered backgrounds.

        Returns:
            An RGBA ``Image.Image`` of the rendered back side.
        """
        return self._render_side(
            template=template,
            fields=fields,
            field_data=field_data,
            photo_path=photo_path,
            side="back",
            cache=cache,
        )

    # ------------------------------------------------------------------
    # QPixmap conversion
    # ------------------------------------------------------------------

    @staticmethod
    def image_to_qpixmap(image: Image.Image) -> QPixmap:
        """Convert a PIL ``Image`` to a ``QPixmap``.

        The conversion uses a PNG memory buffer to avoid any
        dependency on ``PIL.ImageQt``, which can be fragile
        across Qt binding versions.

        Args:
            image: The PIL ``Image`` to convert.

        Returns:
            A ``QPixmap`` suitable for display in ``PreviewCanvas``.
        """
        buffer: io.BytesIO = io.BytesIO()
        image.save(buffer, format="PNG")
        data: QByteArray = QByteArray(buffer.getvalue())
        pixmap: QPixmap = QPixmap()
        pixmap.loadFromData(data, "PNG")
        return pixmap

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------

    def _render_side(
        self,
        template: CardTemplate,
        fields: list[TemplateField],
        field_data: dict[str, str],
        photo_path: str | None,
        side: str,
        cache: PreviewCache | None,
    ) -> Image.Image:
        """Run the rendering pipeline for one card side.

        The rendering order matches ``RenderService._render_side``:
        1. Load / create the background canvas
        2. Render static images and organisation logos
        3. Render the user photo
        4. Render text fields (including date fields)

        Fields are processed in ascending ``z_order``.

        Args:
            template: The card template.
            fields: All fields.
            field_data: User-supplied values keyed by field name.
            photo_path: Optional photo file path.
            side: ``'front'`` or ``'back'``.
            cache: Optional cache for background images.

        Returns:
            The rendered RGBA image.
        """
        px_per_mm: float = self.px_per_mm
        canvas_size: tuple[int, int] = self._canvas_size(template)
        template_id: int | None = template.id
        logger.debug(
            "Preview rendering %s side at %d DPI -> %d x %d px",
            side, self._dpi, *canvas_size,
        )

        # -- Step 1: Background (with caching) --
        bg_path: str | None = (
            template.front_image if side == "front" else template.back_image
        )

        cached: Image.Image | None = None
        if cache is not None and template_id is not None:
            cached = cache.get_background(template_id, side)

        if cached is not None:
            canvas: Image.Image = cached.copy()
            logger.debug("Re-using cached background for %s side", side)
        else:
            canvas = self._image_renderer.load_background(bg_path, canvas_size)
            if cache is not None and template_id is not None:
                cache.set_background(template_id, side, canvas)
                logger.debug("Cached background for %s side", side)

        # -- Filter and sort fields for this side --
        side_fields: list[TemplateField] = [
            f
            for f in fields
            if f.visible and f.page_side == side
        ]
        side_fields.sort(key=lambda f: f.z_order)

        # -- Steps 2-4: Render each field in order --
        for field in side_fields:
            try:
                self._render_field(
                    canvas=canvas,
                    field=field,
                    field_data=field_data,
                    photo_path=photo_path,
                    px_per_mm=px_per_mm,
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Preview failed to render field '%s' (%s)",
                    field.field_name,
                    field.object_type,
                )

        return canvas

    def _render_field(
        self,
        canvas: Image.Image,
        field: TemplateField,
        field_data: dict[str, str],
        photo_path: str | None,
        px_per_mm: float,
    ) -> None:
        """Dispatch a single field to the appropriate renderer.

        Args:
            canvas: The target canvas (modified in place).
            field: The field to render.
            field_data: User-supplied values.
            photo_path: Optional user photo path.
            px_per_mm: Pixel-per-mm conversion factor.
        """
        ftype: str = field.field_type

        # Text / date fields
        if ftype in (FieldType.TEXT, FieldType.DATE):
            user_value: str = field_data.get(field.field_name, "")
            TextRenderer.render_text(canvas, field, user_value, px_per_mm)

        # Photo field
        elif ftype == FieldType.PHOTO:
            self._photo_renderer.render_photo(
                canvas, photo_path, field, px_per_mm
            )

        # Static image / logo
        elif ftype in (FieldType.STATIC_IMAGE, FieldType.ORGANIZATION_LOGO):
            image_path: str | None = field_data.get(field.field_name)
            if image_path:
                img: Image.Image | None = self._image_renderer.load_image(
                    image_path
                )
                if img is not None:
                    self._image_renderer.paste_image(
                        canvas=canvas,
                        image=img,
                        x=self._mm_to_px(field.x),
                        y=self._mm_to_px(field.y),
                        width=self._mm_to_px(field.width),
                        height=self._mm_to_px(field.height),
                        opacity=field.opacity,
                        rotation=float(field.rotation),
                    )

        # Placeholder for future types
        elif ftype in (FieldType.QR_CODE, FieldType.BARCODE, FieldType.SIGNATURE):
            logger.debug(
                "Preview field '%s' type '%s' not yet implemented -- skipped",
                field.field_name,
                ftype,
            )
