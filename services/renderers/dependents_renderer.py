from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config.constants import EDITOR_FONT_DPI, EDITOR_PX_PER_MM
from models.field import TemplateField
from services.renderers.text_renderer import TextRenderer

_HEADERS: list[str] = ["Sr No", "Name", "Relation", "Date of Birth", "CNIC"]
_COL_PERCENTS: list[float] = [0.08, 0.28, 0.20, 0.22, 0.22]
_FONT_SIZE: int = 10
_HEADER_FONT_SIZE: int = 10
_PADDING: int = 4
_LINE_COLOR: tuple[int, int, int] = (200, 200, 200)
_HEADER_BG: tuple[int, int, int] = (230, 230, 230)
_TEXT_COLOR: tuple[int, int, int] = (0, 0, 0)

# Fields whose mapped_field indicates they belong to the dependents table
# repeating group.  The renderer groups these fields together and repeats
# them once per dependent record.
_DEP_TABLE_MAPPED_FIELDS: set[str] = {
    "sr_no",
    "dependent_name",
    "dependent_relation",
    "dependent_date_of_birth",
    "dependent_cnic",
}


# ---------------------------------------------------------------------------
# Column-data lookup helpers
# ---------------------------------------------------------------------------


def _dep_value(mapped_field: str, row_index: int, dep: dict) -> str:
    """Return the value for a column field for a given dependent record.

    ``sr_no`` is auto-generated from *row_index* (1-based).  All other
    mapped_field values strip the ``dependent_`` prefix and use the
    remainder as the key into the dependent dict.
    """
    if mapped_field == "sr_no":
        return str(row_index + 1)
    key: str = mapped_field.replace("dependent_", "", 1)
    return dep.get(key, "")


_HEADER_TEXT: dict[str, str] = {
    "sr_no": "Sr No",
    "dependent_name": "Name",
    "dependent_relation": "Relation",
    "dependent_date_of_birth": "Date of Birth",
    "dependent_cnic": "CNIC",
}


# ---------------------------------------------------------------------------
# Repeating-row template renderer
# ---------------------------------------------------------------------------


def render_repeating_table(
    canvas: Image.Image,
    fields: list[TemplateField],
    dependents: list[dict],
    px_per_mm: float,
) -> None:
    """Render one row template per dependent record.

    The caller passes **all** fields that form the row template (one per
    column).  They are sorted by X position to determine left-to-right
    column order.  The first visible row is a static header; subsequent
    rows are populated from the dependents list.

    Args:
        canvas: Target RGBA image (modified in place).
        fields: Column fields from the template's single row design.
        dependents: List of ``{name, relation, date_of_birth, cnic}`` dicts.
        px_per_mm: Pixels-per-millimetre conversion factor.
    """
    if not fields:
        return

    sorted_fields: list[TemplateField] = sorted(fields, key=lambda f: f.x)

    row_h_mm: float = max(f.height for f in sorted_fields)
    start_y_mm: float = min(f.y for f in sorted_fields)

    # -- Render header row --
    for col_field in sorted_fields:
        header_field: TemplateField = replace(
            col_field,
            y=start_y_mm,
            bold=True,
            is_static=True,
            static_text=_HEADER_TEXT.get(col_field.mapped_field, ""),
        )
        TextRenderer.render_text(canvas, header_field, header_field.static_text, px_per_mm)

    # -- Render data rows --
    for i, dep in enumerate(dependents):
        row_y_mm: float = start_y_mm + (i + 1) * row_h_mm
        for col_field in sorted_fields:
            value: str = _dep_value(col_field.mapped_field, i, dep)
            row_field: TemplateField = replace(col_field, y=row_y_mm)
            TextRenderer.render_text(canvas, row_field, value, px_per_mm)


# ---------------------------------------------------------------------------
# Monolithic table renderer (legacy / fallback)
# ---------------------------------------------------------------------------


