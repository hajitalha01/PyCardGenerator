"""Application configuration settings.

Centralized path resolution and configuration values for the
entire application. All directory and file paths originate from
the project root.

The ``ensure_directories()`` function should be called once at
startup to guarantee that every required directory exists.
"""

from pathlib import Path

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
    GENERATED_CARDS_DIR,
    LOGS_DIR,
    DATABASE_DIR,
)


def ensure_directories() -> None:
    """Create every required application directory if it does not exist."""
    for directory in _REQUIRED_DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)
