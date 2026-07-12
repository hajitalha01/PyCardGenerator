"""Field definition model.

A pure domain dataclass that describes a single field
on any card template.  This class is completely independent
of rendering, persistence, and UI concerns.
"""

import uuid
from dataclasses import dataclass, field

from fields.field_type import FieldType


def _generate_id() -> str:
    """Return a 32-character unique hex string."""
    return uuid.uuid4().hex


@dataclass
class FieldDefinition:
    """Complete definition of a single field on a card template.

    Every visual and behavioural property is captured here so
    that rendering, export, and editing modules can operate
    without additional configuration.

    Attributes:
        id: Globally unique identifier for this field instance.
        field_name: Internal programmatic name (snake_case).
        display_name: Human-readable label shown in the UI.
        field_type: The category of data this field holds.
        x: Horizontal position on the card in millimetres.
        y: Vertical position on the card in millimetres.
        width: Field width in millimetres.
        height: Field height in millimetres.
        font_family: Typeface name (e.g. ``'Arial'``).
        font_size: Typeface size in points.
        font_color: Hex colour string for text (e.g. ``'#000000'``).
        background_color: Hex colour string for the field background.
        bold: Render text with bold weight.
        italic: Render text with italic slant.
        underline: Render text underlined.
        alignment: Horizontal text alignment (``'left'``, ``'center'``,
            ``'right'``, or ``'justify'``).
        rotation: Clockwise rotation of the field in degrees.
        opacity: Opacity level from ``0.0`` (fully transparent) to
            ``1.0`` (fully opaque).
        visible: Whether the field is shown during rendering.
        locked: Whether the field is locked against editing in the UI.
        required: Whether a value must be supplied before generation.
        default_value: Fallback value used when no user input is given.
    """

    id: str = field(default_factory=_generate_id)
    field_name: str = ""
    display_name: str = ""
    field_type: FieldType = FieldType.TEXT
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 20.0
    font_family: str = "Arial"
    font_size: float = 12.0
    font_color: str = "#000000"
    background_color: str = "#FFFFFF"
    bold: bool = False
    italic: bool = False
    underline: bool = False
    alignment: str = "left"
    rotation: float = 0.0
    opacity: float = 1.0
    visible: bool = True
    locked: bool = False
    required: bool = False
    default_value: str = ""
