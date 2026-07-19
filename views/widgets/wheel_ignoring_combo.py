"""Widget subclasses that ignore mouse-wheel scrolling.

Use these anywhere a control should only change via explicit user
interaction, never via accidental scroll-wheel rotation.

Includes:
    * ``WheelIgnoringComboBox`` — QComboBox variant
    * ``WheelIgnoringSpinBox`` — QSpinBox variant
    * ``WheelIgnoringDoubleSpinBox`` — QDoubleSpinBox variant
"""

from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QSpinBox


class WheelIgnoringComboBox(QComboBox):
    """A combo-box that ignores mouse-wheel events."""

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()


class WheelIgnoringSpinBox(QSpinBox):
    """A spin-box that ignores mouse-wheel events."""

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()


class WheelIgnoringDoubleSpinBox(QDoubleSpinBox):
    """A double-spin-box that ignores mouse-wheel events."""

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()
