"""Lightweight renderer for live card previews.

Renders card images at a lower DPI (150 by default) to meet the
<100 ms refresh target.  Returns in-memory ``Image.Image``
objects rather than writing to disk.  Delegates to the same
specialised renderers (TextRenderer, PhotoRenderer, ImageRenderer)
that the full-resolution RenderService uses.
"""

from __future__ import annotations

import io
from dataclasses import replace

from PIL import Image
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QPixmap

from config.constants import (
    CARD_HEIGHT_MM,
    CARD_HEIGHT_PX,
    CARD_WIDTH_MM,
    CARD_WIDTH_PX,
    EDITOR_PX_PER_MM,
    PREVIEW_DPI,
)
from config.settings import resolve_template_image
from fields.field_type import FieldType
from models.field import TemplateField
from models.template import CardTemplate
from services.renderers.dependents_renderer import (
    DependentsRenderer,
    is_dependents_table_field,
    render_repeating_table,
)
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

    def __init__(self, dpi: int = PREVIEW_DPI) -> None:
        """Initialise the preview renderer.

        Args:
            dpi: Output resolution in dots per inch.  A quarter of the
                export DPI (600) yields 16× fewer pixels per card
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
        """Pixels-per-millimetre matching the editor canvas."""
        return EDITOR_PX_PER_MM

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

        Uses the editor's native resolution so the preview is a
        pixel-perfect match of the Template Editor canvas.

        Args:
            template: The card template defining physical dimensions.

        Returns:
            ``(width, height)`` in pixels.
        """
        return (CARD_WIDTH_PX, CARD_HEIGHT_PX)

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
        dependents: list[dict] | None = None,
    ) -> Image.Image:
        """Render the front side of a card as an in-memory image.

        Args:
            template: The ``CardTemplate`` defining layout and images.
            fields: Every field belonging to this template.
            field_data: ``{field_name: user_value}`` dictionary.
            photo_path: Optional path to the user's photo file.
            cache: Optional ``PreviewCache`` to re-use rendered backgrounds.
            dependents: Optional list of dependent records.

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
            dependents=dependents,
        )

    def render_back(
        self,
        template: CardTemplate,
        fields: list[TemplateField],
        field_data: dict[str, str],
        photo_path: str | None = None,
        cache: PreviewCache | None = None,
        dependents: list[dict] | None = None,
    ) -> Image.Image:
        """Render the back side of a card as an in-memory image.

        Args:
            template: The ``CardTemplate`` defining layout and images.
            fields: Every field belonging to this template.
            field_data: ``{field_name: user_value}`` dictionary.
            photo_path: Optional path to the user's photo file.
            cache: Optional ``PreviewCache`` to re-use rendered backgrounds.
            dependents: Optional list of dependent records.

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
            dependents=dependents,
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
        dependents: list[dict] | None = None,
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
            dependents: Optional list of dependent records.

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

        # ---- Normalise editor coordinates to canvas coordinates ----
        # The Template Editor's card rect has a 60 px scene margin.
        # All stored positions (bg + fields) are relative to card_pos
        # (0,0 in the editor scene), but the canvas corresponds to
        # the card RECT which is 60 px (= margin_mm in mm) from that
        # origin.  We subtract this margin to get canvas-relative
        # positions.  See debug_rca_report.py for the full analysis.
        margin_mm_x: float = 60.0 * CARD_WIDTH_MM / CARD_WIDTH_PX    # ≈ 8.56
        margin_mm_y: float = 60.0 * CARD_HEIGHT_MM / CARD_HEIGHT_PX  # ≈ 8.55

        # -- Step 1: Background (with caching) --
        bg_path: str | None = resolve_template_image(
            template.front_image if side == "front" else template.back_image
        )
        bg_pos_x: float = max(
            0.0,
            (template.front_bg_pos_x if side == "front" else template.back_bg_pos_x)
            - margin_mm_x,
        )
        bg_pos_y: float = max(
            0.0,
            (template.front_bg_pos_y if side == "front" else template.back_bg_pos_y)
            - margin_mm_y,
        )
        bg_w_mm: float = (
            template.front_bg_width if side == "front" else template.back_bg_width
        )
        bg_h_mm: float = (
            template.front_bg_height if side == "front" else template.back_bg_height
        )

        cached: Image.Image | None = None
        if cache is not None and template_id is not None:
            cached = cache.get_background(template_id, side)

        if cached is not None:
            canvas: Image.Image = cached.copy()
            logger.debug("Re-using cached background for %s side", side)
        else:
            canvas = self._image_renderer.load_background(
                bg_path, canvas_size,
                px_per_mm=px_per_mm,
                bg_x_mm=bg_pos_x,
                bg_y_mm=bg_pos_y,
                bg_w_mm=bg_w_mm,
                bg_h_mm=bg_h_mm,
            )
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

        # Separate repeating-group fields (dependents table) from regular fields
        regular_fields: list[TemplateField] = []
        dep_table_fields: list[TemplateField] = []
        for f in side_fields:
            if is_dependents_table_field(f):
                dep_table_fields.append(f)
            else:
                regular_fields.append(f)

        # -- Render regular fields (one copy at template position) --
        for field in regular_fields:
            try:
                norm_field: TemplateField = replace(
                    field,
                    x=max(0.0, field.x - margin_mm_x),
                    y=max(0.0, field.y - margin_mm_y),
                )
                self._render_field(
                    canvas=canvas,
                    field=norm_field,
                    field_data=field_data,
                    photo_path=photo_path,
                    px_per_mm=px_per_mm,
                    dependents=dependents,
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Preview failed to render field '%s' (%s)",
                    field.field_name,
                    field.object_type,
                )

        # -- Render repeating dependents-table rows --
        if dep_table_fields:
            norm_dep_fields: list[TemplateField] = [
                replace(
                    f,
                    x=max(0.0, f.x - margin_mm_x),
                    y=max(0.0, f.y - margin_mm_y),
                )
                for f in dep_table_fields
            ]
            try:
                render_repeating_table(
                    canvas, norm_dep_fields, dependents, px_per_mm,
                )
            except Exception:  # noqa: BLE001
                logger.exception("Preview failed to render dependents table")

        return canvas

    def _render_field(
        self,
        canvas: Image.Image,
        field: TemplateField,
        field_data: dict[str, str],
        photo_path: str | None,
        px_per_mm: float,
        dependents: list[dict] | None = None,
    ) -> None:
        """Dispatch a single field to the appropriate renderer.

        Args:
            canvas: The target canvas (modified in place).
            field: The field to render.
            field_data: User-supplied values.
            photo_path: Optional user photo path.
            px_per_mm: Pixel-per-mm conversion factor.
            dependents: Optional list of dependent records.
        """
        ftype: str = field.field_type

        # --- Static text: render the literal static_text directly ---
        if field.is_static:
            TextRenderer.render_text(canvas, field, field.static_text, px_per_mm)
            return

        # --- Dynamic text / date fields ---
        # Use mapped_field for data lookup, fall back to field_name.
        if ftype in (FieldType.TEXT, FieldType.DATE):
            lookup_key: str = field.mapped_field or field.field_name

            # Dependents table: render as a proper table grid
            if lookup_key == "dependence":
                DependentsRenderer.render(
                    canvas, field, dependents or [], px_per_mm,
                )
                return

            user_value: str = field_data.get(lookup_key, "")
            TextRenderer.render_text(canvas, field, user_value, px_per_mm)

        # Photo field
        elif ftype == FieldType.PHOTO:
            self._photo_renderer.render_photo(
                canvas, photo_path, field, px_per_mm
            )

        # Static image / logo
        elif ftype in (FieldType.STATIC_IMAGE, FieldType.ORGANIZATION_LOGO):
            lookup_key = field.mapped_field or field.field_name
            image_path: str | None = field_data.get(lookup_key)
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
