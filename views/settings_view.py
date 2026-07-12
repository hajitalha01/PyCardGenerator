"""Settings view.

Allows users to configure application preferences such as
default output directories and card dimensions.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class SettingsView(QWidget):
    """Application settings panel.

    Currently a placeholder. Will include options for default
    output paths, default template, and display preferences.
    """

    def __init__(self) -> None:
        """Initialise the view with title and description."""
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

        placeholder: QWidget = QWidget()
        placeholder.setObjectName("viewContent")
        layout.addWidget(placeholder, stretch=1)
