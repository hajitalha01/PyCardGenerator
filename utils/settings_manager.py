"""Unified settings persistence using QSettings.

Provides a singleton ``SettingsManager`` that reads and writes
all user-configurable application settings. Uses Qt's ``QSettings``
(Windows registry) as the backend. Emits ``settings_changed`` so UI
components can react immediately.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QSettings, Signal

from config.constants import APP_NAME, EXPORT_DPI, PREVIEW_DPI


class SettingsManager(QObject):
    """Singleton for persisting and retrieving user settings.

    Every setting is exposed as a Python ``@property`` with a
    getter and setter.  The setter writes through to ``QSettings``
    and emits ``settings_changed`` with the setting key.
    """

    settings_changed = Signal(str)

    _instance: SettingsManager | None = None

    def __new__(cls, *args, **kwargs) -> SettingsManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialised"):
            return
        super().__init__()
        self._initialised = True
        self._settings: QSettings = QSettings(APP_NAME, APP_NAME)

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    @property
    def theme(self) -> str:
        """Current theme: ``'light'``, ``'dark'``, or ``'system'``."""
        return self._settings.value("theme", "light", type=str)

    @theme.setter
    def theme(self, value: str) -> None:
        self._settings.setValue("theme", value)
        self.settings_changed.emit("theme")

    # ------------------------------------------------------------------
    # Language
    # ------------------------------------------------------------------

    @property
    def language(self) -> str:
        """Current language code (e.g. ``'en'``). Extensible for i18n."""
        return self._settings.value("language", "en", type=str)

    @language.setter
    def language(self, value: str) -> None:
        self._settings.setValue("language", value)
        self.settings_changed.emit("language")

    # ------------------------------------------------------------------
    # Auto Save
    # ------------------------------------------------------------------

    @property
    def auto_save(self) -> bool:
        """Automatically save generated card data after export."""
        return self._settings.value("auto_save", False, type=bool)

    @auto_save.setter
    def auto_save(self, value: bool) -> None:
        self._settings.setValue("auto_save", value)
        self.settings_changed.emit("auto_save")

    # ------------------------------------------------------------------
    # Preview Quality
    # ------------------------------------------------------------------

    @property
    def preview_quality(self) -> str:
        """Preview quality: ``'normal'`` or ``'high'``."""
        return self._settings.value("preview_quality", "normal", type=str)

    @preview_quality.setter
    def preview_quality(self, value: str) -> None:
        self._settings.setValue("preview_quality", value)
        self.settings_changed.emit("preview_quality")

    @property
    def preview_dpi(self) -> int:
        """Resolved preview DPI based on current quality setting."""
        return PREVIEW_DPI if self.preview_quality == "normal" else PREVIEW_DPI * 2

    # ------------------------------------------------------------------
    # Export DPI
    # ------------------------------------------------------------------

    @property
    def export_dpi(self) -> int:
        """Export resolution in DPI (300 or 600)."""
        return self._settings.value("export_dpi", EXPORT_DPI, type=int)

    @export_dpi.setter
    def export_dpi(self, value: int) -> None:
        self._settings.setValue("export_dpi", value)
        self.settings_changed.emit("export_dpi")

    # ------------------------------------------------------------------
    # Download Folder
    # ------------------------------------------------------------------

    @property
    def download_folder(self) -> str:
        """Default directory for exported card images and PDFs."""
        default: str = str(Path.home() / "Documents" / APP_NAME)
        return self._settings.value("download_folder", default, type=str)

    @download_folder.setter
    def download_folder(self, value: str) -> None:
        self._settings.setValue("download_folder", value)
        self.settings_changed.emit("download_folder")

    # ------------------------------------------------------------------
    # Window geometry (migrated from MainWindow)
    # ------------------------------------------------------------------

    def save_window_geometry(self, geometry: bytes, state: bytes) -> None:
        """Persist window position and maximised state."""
        self._settings.setValue("main_window/geometry", geometry)
        self._settings.setValue("main_window/state", state)

    @property
    def window_geometry(self) -> bytes | None:
        return self._settings.value("main_window/geometry")

    @property
    def window_state(self) -> bytes | None:
        return self._settings.value("main_window/state")
