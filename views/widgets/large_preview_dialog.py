"""Large preview dialog with zoom controls.

Provides an expandable, full-size card preview window with
Zoom In, Zoom Out, Fit Screen, and Reset Zoom controls.
Mouse-wheel zoom is supported inside the preview canvas.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from views.widgets.preview_canvas import PreviewCanvas


class LargePreviewDialog(QDialog):
    """A resizable dialog showing a card preview with zoom controls.

    Usage::

        dialog = LargePreviewDialog(self)
        dialog.set_pixmap(pixmap)
        dialog.exec()
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise the dialog with a preview canvas and zoom toolbar.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Card Preview")
        self.setMinimumSize(800, 600)
        self.resize(960, 720)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Preview canvas
        self._canvas: PreviewCanvas = PreviewCanvas("")
        layout.addWidget(self._canvas, stretch=1)

        # Zoom control toolbar
        controls: QWidget = QWidget()
        controls.setObjectName("previewToolbar")
        controls_layout: QHBoxLayout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        zoom_in_btn: QPushButton = QPushButton("Zoom In")
        zoom_in_btn.setObjectName("previewToolBtn")
        zoom_in_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        zoom_in_btn.clicked.connect(self._canvas.zoom_in)
        controls_layout.addWidget(zoom_in_btn)

        zoom_out_btn: QPushButton = QPushButton("Zoom Out")
        zoom_out_btn.setObjectName("previewToolBtn")
        zoom_out_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        zoom_out_btn.clicked.connect(self._canvas.zoom_out)
        controls_layout.addWidget(zoom_out_btn)

        fit_btn: QPushButton = QPushButton("Fit Screen")
        fit_btn.setObjectName("previewToolBtn")
        fit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fit_btn.clicked.connect(self._canvas.fit_to_window)
        controls_layout.addWidget(fit_btn)

        reset_btn: QPushButton = QPushButton("Reset Zoom")
        reset_btn.setObjectName("previewToolBtn")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.clicked.connect(self._canvas.reset_zoom)
        controls_layout.addWidget(reset_btn)

        controls_layout.addStretch()

        close_btn: QPushButton = QPushButton("Close")
        close_btn.setObjectName("previewToolBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        controls_layout.addWidget(close_btn)

        layout.addWidget(controls)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_pixmap(self, pixmap: QPixmap | None) -> None:
        """Set the card image to display.

        Args:
            pixmap: The card image, or ``None`` to show placeholder.
        """
        self._canvas.set_pixmap(pixmap)

    def set_placeholder(self, text: str) -> None:
        """Set the placeholder text when no image is shown.

        Args:
            text: Placeholder string.
        """
        self._canvas.set_placeholder(text)
