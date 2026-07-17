"""Settings view.

Allows users to configure application preferences such as
default output directories, export resolution, and card dimensions.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from config.constants import EXPORT_DPI


class SettingsView(QWidget):
    """Application settings panel.

    Provides controls for export resolution, default output
    paths, and other global preferences.
    """

    def __init__(self) -> None:
        """Initialise the view with settings controls."""
        super().__init__()
        self.setObjectName("settingsView")

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        title: QLabel = QLabel("Settings")
        title.setObjectName("viewTitle")
        layout.addWidget(title)

        description: QLabel = QLabel(
            "Configure application preferences and default values."
        )
        description.setObjectName("viewDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        # --- Settings content ---
        content: QWidget = QWidget()
        content.setObjectName("viewContent")
        content_layout: QVBoxLayout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(24)

        # Export resolution
        export_section: QWidget = QWidget()
        export_layout: QFormLayout = QFormLayout(export_section)
        export_layout.setSpacing(10)
        export_layout.setContentsMargins(0, 0, 0, 0)

        export_heading: QLabel = QLabel("Export Resolution")
        export_heading.setObjectName("formSectionTitle")
        export_layout.addRow(export_heading)

        self._dpi_combo: QComboBox = QComboBox()
        self._dpi_combo.setObjectName("fieldInput")
        self._dpi_combo.addItem("300 DPI — Standard Print", 300)
        self._dpi_combo.addItem("600 DPI — Professional Print (Recommended)", 600)
        self._dpi_combo.addItem("1200 DPI — Ultra High Resolution", 1200)

        idx: int = self._dpi_combo.findData(EXPORT_DPI)
        if idx >= 0:
            self._dpi_combo.setCurrentIndex(idx)

        export_layout.addRow("Resolution:", self._dpi_combo)

        dpi_note: QLabel = QLabel(
            "Higher DPI produces sharper text and images but larger file sizes.\n"
            "600 DPI is recommended for professional card printing."
        )
        dpi_note.setObjectName("infoLabel")
        dpi_note.setWordWrap(True)
        export_layout.addRow(dpi_note)

        content_layout.addWidget(export_section)
        content_layout.addStretch()
        layout.addWidget(content, stretch=1)

    @property
    def selected_dpi(self) -> int:
        """The currently selected export DPI value."""
        return self._dpi_combo.currentData() or 600
