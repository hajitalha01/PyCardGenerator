"""Application-wide constants.

Defines immutable values including application metadata,
window geometry, card dimensions, file-type whitelists,
logging parameters, and Qt alignment helpers.
"""

from PySide6.QtCore import Qt

# ------------------------------------------------------------------
# Application metadata
# ------------------------------------------------------------------
APP_NAME: str = "Card Generator"
APP_VERSION: str = "1.0.0"
COMPANY_NAME: str = "CardGenerator"

# ------------------------------------------------------------------
# Window geometry
# ------------------------------------------------------------------
WINDOW_MIN_WIDTH: int = 1200
WINDOW_MIN_HEIGHT: int = 800
SIDEBAR_WIDTH: int = 250
SIDEBAR_COLLAPSED_WIDTH: int = 64

# ------------------------------------------------------------------
# Card dimensions
# ------------------------------------------------------------------
CARD_WIDTH_MM: float = 85.6
CARD_HEIGHT_MM: float = 54.0
CARD_WIDTH_PX: int = 600
CARD_HEIGHT_PX: int = 379

# ------------------------------------------------------------------
# Rendering resolution
# ------------------------------------------------------------------
CARD_DPI: int = 300        # Base DPI for editor scene calculations
PREVIEW_DPI: int = 300     # Live preview (balanced quality & speed)
EXPORT_DPI: int = 600      # Export / print (professional quality)

# ------------------------------------------------------------------
# Supported file types
# ------------------------------------------------------------------
SUPPORTED_IMAGE_FORMATS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".bmp")
SUPPORTED_PDF_TYPES: tuple[str, ...] = (".pdf",)

# ------------------------------------------------------------------
# Default styling
# ------------------------------------------------------------------
DEFAULT_FONT_FAMILY: str = "Arial"
DEFAULT_FONT_SIZE: int = 12

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
LOG_FILENAME: str = "application.log"
LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT: int = 5

# ------------------------------------------------------------------
# Qt alignment helpers
# ------------------------------------------------------------------
ALIGN_LEFT = Qt.AlignmentFlag.AlignLeft
ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
ALIGN_RIGHT = Qt.AlignmentFlag.AlignRight
ALIGN_TOP = Qt.AlignmentFlag.AlignTop
ALIGN_BOTTOM = Qt.AlignmentFlag.AlignBottom
