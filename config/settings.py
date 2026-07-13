"""Application configuration settings.

Centralized path resolution and configuration values for the
entire application. All directory and file paths originate from
the project root.

The ``ensure_directories()`` function should be called once at
startup to guarantee that every required directory exists.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT_DIR: Path = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------
# Assets
# ------------------------------------------------------------------
ASSETS_DIR: Path = ROOT_DIR / "assets"
TEMPLATES_DIR: Path = ASSETS_DIR / "templates"
ICONS_DIR: Path = ASSETS_DIR / "icons"
FONTS_DIR: Path = ASSETS_DIR / "fonts"

# ------------------------------------------------------------------
# Data directories
# ------------------------------------------------------------------
UPLOADS_DIR: Path = ROOT_DIR / "uploads"
TEMPLATE_UPLOADS_DIR: Path = UPLOADS_DIR / "templates"
GENERATED_CARDS_DIR: Path = ROOT_DIR / "generated_cards"
LOGS_DIR: Path = ROOT_DIR / "logs"
DATABASE_DIR: Path = ROOT_DIR / "database"

# ------------------------------------------------------------------
# Database files
# ------------------------------------------------------------------
DATABASE_PATH: Path = DATABASE_DIR / "card_generator.db"
SCHEMA_PATH: Path = DATABASE_DIR / "schema.sql"

# ------------------------------------------------------------------
# Directories that must exist at runtime
# ------------------------------------------------------------------
_REQUIRED_DIRECTORIES: tuple[Path, ...] = (
    ASSETS_DIR,
    TEMPLATES_DIR,
    ICONS_DIR,
    FONTS_DIR,
    UPLOADS_DIR,
    TEMPLATE_UPLOADS_DIR,
    GENERATED_CARDS_DIR,
    LOGS_DIR,
    DATABASE_DIR,
)


def ensure_directories() -> None:
    """Create every required application directory if it does not exist."""
    for directory in _REQUIRED_DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)


def resolve_template_image(path: str | None) -> str | None:
    """Resolve a template image path to an absolute filesystem path.

    Supports both:
    * Legacy absolute paths (used directly).
    * Relative paths stored under :attr:`TEMPLATE_UPLOADS_DIR`
      (resolved from :attr:`ROOT_DIR`).

    Returns ``None`` when *path* is ``None`` or the file does not exist.
    """
    if not path:
        return None
    p: Path = Path(path)
    if p.is_absolute():
        absolute: Path = p
    else:
        absolute = ROOT_DIR / p
    if not absolute.is_file():
        logger.warning("Template image not found: %s (resolved: %s)", path, absolute)
        return None
    return str(absolute)


def is_managed_image(path: str | None) -> bool:
    """Check whether *path* points to a file inside
    :attr:`TEMPLATE_UPLOADS_DIR`.

    Managed files can be cleaned up safely (they are copies of the
    user's original source image).
    """
    if not path:
        return False
    try:
        resolved: Path = Path(path).resolve()
        uploads: Path = TEMPLATE_UPLOADS_DIR.resolve()
        return uploads in resolved.parents or resolved.parent == uploads
    except (OSError, ValueError):
        return False
