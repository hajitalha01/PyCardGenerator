"""QComboBox subclass that ignores mouse-wheel scrolling.

Use this anywhere a combo-box should only change via explicit
click-and-select, never via accidental scroll-wheel rotation.
"""

from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QComboBox


class WheelIgnoringComboBox(QComboBox):
    """A combo-box that ignores mouse-wheel events."""

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()
