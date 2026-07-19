"""Application configuration settings.

Centralized path resolution and configuration values for the
entire application. All directory and file paths originate from
the portable ``PathManager``.

The ``ensure_directories()`` function should be called once at
startup to guarantee that every required directory exists.
"""

import logging
from pathlib import Path

from utils.resource_path import PathManager

logger = logging.getLogger(__name__)

_pm: PathManager = PathManager()

ROOT_DIR = _pm.root

# ------------------------------------------------------------------
# Assets
# ------------------------------------------------------------------
ASSETS_DIR = _pm.assets_dir
TEMPLATES_DIR = _pm.templates_dir
ICONS_DIR = _pm.icons_dir
FONTS_DIR = _pm.fonts_dir

# ------------------------------------------------------------------
# Data directories
# ------------------------------------------------------------------
UPLOADS_DIR = _pm.uploads_dir
TEMPLATE_UPLOADS_DIR = _pm.template_uploads_dir
LOGS_DIR = _pm.logs_dir
DATABASE_DIR = _pm.database_dir

# ------------------------------------------------------------------
# Database files
# ------------------------------------------------------------------
DATABASE_PATH = _pm.database_path
SCHEMA_PATH = _pm.schema_path

# ------------------------------------------------------------------
# Directories that must exist at runtime
# ------------------------------------------------------------------
_REQUIRED_DIRECTORIES: tuple = (
    ASSETS_DIR,
    TEMPLATES_DIR,
    ICONS_DIR,
    FONTS_DIR,
    UPLOADS_DIR,
    TEMPLATE_UPLOADS_DIR,
    LOGS_DIR,
    DATABASE_DIR,
)


def ensure_directories() -> None:
    """Create every required application directory if it does not exist."""
    _pm.ensure_dirs()


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
