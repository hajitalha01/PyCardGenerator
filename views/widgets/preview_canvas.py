"""Zoomable card preview canvas.

Provides a ``QGraphicsView``-based card preview that supports
mouse-wheel zoom, click-and-drag pan, fit-to-window, and
programmatic zoom control.  Maintains the ID-1 card aspect ratio
(85.6 × 54.0 mm) when displaying placeholder content.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPixmap,
    QResizeEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class PreviewCanvas(QWidget):
    """Zoomable card preview with title label.

    Displays a title heading above a ``QGraphicsView`` that shows
    either a card image (via ``set_pixmap``) or placeholder text.
    Supports mouse-wheel zoom (Ctrl+Scroll), click-and-drag pan,
    fit-to-window, and programmatic zoom.
    """

    def __init__(
        self, title: str, parent: QWidget | None = None
    ) -> None:
        """Initialise the preview canvas.

        Args:
            title: Section heading shown above the viewport.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setObjectName("previewCanvas")

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._title_label: QLabel = QLabel(title)
        self._title_label.setObjectName("previewCardTitle")
        layout.addWidget(self._title_label)

        self._view: _CardGraphicsView = _CardGraphicsView()
        layout.addWidget(self._view, stretch=1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_pixmap(self, pixmap: QPixmap | None) -> None:
        """Set the card image to display.

        Passing ``None`` restores the placeholder text.

        Args:
            pixmap: The card image, or ``None`` to clear.
        """
        self._view.set_pixmap(pixmap)

    def set_placeholder(self, text: str) -> None:
        """Set the placeholder text shown when no pixmap is set.

        Args:
            text: Placeholder string.
        """
        self._view.set_placeholder(text)

    def zoom_in(self) -> None:
        """Zoom in by a fixed factor (1.25×)."""
        self._view.zoom_in()

    def zoom_out(self) -> None:
        """Zoom out by a fixed factor (0.8×)."""
        self._view.zoom_out()

    def reset_zoom(self) -> None:
        """Reset zoom to 1:1 and re-fit the image."""
        self._view.reset_zoom()

    def fit_to_window(self) -> None:
        """Scale the image to fit the viewport."""
        self._view.fit_in_view()

    # ------------------------------------------------------------------
    # Public access to inner view (for advanced interaction)
    # ------------------------------------------------------------------

    def current_pixmap(self) -> QPixmap:
        """Return the currently displayed pixmap.

        Returns:
            The current ``QPixmap`` (may be null).
        """
        return self._view.current_pixmap()

    @property
    def graphics_view(self) -> QGraphicsView:
        """The inner ``QGraphicsView`` instance for advanced use."""
        return self._view


class _CardGraphicsView(QGraphicsView):
    """Internal graphics view with zoom, pan and placeholder support."""

    _PLACEHOLDER_COLOR: str = "#888888"
    _PLACEHOLDER_FONT_SIZE: int = 14
    _ZOOM_FACTOR: float = 1.15
    _FIT_MARGIN: int = 8

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise the graphics view."""
        super().__init__(parent)
        self.setObjectName("cardGraphicsView")
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setStyleSheet("background: transparent; border: none;")

        self._scene: QGraphicsScene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._pixmap_item: QGraphicsPixmapItem = QGraphicsPixmapItem()
        self._scene.addItem(self._pixmap_item)

        self._placeholder: str = ""
        self._zoom: float = 1.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_pixmap(self, pixmap: QPixmap | None) -> None:
        """Set or clear the displayed pixmap.

        Args:
            pixmap: The pixmap to show, or ``None`` to clear.
        """
        if pixmap is not None and not pixmap.isNull():
            self._pixmap_item.setPixmap(pixmap)
            self._scene.setSceneRect(
                QRectF(self._pixmap_item.boundingRect())
            )
            self.fit_in_view()
        else:
            self._pixmap_item.setPixmap(QPixmap())
            # Provide a reasonable scene rect for placeholder drawing
            self._scene.setSceneRect(QRectF(0, 0, 400, 250))
            self.resetTransform()
            self._zoom = 1.0
        self.viewport().update()

    def set_placeholder(self, text: str) -> None:
        """Set the placeholder text.

        Args:
            text: Placeholder string.
        """
        self._placeholder = text
        self.set_pixmap(None)

    def zoom_in(self) -> None:
        """Zoom in by a fixed factor."""
        self._apply_zoom(self._ZOOM_FACTOR)

    def zoom_out(self) -> None:
        """Zoom out by a fixed factor."""
        self._apply_zoom(1.0 / self._ZOOM_FACTOR)

    def reset_zoom(self) -> None:
        """Reset zoom to 1.0 and centre the image."""
        self._zoom = 1.0
        self.resetTransform()
        self.fit_in_view()

    def fit_in_view(self) -> None:
        """Scale the image to fit the viewport."""
        if not self._pixmap_item.pixmap().isNull():
            self.fitInView(
                self._pixmap_item,
                Qt.AspectRatioMode.KeepAspectRatio,
            )
            self._zoom = 1.0

    def current_pixmap(self) -> QPixmap:
        """Return the currently displayed pixmap.

        Returns:
            The current ``QPixmap`` (may be null).
        """
        return self._pixmap_item.pixmap()

    # ------------------------------------------------------------------
    # Event overrides
    # ------------------------------------------------------------------

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        """Re-fit the card image when the viewport is resized."""
        super().resizeEvent(event)
        if not self._pixmap_item.pixmap().isNull():
            self.fit_in_view()

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        """Zoom with Ctrl+Scroll; otherwise scroll normally."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor: float = (
                self._ZOOM_FACTOR
                if event.angleDelta().y() > 0
                else 1.0 / self._ZOOM_FACTOR
            )
            self._apply_zoom(factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def drawForeground(  # noqa: N802
        self, painter: QPainter, rect: QRectF
    ) -> None:
        """Draw placeholder text when no pixmap is displayed.

        Args:
            painter: The view's painter.
            rect: The exposed scene rectangle.
        """
        super().drawForeground(painter, rect)
        if self._pixmap_item.pixmap().isNull() and self._placeholder:
            painter.setPen(QColor(self._PLACEHOLDER_COLOR))
            font: QFont = QFont("Arial", self._PLACEHOLDER_FONT_SIZE)
            painter.setFont(font)
            painter.drawText(
                self._scene.sceneRect(),
                Qt.AlignmentFlag.AlignCenter
                | Qt.AlignmentFlag.AlignVCenter,
                self._placeholder,
            )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _apply_zoom(self, factor: float) -> None:
        """Apply a zoom factor around the current mouse position.

        Args:
            factor: Multiplication factor (e.g. 1.15 to zoom in).
        """
        if self._pixmap_item.pixmap().isNull():
            return
        self._zoom *= factor
        self.scale(factor, factor)
