"""Application settings panel.

Divided into modern card-based sections — Appearance, Language,
Card Generation, Downloads, About, and Future Settings — each
with real-time persistence via ``SettingsManager``.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from config.constants import APP_NAME, APP_VERSION
from utils.settings_manager import SettingsManager
from utils.theme_manager import ThemeManager


class SettingsView(QWidget):
    """Application settings panel with card-based sections."""

    def __init__(self) -> None:
        """Initialise the settings view."""
        super().__init__()
        self.setObjectName("settingsView")

        self._settings: SettingsManager = SettingsManager()
        self._theme_mgr: ThemeManager = ThemeManager()

        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Build the complete settings page."""
        root: QVBoxLayout = QVBoxLayout(self)
        root.setContentsMargins(24, 0, 24, 0)
        root.setSpacing(0)

        # --- Header ---
        header_widget: QWidget = QWidget()
        header_layout: QVBoxLayout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 20, 0, 0)
        header_layout.setSpacing(4)

        title: QLabel = QLabel("Settings")
        title.setObjectName("viewTitle")
        header_layout.addWidget(title)

        description: QLabel = QLabel(
            "Configure application preferences, theme, and default values."
        )
        description.setObjectName("viewDescription")
        description.setWordWrap(True)
        header_layout.addWidget(description)
        root.addWidget(header_widget)

        # --- Scrollable content ---
        scroll: QScrollArea = QScrollArea()
        scroll.setObjectName("formScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content: QWidget = QWidget()
        content_layout: QVBoxLayout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 16, 0, 24)
        content_layout.setSpacing(16)

        content_layout.addWidget(self._build_appearance_card())
        content_layout.addWidget(self._build_language_card())
        content_layout.addWidget(self._build_card_generation_card())
        content_layout.addWidget(self._build_downloads_card())
        content_layout.addWidget(self._build_about_card())
        content_layout.addWidget(self._build_future_card())
        content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

    # ------------------------------------------------------------------
    # Card helper
    # ------------------------------------------------------------------

    @staticmethod
    def _build_card(title: str, description: str) -> tuple[QWidget, QVBoxLayout]:
        """Create a styled settings card.

        Args:
            title: Section heading.
            description: Short description below the heading.

        Returns:
            ``(card_widget, body_layout)`` — the body layout is returned
            so the caller can populate it with controls.
        """
        card: QWidget = QWidget()
        card.setObjectName("viewContent")

        layout: QVBoxLayout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(4)

        heading: QLabel = QLabel(title)
        heading.setObjectName("formSectionTitle")
        layout.addWidget(heading)

        desc: QLabel = QLabel(description)
        desc.setObjectName("infoLabel")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        body: QVBoxLayout = QVBoxLayout()
        body.setContentsMargins(0, 12, 0, 0)
        body.setSpacing(12)
        layout.addLayout(body)

        return card, body

    # ------------------------------------------------------------------
    # 1. Appearance
    # ------------------------------------------------------------------

    def _build_appearance_card(self) -> QWidget:
        """Appearance section — theme radio buttons."""
        card, body = self._build_card(
            "\U0001f3a8 Appearance",
            "Choose your preferred colour theme. Changes apply instantly.",
        )

        theme_row: QWidget = QWidget()
        theme_layout: QHBoxLayout = QHBoxLayout(theme_row)
        theme_layout.setContentsMargins(0, 0, 0, 0)
        theme_layout.setSpacing(20)

        self._theme_group: QButtonGroup = QButtonGroup(self)
        for val, label in [("light", "\u2600 Light Mode"), ("dark", "\U0001f319 Dark Mode"), ("system", "\U0001f310 Follow System")]:
            rb: QRadioButton = QRadioButton(label)
            rb.setObjectName("settingsRadio")
            rb.setCursor(Qt.CursorShape.PointingHandCursor)
            self._theme_group.addButton(rb)
            theme_layout.addWidget(rb)
            setattr(self, f"_theme_{val}", rb)

        current: str = self._settings.theme
        getattr(self, f"_theme_{current}").setChecked(True)
        self._theme_group.idClicked.connect(self._on_theme_changed)

        theme_layout.addStretch()
        body.addWidget(theme_row)

        return card

    def _on_theme_changed(self) -> None:
        """Apply the newly selected theme and persist."""
        for val in ("light", "dark", "system"):
            rb: QRadioButton = getattr(self, f"_theme_{val}")
            if rb.isChecked():
                self._settings.theme = val
                self._theme_mgr.apply(val)
                break

    # ------------------------------------------------------------------
    # 2. Language
    # ------------------------------------------------------------------

    def _build_language_card(self) -> QWidget:
        """Language section — dropdown (extensible for i18n)."""
        card, body = self._build_card(
            "\U0001f310 Language",
            "Select the application language. Architecture is ready for future translations.",
        )

        row: QWidget = QWidget()
        row_layout: QHBoxLayout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(12)

        self._language_combo: QComboBox = QComboBox()
        self._language_combo.setObjectName("fieldInput")
        self._language_combo.setMinimumWidth(220)
        self._language_combo.addItem("English", "en")
        self._language_combo.addItem("Urdu", "ur")
        self._language_combo.addItem("Arabic", "ar")

        idx: int = self._language_combo.findData(self._settings.language)
        if idx >= 0:
            self._language_combo.setCurrentIndex(idx)
        self._language_combo.currentIndexChanged.connect(self._on_language_changed)

        row_layout.addWidget(self._language_combo)
        row_layout.addStretch()
        body.addWidget(row)

        return card

    def _on_language_changed(self) -> None:
        """Persist the selected language code."""
        code: str = self._language_combo.currentData() or "en"
        self._settings.language = code

    # ------------------------------------------------------------------
    # 3. Card Generation
    # ------------------------------------------------------------------

    def _build_card_generation_card(self) -> QWidget:
        """Card Generation section — auto-save toggle, preview & export quality."""
        card, body = self._build_card(
            "\U0001f4be Card Generation",
            "Control auto-save behaviour and rendering quality.",
        )

        # -- Auto Save --
        auto_row: QWidget = QWidget()
        auto_layout: QHBoxLayout = QHBoxLayout(auto_row)
        auto_layout.setContentsMargins(0, 0, 0, 0)
        auto_layout.setSpacing(12)

        self._auto_save_check: QCheckBox = QCheckBox("Auto Save")
        self._auto_save_check.setObjectName("settingsToggle")
        self._auto_save_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self._auto_save_check.setChecked(self._settings.auto_save)
        self._auto_save_check.toggled.connect(self._on_auto_save_toggled)
        auto_layout.addWidget(self._auto_save_check)

        auto_desc: QLabel = QLabel(
            "Automatically save generated card information after successful generation."
        )
        auto_desc.setObjectName("infoLabel")
        auto_desc.setWordWrap(True)
        auto_layout.addWidget(auto_desc, stretch=1)
        body.addWidget(auto_row)

        # -- Preview Quality --
        preview_row: QWidget = QWidget()
        preview_layout: QHBoxLayout = QHBoxLayout(preview_row)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(12)

        preview_label: QLabel = QLabel("Preview Quality:")
        preview_label.setObjectName("infoLabel")
        preview_layout.addWidget(preview_label)

        self._preview_quality_combo: QComboBox = QComboBox()
        self._preview_quality_combo.setObjectName("fieldInput")
        self._preview_quality_combo.setMinimumWidth(200)
        self._preview_quality_combo.addItem("Normal \u2014 Fast preview rendering", "normal")
        self._preview_quality_combo.addItem(
            "High \u2014 Higher quality with slightly more GPU/CPU usage", "high"
        )
        idx_pq: int = self._preview_quality_combo.findData(self._settings.preview_quality)
        if idx_pq >= 0:
            self._preview_quality_combo.setCurrentIndex(idx_pq)
        self._preview_quality_combo.currentIndexChanged.connect(self._on_preview_quality_changed)
        preview_layout.addWidget(self._preview_quality_combo)
        preview_layout.addStretch()
        body.addWidget(preview_row)

        # -- Export Quality --
        export_row: QWidget = QWidget()
        export_layout: QHBoxLayout = QHBoxLayout(export_row)
        export_layout.setContentsMargins(0, 0, 0, 0)
        export_layout.setSpacing(12)

        export_label: QLabel = QLabel("Export Quality:")
        export_label.setObjectName("infoLabel")
        export_layout.addWidget(export_label)

        self._export_dpi_combo: QComboBox = QComboBox()
        self._export_dpi_combo.setObjectName("fieldInput")
        self._export_dpi_combo.setMinimumWidth(200)
        self._export_dpi_combo.addItem("300 DPI \u2014 Recommended", 300)
        self._export_dpi_combo.addItem("600 DPI \u2014 Ultra HD printing quality", 600)
        idx_ed: int = self._export_dpi_combo.findData(self._settings.export_dpi)
        if idx_ed >= 0:
            self._export_dpi_combo.setCurrentIndex(idx_ed)
        self._export_dpi_combo.currentIndexChanged.connect(self._on_export_dpi_changed)
        export_layout.addWidget(self._export_dpi_combo)
        export_layout.addStretch()
        body.addWidget(export_row)

        return card

    def _on_auto_save_toggled(self, checked: bool) -> None:
        """Persist auto-save preference."""
        self._settings.auto_save = checked

    def _on_preview_quality_changed(self) -> None:
        """Persist preview quality setting."""
        val: str = self._preview_quality_combo.currentData() or "normal"
        self._settings.preview_quality = val

    def _on_export_dpi_changed(self) -> None:
        """Persist export DPI setting."""
        dpi: int = self._export_dpi_combo.currentData() or 600
        self._settings.export_dpi = dpi

    # ------------------------------------------------------------------
    # 4. Downloads
    # ------------------------------------------------------------------

    def _build_downloads_card(self) -> QWidget:
        """Downloads section — current path display + Browse button."""
        card, body = self._build_card(
            "\U0001f4c2 Downloads",
            "Choose the default folder for exported card images and PDFs.",
        )

        path_row: QWidget = QWidget()
        path_layout: QHBoxLayout = QHBoxLayout(path_row)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(12)

        self._download_path_label: QLabel = QLabel(self._settings.download_folder)
        self._download_path_label.setObjectName("fieldInput")
        self._download_path_label.setMinimumWidth(300)
        self._download_path_label.setMaximumHeight(36)
        self._download_path_label.setStyleSheet("padding: 7px 12px;")
        path_layout.addWidget(self._download_path_label)

        self._browse_btn: QPushButton = QPushButton("Browse")
        self._browse_btn.setObjectName("actionButton")
        self._browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_btn.clicked.connect(self._on_browse_download_folder)
        path_layout.addWidget(self._browse_btn)

        path_layout.addStretch()
        body.addWidget(path_row)

        return card

    def _on_browse_download_folder(self) -> None:
        """Open a folder picker and persist the chosen path."""
        folder: str = QFileDialog.getExistingDirectory(
            self,
            "Select Default Download Folder",
            self._settings.download_folder,
        )
        if folder:
            self._settings.download_folder = folder
            self._download_path_label.setText(folder)

    # ------------------------------------------------------------------
    # 5. About
    # ------------------------------------------------------------------

    def _build_about_card(self) -> QWidget:
        """About section — application information."""
        card, body = self._build_card(
            "\u2139 About",
            "Application version and credits.",
        )

        rows: list[tuple[str, str]] = [
            ("Application", APP_NAME),
            ("Version", f"v{APP_VERSION}"),
            ("Product By", "Tatheer Fatima"),
            ("License", "MIT"),
        ]

        for label, value in rows:
            row: QWidget = QWidget()
            row_layout: QHBoxLayout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)

            lbl: QLabel = QLabel(label + ":")
            lbl.setObjectName("infoLabel")
            lbl.setMinimumWidth(100)
            row_layout.addWidget(lbl)

            val: QLabel = QLabel(value)
            val.setObjectName("templateInfoValue")
            row_layout.addWidget(val)

            row_layout.addStretch()
            body.addWidget(row)

        return card

    # ------------------------------------------------------------------
    # 6. Future Settings (disabled placeholders)
    # ------------------------------------------------------------------

    def _build_future_card(self) -> QWidget:
        """Future Settings section — disabled placeholders."""
        card, body = self._build_card(
            "\U0001f52e Future Settings",
            "Upcoming features. Stay tuned for updates.",
        )

        placeholders: list[str] = [
            "Notifications",
            "Backup",
            "Cloud Sync",
            "Automatic Updates",
            "Recent Files",
        ]

        for label in placeholders:
            row: QWidget = QWidget()
            row_layout: QHBoxLayout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)

            cb: QCheckBox = QCheckBox(label)
            cb.setObjectName("settingsToggle")
            cb.setEnabled(False)
            row_layout.addWidget(cb)

            coming: QLabel = QLabel("Coming soon")
            coming.setObjectName("infoLabel")
            coming.setStyleSheet("color: #aaaaaa; font-style: italic;")
            row_layout.addWidget(coming)

            row_layout.addStretch()
            body.addWidget(row)

        return card
