"""Dashboard view.

Serves as the landing page after application launch. Displays
a welcome message and a summary of recent activity.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class DashboardView(QWidget):
    """Home view shown when the application starts.

    Currently displays a welcome message. Future iterations will
    include recent-card history, template quick-actions, and
    generation statistics.
    """

    def __init__(self) -> None:
        """Initialise the dashboard with a welcome banner."""
        super().__init__()
        self.setObjectName("dashboardView")

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        title: QLabel = QLabel("Dashboard")
        title.setObjectName("viewTitle")
        layout.addWidget(title)

        description: QLabel = QLabel(
            "Welcome to Card Generator. Select a page from the "
            "sidebar to get started."
        )
        description.setObjectName("viewDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        placeholder: QWidget = QWidget()
        placeholder.setObjectName("viewContent")
        layout.addWidget(placeholder, stretch=1)
