"""Card template model.

Represents a reusable card layout containing a name,
optional front/back background image paths, and editor
canvas state for full layout persistence.
"""

from dataclasses import dataclass

from config.constants import CARD_HEIGHT_MM, CARD_WIDTH_MM


@dataclass
class CardTemplate:
    """A card template that defines the layout and appearance of generated cards.

    Attributes:
        id: Unique identifier (``None`` until persisted).
        template_name: Human-readable template name.
        front_image: Path to the front-side background image (optional).
        back_image: Path to the back-side background image (optional).
        canvas_width: Card width in millimetres.
        canvas_height: Card height in millimetres.
        front_bg_pos_x: Front background X offset from card left in mm.
        front_bg_pos_y: Front background Y offset from card top in mm.
        front_bg_width: Front background width in mm.
        front_bg_height: Front background height in mm.
        back_bg_pos_x: Back background X offset from card left in mm.
        back_bg_pos_y: Back background Y offset from card top in mm.
        back_bg_width: Back background width in mm.
        back_bg_height: Back background height in mm.
        grid_size: Grid snap size in scene units (pixels).
        snap_to_grid: Whether grid snapping is enabled.
        zoom_level: Canvas zoom percentage (100 = 100 %).
        created_at: ISO-8601 timestamp of creation.
        updated_at: ISO-8601 timestamp of last update.
    """

    id: int | None = None
    template_name: str = ""
    front_image: str | None = None
    back_image: str | None = None
    canvas_width: float = CARD_WIDTH_MM
    canvas_height: float = CARD_HEIGHT_MM
    front_bg_pos_x: float = 0.0
    front_bg_pos_y: float = 0.0
    front_bg_width: float = CARD_WIDTH_MM
    front_bg_height: float = CARD_HEIGHT_MM
    back_bg_pos_x: float = 0.0
    back_bg_pos_y: float = 0.0
    back_bg_width: float = CARD_WIDTH_MM
    back_bg_height: float = CARD_HEIGHT_MM
    grid_size: int = 10
    snap_to_grid: bool = True
    zoom_level: float = 100.0
    size_locked: bool = True
    created_at: str | None = None
    updated_at: str | None = None
