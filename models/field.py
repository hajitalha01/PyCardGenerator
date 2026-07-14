"""Template field model.

Represents a single user-editable field positioned on a card template.
Stores all visual and behavioural properties needed for full layout
persistence and compatibility with the Dynamic Field System.
"""

from dataclasses import dataclass


@dataclass
class TemplateField:
    """A single object (field or shape) belonging to a card template.

    Attributes:
        id: Unique identifier (``None`` until persisted).
        template_id: Foreign key to the parent ``CardTemplate``.
        object_type: Visual type for the canvas item (``text_field``,
            ``photo_field``, ``rectangle``, ``line``, ...).
        field_name: Internal programmatic name (snake_case).
        display_name: Human-readable label shown in the UI.
        field_type: Data type from the Dynamic Field System
            (``text``, ``photo``, ``qr_code``, ...).
        mapped_field: Semantic field name linking to Card Generator
            form data (e.g. ``"employee_name"``).  Empty for shapes
            or static text.
        is_static: ``True`` for static labels that never change;
            ``False`` for dynamic fields linked to form data.
        static_text: The literal text content for static labels.
        x: Horizontal position on the card in millimetres.
        y: Vertical position on the card in millimetres.
        width: Field width in millimetres.
        height: Field height in millimetres.
        font_family: Font family name (e.g. ``'Arial'``).
        font_size: Font size in points.
        font_color: Hexadecimal colour string (e.g. ``'#000000'``).
        background_color: Hexadecimal colour string for the field background.
        bold: Whether the text should be rendered in bold.
        italic: Whether the text should be rendered in italics.
        underline: Whether the text should be rendered underlined.
        alignment: Text alignment (``left``, ``center``, ``right``).
        rotation: Text rotation in degrees.
        opacity: Opacity level (``0.0`` = transparent, ``1.0`` = opaque).
        visible: Whether the field is shown during rendering.
        locked: Whether the field is locked against editing.
        required: Whether a value must be supplied before generation.
        default_value: Fallback value when no user input is given.
        z_order: Stacking order (higher = on top).
        page_side: Which side of the card (``front`` or ``back``).
        created_at: ISO-8601 timestamp of creation.
    """

    id: int | None = None
    template_id: int | None = None
    object_type: str = "text_field"
    field_name: str = ""
    display_name: str = ""
    field_type: str = "text"
    mapped_field: str = ""
    is_static: bool = False
    static_text: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 20.0
    font_family: str = "Arial"
    font_size: int = 12
    font_color: str = "#000000"
    background_color: str = "#FFFFFF"
    bold: bool = False
    italic: bool = False
    underline: bool = False
    alignment: str = "left"
    rotation: int = 0
    opacity: float = 1.0
    visible: bool = True
    locked: bool = False
    required: bool = False
    default_value: str = ""
    z_order: int = 0
    page_side: str = "front"
    created_at: str | None = None
