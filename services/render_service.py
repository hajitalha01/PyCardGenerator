"""Rendering service for card images.

The top-level orchestrator for generating high-quality card
images.  Delegates to specialised renderers for each field
type and manages the full compositing pipeline.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PIL import Image

from config.constants import (
    CARD_HEIGHT_MM,
    CARD_HEIGHT_PX,
    CARD_WIDTH_MM,
    CARD_WIDTH_PX,
    EXPORT_DPI,
)
from config.settings import GENERATED_CARDS_DIR
from fields.field_type import FieldType
from models.card import GeneratedCard
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
from utils.helpers import ensure_dir, generate_filename
from utils.logger import setup_logger

logger = setup_logger(__name__)


class RenderService:
    """Orchestrates the card rendering pipeline.

    Accepts a template, a sorted list of fields, user-supplied
    values, and an optional photo.      Produces a high-resolution
    (600 DPI by default) RGBA PNG image for each card side.

    Typical usage::

        service = RenderService()

        front_path = service.render_front(
            template=my_template,
            fields=template_fields,
            field_data={"employee_name": "John Doe", "designation": "Engineer"},
            photo_path="uploads/photo.jpg",
        )
    """

    def __init__(self, dpi: int = EXPORT_DPI) -> None:
        """Initialise the render service.

        Args:
            dpi: Output resolution in dots per inch.  All mm-based
                field coordinates are converted using this value.
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
        output_path: str | None = None,
        dependents: list[dict] | None = None,
    ) -> str:
        """Render the front side of a card and save it to disk.

        Args:
            template: The ``CardTemplate`` defining layout and
                background images.
            fields: Every field belonging to this template.
                Only those with ``page_side == 'front'`` and
                ``visible == True`` are rendered.
            field_data: Dictionary mapping ``field_name`` to the
                user-supplied string value.
            photo_path: Optional path to the user's photo file.
            output_path: Desired output path.  If ``None`` a unique
                filename is generated inside ``GENERATED_CARDS_DIR``.
            dependents: Optional list of dependent records.

        Returns:
            The filesystem path to the rendered front image.
        """
        return self._render_side(
            template=template,
            fields=fields,
            field_data=field_data,
            photo_path=photo_path,
            side="front",
            output_path=output_path,
            dependents=dependents,
        )

    def render_back(
        self,
        template: CardTemplate,
        fields: list[TemplateField],
        field_data: dict[str, str],
        photo_path: str | None = None,
        output_path: str | None = None,
        dependents: list[dict] | None = None,
    ) -> str:
        """Render the back side of a card and save it to disk.

        Args:
            template: The ``CardTemplate`` defining layout and
                background images.
            fields: Every field belonging to this template.
                Only those with ``page_side == 'back'`` and
                ``visible == True`` are rendered.
            field_data: Dictionary mapping ``field_name`` to the
                user-supplied string value.
            photo_path: Optional path to the user's photo file.
            output_path: Desired output path.  If ``None`` a unique
                filename is generated inside ``GENERATED_CARDS_DIR``.
            dependents: Optional list of dependent records.

        Returns:
            The filesystem path to the rendered back image.
        """
        return self._render_side(
            template=template,
            fields=fields,
            field_data=field_data,
            photo_path=photo_path,
            side="back",
            output_path=output_path,
            dependents=dependents,
        )

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
        output_path: str | None,
        dependents: list[dict] | None = None,
    ) -> str:
        """Run the full rendering pipeline for one card side.

        The rendering order is:

        1. Load / create the background canvas
        2. Render static images and organisation logos
        3. Render the user photo
        4. Render text fields (including date fields)
        5. Save to disk

        Fields are processed in ascending ``z_order`` so that
        higher-z items appear on top.

        Args:
            template: The card template.
            fields: All fields (filtered to *side* internally).
            field_data: User-supplied values keyed by field name.
            photo_path: Optional photo file path.
            side: ``'front'`` or ``'back'``.
            output_path: Optional explicit output path.
            dependents: Optional list of dependent records.

        Returns:
            The path to the rendered image.
        """
        px_per_mm: float = self.px_per_mm
        canvas_size: tuple[int, int] = self._canvas_size(template)
        logger.info(
            "Rendering %s side at %d DPI -> %d x %d px",
            side, self._dpi, *canvas_size,
        )

        # ---- Normalise editor coordinates to canvas coordinates ----
        # The Template Editor's card rect has a 60 px scene margin.
        # All stored positions (bg + fields) are relative to card_pos
        # (0,0 in the editor scene), but the canvas corresponds to
        # the card RECT which is 60 px (= margin_mm in mm) from that
        # origin.  We subtract this margin to get canvas-relative
        # positions.
        margin_mm_x: float = 60.0 * CARD_WIDTH_MM / CARD_WIDTH_PX    # ≈ 8.56
        margin_mm_y: float = 60.0 * CARD_HEIGHT_MM / CARD_HEIGHT_PX  # ≈ 8.55

        # -- Step 1: Background --
        bg_path: str | None = (
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
        canvas: Image.Image = self._image_renderer.load_background(
            bg_path, canvas_size,
            px_per_mm=px_per_mm,
            bg_x_mm=bg_pos_x,
            bg_y_mm=bg_pos_y,
            bg_w_mm=bg_w_mm,
            bg_h_mm=bg_h_mm,
        )

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
                    "Failed to render field '%s' (%s)",
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
                logger.exception("Failed to render dependents table")

        # -- Step 5: Save --
        if output_path is None:
            ensure_dir(GENERATED_CARDS_DIR)
            prefix: str = f"{side}_card"
            output_path = str(
                GENERATED_CARDS_DIR / generate_filename(prefix, ".png")
            )

        self._image_renderer.save_image(canvas, output_path, self._dpi)
        logger.info("Saved %s card image: %s", side, output_path)
        return output_path

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
                "Field '%s' type '%s' not yet implemented -- skipped",
                field.field_name,
                ftype,
            )

    # ------------------------------------------------------------------
    # Field metadata helpers (for GeneratedCard)
    # ------------------------------------------------------------------

    def generate_front_output_path(self) -> str:
        """Generate a default front-card output path.

        Returns:
            An absolute path under ``GENERATED_CARDS_DIR``.
        """
        ensure_dir(GENERATED_CARDS_DIR)
        return str(GENERATED_CARDS_DIR / generate_filename("front_card", ".png"))

    def generate_back_output_path(self) -> str:
        """Generate a default back-card output path.

        Returns:
            An absolute path under ``GENERATED_CARDS_DIR``.
        """
        ensure_dir(GENERATED_CARDS_DIR)
        return str(GENERATED_CARDS_DIR / generate_filename("back_card", ".png"))
