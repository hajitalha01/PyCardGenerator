"""Card preview widget.

Displays a framed preview of a card, maintaining the physical
aspect ratio (85.6 × 54.0 mm).  Supports both placeholder text
and QPixmap content for future rendering integration.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from config.constants import CARD_HEIGHT_MM, CARD_WIDTH_MM


class CardPreviewWidget(QWidget):
    """Framed card preview that maintains the ID-1 aspect ratio.

    Displays a title, then a card-shaped frame that shows either
    placeholder text or a scaled QPixmap.

    Usage::

        preview = CardPreviewWidget("Front Card")
        preview.set_placeholder("No Front Template Selected")
        preview.set_pixmap(qpixmap)   # when rendering is wired
    """

    _ASPECT: float = CARD_WIDTH_MM / CARD_HEIGHT_MM

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        """Initialise the preview widget with a title.

        Args:
            title:  Section heading shown above the card frame.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setObjectName("cardPreviewWidget")

        self._pixmap: QPixmap | None = None
        self._placeholder_text: str = "No Template Selected"

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        title_label: QLabel = QLabel(title)
        title_label.setObjectName("previewCardTitle")
        layout.addWidget(title_label)

        self._card_frame: QWidget = QWidget()
        self._card_frame.setObjectName("cardFrame")
        self._card_frame.setMinimumSize(160, 100)

        frame_layout: QVBoxLayout = QVBoxLayout(self._card_frame)
        frame_layout.setContentsMargins(8, 8, 8, 8)

        self._display: QLabel = QLabel(self._placeholder_text)
        self._display.setObjectName("cardPlaceholder")
        self._display.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        self._display.setWordWrap(True)
        frame_layout.addWidget(self._display)

        layout.addWidget(self._card_frame, stretch=1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_pixmap(self, pixmap: QPixmap | None) -> None:
        """Set the card image to display.

        Passing ``None`` restores the placeholder text.

        Args:
            pixmap: The card image, or ``None`` to clear.
        """
        self._pixmap = pixmap
        self._update_display()

    def set_placeholder(self, text: str) -> None:
        """Change the placeholder text shown when no pixmap is set.

        Args:
            text: Placeholder string (e.g. ``'No Front Template Selected'``).
        """
        self._placeholder_text = text
        if self._pixmap is None:
            self._display.setText(text)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        """Re-scale the pixmap on every resize to maintain quality."""
        super().resizeEvent(event)
        self._update_display()

    def _update_display(self) -> None:
        """Scale the current pixmap to fit the frame or show placeholder."""
        if self._pixmap is not None and not self._pixmap.isNull():
            # Leave a 4 px margin inside the frame border
            margin: int = 4
            target_w: int = self._card_frame.width() - margin * 2
            target_h: int = self._card_frame.height() - margin * 2

            scaled: QPixmap = self._pixmap.scaled(
                target_w,
                target_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._display.setPixmap(scaled)
        else:
            self._display.setText(self._placeholder_text)
