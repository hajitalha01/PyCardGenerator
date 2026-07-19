"""Centralised path resolution for portable application execution.

Provides a single ``resource_path()`` function and a ``PathManager``
class that resolve filesystem paths correctly in both:

* **Development mode** — paths relative to the project root.
* **PyInstaller frozen mode** — resources come from ``sys._MEIPASS``
  (read-only bundle) while writable data (database, uploads, logs,
  exports) are placed next to the executable.

Every module in the application MUST use this module instead of
hardcoding paths or using ``__file__`` directly.
"""

import sys
from pathlib import Path


def _is_frozen() -> bool:
    """Return ``True`` when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def _get_resource_root() -> Path:
    """Return the root directory for read-only bundled resources.

    In development this is the project root (parent of ``utils``).
    In PyInstaller mode this is ``sys._MEIPASS`` (the unpacked bundle).
    """
    if _is_frozen():
        return Path(sys._MEIPASS)  # noqa: SLF001
    return Path(__file__).resolve().parent.parent


def _get_data_root() -> Path:
    """Return the root directory for writable application data.

    In development this is the project root.
    In PyInstaller mode this is the directory containing the executable,
    so that database, uploads, logs, and exports persist alongside the
    .exe and survive re-installation.
    """
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_path(relative: str | Path) -> Path:
    """Resolve *relative* to an absolute path inside the read-only bundle.

    Use this for assets, icons, fonts, and the database schema —
    files that ship with the application.

    Args:
        relative: A path relative to the resource root.

    Returns:
        An absolute :class:`Path` pointing to the resource.
    """
    return _get_resource_root() / relative


def data_path(relative: str | Path) -> Path:
    """Resolve *relative* to an absolute writable path outside the bundle.

    Use this for the database file, uploaded images, generated cards,
    and logs — files that are created at runtime.

    Args:
        relative: A path relative to the data root.

    Returns:
        An absolute :class:`Path` pointing to the data location.
    """
    return _get_data_root() / relative


# ---------------------------------------------------------------------------
# PathManager — convenience wrapper exposing all well-known application paths
# ---------------------------------------------------------------------------


class PathManager:
    """Singleton that provides every standard application path.

    Read-only resources (assets, schema) are resolved from the bundle.
    Writable paths (database, uploads, logs, exports) are resolved
    relative to the executable's directory so they survive updates.

    Usage::

        pm = PathManager()
        db_path = pm.database_path
        icon    = pm.icons_dir / "app.ico"
    """

    _instance: "PathManager | None" = None

    def __new__(cls) -> "PathManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialised"):
            return
        self._initialised = True
        self._res_root: Path = _get_resource_root()
        self._data_root: Path = _get_data_root()

    # -- Roots --
    @property
    def root(self) -> Path:
        """Project root (dev) or executable directory (frozen)."""
        return self._data_root

    @property
    def resource_root(self) -> Path:
        """Read-only bundle root (sys._MEIPASS) or project root in dev."""
        return self._res_root

    # -- Assets (read-only, from bundle) --
    @property
    def assets_dir(self) -> Path:
        return self._res_root / "assets"

    @property
    def templates_dir(self) -> Path:
        return self._res_root / "assets" / "templates"

    @property
    def icons_dir(self) -> Path:
        return self._res_root / "assets" / "icons"

    @property
    def fonts_dir(self) -> Path:
        return self._res_root / "assets" / "fonts"

    # -- Data directories (writable, alongside executable) --
    @property
    def uploads_dir(self) -> Path:
        return self._data_root / "uploads"

    @property
    def template_uploads_dir(self) -> Path:
        return self._data_root / "uploads" / "templates"

    @property
    def logs_dir(self) -> Path:
        return self._data_root / "logs"

    @property
    def database_dir(self) -> Path:
        return self._data_root / "database"

    # -- Database files (writable, alongside executable) --
    @property
    def database_path(self) -> Path:
        return self._data_root / "database" / "card_generator.db"

    @property
    def schema_path(self) -> Path:
        return self._res_root / "database" / "schema.sql"

    # -- Convenience --
    def ensure_dirs(self) -> None:
        """Create every required writable directory if it does not exist."""
        dirs: tuple[Path, ...] = (
            self.assets_dir,
            self.templates_dir,
            self.icons_dir,
            self.fonts_dir,
            self.uploads_dir,
            self.template_uploads_dir,
            self.logs_dir,
            self.database_dir,
        )
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