def _get_font(size: int = _FONT_SIZE) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    dirs: tuple[str, ...] = (
        r"C:\Windows\Fonts",
        r"C:\Windows\WinSxS\amd64_microsoft-windows-f..onecore-fonts_31bf3856ad364e35_10.0.26100.1_none_eca354117831f639",
    )
    for directory in dirs:
        for name in ("arial.ttf", "Arial.ttf"):
            full = Path(directory) / name
            if full.is_file():
                try:
                    return ImageFont.truetype(str(full), size)
                except OSError:
                    pass
    return ImageFont.load_default()


def _calc_col_widths(table_w: int) -> list[int]:
    return [max(1, round(p * table_w)) for p in _COL_PERCENTS]


def render_dependents_table(
    canvas: Image.Image,
    field: TemplateField,
    dependents: list[dict],
    px_per_mm: float,
) -> None:
    """Render a self-contained table (headers + rows) inside *field*'s rect.

    This is the legacy approach where a single field represents the entire
    table.  Prefer ``render_repeating_table`` for newer templates.
    """
    if not field.visible:
        return

    x: int = round(field.x * px_per_mm)
    y: int = round(field.y * px_per_mm)
    w: int = round(field.width * px_per_mm)
    h: int = round(field.height * px_per_mm)

    if w <= 0 or h <= 0:
        return

    # Scale font sizes to match the editor's Qt rendering
    scale: float = (EDITOR_FONT_DPI / 72.0) * (px_per_mm / EDITOR_PX_PER_MM)
    scaled_font_size: int = max(1, round(_FONT_SIZE * scale))
    scaled_header_font_size: int = max(1, round(_HEADER_FONT_SIZE * scale))

    font = _get_font(scaled_font_size)
    header_font = _get_font(scaled_header_font_size)

    # Padding matching the editor's proportional scaling
    padding: int = max(2, round(_PADDING * (px_per_mm / EDITOR_PX_PER_MM)))
    col_widths: list[int] = _calc_col_widths(w)
    line_h: int = font.getbbox("Ag")[3] + padding * 2 + 2
    header_h: int = header_font.getbbox("Ag")[3] + padding * 2 + 2

    max_rows: int = max(0, (h - header_h) // line_h)
    visible_deps: list[dict] = dependents[:max_rows]

    draw: ImageDraw.ImageDraw = ImageDraw.Draw(canvas)

    cx: int = x
    cy: int = y

    for ci, header in enumerate(_HEADERS):
        cw: int = col_widths[ci]
        draw.rectangle([cx, cy, cx + cw, cy + header_h], fill=_HEADER_BG)
        draw.rectangle([cx, cy, cx + cw, cy + header_h], outline=_LINE_COLOR)
        draw.text(
            (cx + padding, cy + padding),
            header,
            font=header_font,
            fill=_TEXT_COLOR,
        )
        cx += cw

    cy += header_h

    for row_idx, dep in enumerate(visible_deps):
        cx = x
        row_data: list[str] = [
            str(row_idx + 1),
            dep.get("name", ""),
            dep.get("relation", ""),
            dep.get("date_of_birth", ""),
            dep.get("cnic", ""),
        ]

        for ci, cell_text in enumerate(row_data):
            cw = col_widths[ci]
            draw.rectangle([cx, cy, cx + cw, cy + line_h], outline=_LINE_COLOR)
            draw.text(
                (cx + padding, cy + padding),
                cell_text,
                font=font,
                fill=_TEXT_COLOR,
            )
            cx += cw

        cy += line_h


# ---------------------------------------------------------------------------
# Convenience: is_dependents_table_field
# ---------------------------------------------------------------------------


def is_dependents_table_field(field: TemplateField) -> bool:
    """Return ``True`` if *field* is part of the dependents table row template.

    Detected by checking whether ``mapped_field`` is one of the predefined
    dependents-table column names.
    """
    return field.mapped_field in _DEP_TABLE_MAPPED_FIELDS


class DependentsRenderer:
    @staticmethod
    def render(
        canvas: Image.Image,
        field: TemplateField,
        dependents: list[dict],
        px_per_mm: float,
    ) -> None:
        render_dependents_table(canvas, field, dependents, px_per_mm)
