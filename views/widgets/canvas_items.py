"""Interactive canvas item classes.

Provides a family of QGraphicsObject subclasses that support
selection, dragging, resizing, snapping, alignment guidelines,
layer ordering, and context menus.  These are the building blocks
for the template editor's interactive canvas.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QFontMetrics,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QGraphicsTextItem,
    QMenu,
    QStyle,
    QWidget,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
HANDLE_SIZE: float = 8.0
HANDLE_HALF: float = HANDLE_SIZE / 2.0
MIN_ITEM_SIZE: float = 20.0
SNAP_THRESHOLD: float = 8.0
GUIDE_COLOR: QColor = QColor("#1a73e8")
GUIDE_PEN: QPen = QPen(GUIDE_COLOR, 1, Qt.PenStyle.DashLine)
SELECTION_PEN: QPen = QPen(QColor("#1a73e8"), 2, Qt.PenStyle.DashLine)
HANDLE_BRUSH: QBrush = QBrush(QColor("#ffffff"))
HANDLE_PEN: QPen = QPen(QColor("#1a73e8"), 1)

_CURSOR_MAP: dict[int, Qt.CursorShape] = {
    0: Qt.CursorShape.SizeFDiagCursor,   # TL
    1: Qt.CursorShape.SizeVerCursor,      # T
    2: Qt.CursorShape.SizeBDiagCursor,    # TR
    3: Qt.CursorShape.SizeHorCursor,      # R
    4: Qt.CursorShape.SizeFDiagCursor,    # BR
    5: Qt.CursorShape.SizeVerCursor,      # B
    6: Qt.CursorShape.SizeBDiagCursor,    # BL
    7: Qt.CursorShape.SizeHorCursor,      # L
}


# ---------------------------------------------------------------------------
# Helper – handle positions (8: TL, T, TR, R, BR, B, BL, L)
# ---------------------------------------------------------------------------
def _handle_positions(rect: QRectF) -> list[QPointF]:
    """Return the 8 handle centre points for *rect*."""
    return [
        rect.topLeft(),
        QPointF(rect.center().x(), rect.top()),
        rect.topRight(),
        QPointF(rect.right(), rect.center().y()),
        rect.bottomRight(),
        QPointF(rect.center().x(), rect.bottom()),
        rect.bottomLeft(),
        QPointF(rect.left(), rect.center().y()),
    ]


def _handle_rects(rect: QRectF) -> list[QRectF]:
    """Return the 8 handle bounding rectangles for *rect*."""
    return [
        QRectF(p.x() - HANDLE_HALF, p.y() - HANDLE_HALF, HANDLE_SIZE, HANDLE_SIZE)
        for p in _handle_positions(rect)
    ]


# ---------------------------------------------------------------------------
# Base interactive item
# ---------------------------------------------------------------------------

class BaseCanvasItem(QGraphicsObject):
    """Abstract base for all interactive canvas items.

    Provides selection visuals, 8 resize handles, movable+selectable
    flags, snap-to-grid, alignment guidelines, context menu, and
    layer-order operations.

    Signals
    -------
    item_selected:
        Emitted when this item becomes selected.
    item_moved:
        Emitted after the item's position changes.
        Carries ``(item, new_x, new_y)``.
    item_resized:
        Emitted after a resize operation completes.
        Carries ``(item, x, y, w, h)`` (the item's geometry).
    item_deleted:
        Emitted just before the item is removed from the scene.
    """

    item_selected = Signal(object)
    item_moved = Signal(object, float, float)
    item_resized = Signal(object, float, float, float, float)
    item_deleted = Signal(object)

    def __init__(self, x: float, y: float, w: float, h: float) -> None:
        """Initialise the item at *(x, y)* with size *(w, h)*.

        Args:
            x: Initial scene X position.
            y: Initial scene Y position.
            w: Item width.
            h: Item height.
        """
        super().__init__()
        self._rect: QRectF = QRectF(0, 0, max(w, MIN_ITEM_SIZE), max(h, MIN_ITEM_SIZE))
        self.setPos(x, y)

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

        self._snap_enabled: bool = True
        self._snap_size: float = 10.0
        self._locked: bool = False
        self._active_handle: int = -1
        self._drag_start_pos: QPointF = QPointF()
        self._guide_lines: list[QGraphicsItem] = []

    # ------------------------------------------------------------------
    # Public configuration
    # ------------------------------------------------------------------

    def set_snap(self, enabled: bool, size: float = 10.0) -> None:
        """Enable or disable grid snapping.

        Args:
            enabled: Whether to snap to the grid.
            size:    Grid cell size in scene units.
        """
        self._snap_enabled = enabled
        self._snap_size = max(1.0, size)

    def set_locked(self, locked: bool) -> None:
        """Lock or unlock the item (prevents move/resize).

        Args:
            locked: ``True`` to lock.
        """
        self._locked = locked

    @property
    def item_rect(self) -> QRectF:
        """The inner content rectangle (local coordinates)."""
        return QRectF(self._rect)

    # ------------------------------------------------------------------
    # QGraphicsItem interface
    # ------------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        """Return the bounding rect including handles."""
        m: float = HANDLE_HALF + 2.0
        return self._rect.adjusted(-m, -m, m, m)

    def paint(
        self,
        painter: QPainter,
        option: QStyle,
        widget: QWidget | None = None,
    ) -> None:
        """Draw the item contents, selection border, and handles."""
        # Subclass must override to draw its content first, then call this
        if self.isSelected():
            painter.setPen(SELECTION_PEN)
            painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            painter.drawRect(self._rect)
            self._draw_handles(painter)

    def _draw_handles(self, painter: QPainter) -> None:
        """Draw the 8 resize handles."""
        for hr in _handle_rects(self._rect):
            painter.fillRect(hr, HANDLE_BRUSH)
            painter.setPen(HANDLE_PEN)
            painter.drawRect(hr)

    def shape(self) -> QPainterPath:
        """Return the shape for hit-testing including handle margin."""
        from PySide6.QtGui import QPainterPath

        path: QPainterPath = QPainterPath()
        m: float = HANDLE_HALF + 2.0
        path.addRect(self._rect.adjusted(-m, -m, m, m))
        return path

    # ------------------------------------------------------------------
    # Hover
    # ------------------------------------------------------------------

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent) -> None:  # noqa: N802
        """Update cursor shape based on handle proximity."""
        if self._locked:
            super().hoverMoveEvent(event)
            return
        idx: int = self._handle_at(event.pos())
        if idx >= 0:
            self.setCursor(QCursor(_CURSOR_MAP.get(idx, Qt.CursorShape.ArrowCursor)))
        else:
            self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        super().hoverMoveEvent(event)

    # ------------------------------------------------------------------
    # Mouse handling
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:  # noqa: N802
        """Start a resize or drag operation."""
        if self._locked:
            event.ignore()
            return
        self._active_handle = self._handle_at(event.pos())
        if self._active_handle >= 0:
            self._drag_start_pos = event.scenePos()
            event.accept()
        else:
            super().mousePressEvent(event)
            self._drag_start_pos = event.pos()
            if self.isSelected():
                self.item_selected.emit(self)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:  # noqa: N802
        """Perform resize or drag, and show alignment guides."""
        if self._active_handle >= 0:
            self._resize_to(event)
        else:
            super().mouseMoveEvent(event)
        self._update_guides(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:  # noqa: N802
        """Finish resize/drag, snap, and clear guides."""
        self._clear_guides()
        if self._active_handle >= 0:
            self._active_handle = -1
            self._snap_rect()
            self.item_resized.emit(
                self, self.pos().x(), self.pos().y(),
                self._rect.width(), self._rect.height(),
            )
        else:
            if self._snap_enabled:
                self._snap_position()
            self._snap_to_center()
            self.item_moved.emit(self, self.pos().x(), self.pos().y())
        super().mouseReleaseEvent(event)

    def _snap_to_center(self) -> None:
        """Snap the item's centre to the card centre if close enough."""
        scene: QGraphicsScene | None = self.scene()
        if scene is None:
            return
        sr: QRectF = scene.sceneRect()
        cx: float = sr.center().x()
        cy: float = sr.center().y()
        pc: QPointF = self._rect.center() + self.pos()
        if abs(pc.x() - cx) < SNAP_THRESHOLD:
            self.setPos(cx - self._rect.center().x(), self.pos().y())
        if abs(pc.y() - cy) < SNAP_THRESHOLD:
            self.setPos(self.pos().x(), cy - self._rect.center().y())

    # ------------------------------------------------------------------
    # Resize logic
    # ------------------------------------------------------------------

    def _resize_to(self, event: QGraphicsSceneMouseEvent) -> None:
        """Update the item rectangle based on handle drag delta."""
        delta: QPointF = event.scenePos() - self._drag_start_pos
        self._drag_start_pos = event.scenePos()

        r: QRectF = QRectF(self._rect)
        dx: float = delta.x()
        dy: float = delta.y()

        # 0=TL, 1=T, 2=TR, 3=R, 4=BR, 5=B, 6=BL, 7=L
        h: int = self._active_handle
        if h in (0, 1, 2):
            r.setTop(r.top() + dy)
        if h in (4, 5, 6):
            r.setBottom(r.bottom() + dy)
        if h in (0, 6, 7):
            r.setLeft(r.left() + dx)
        if h in (2, 3, 4):
            r.setRight(r.right() + dx)

        # Minimum size protection
        if r.width() < MIN_ITEM_SIZE:
            r.setWidth(MIN_ITEM_SIZE)
        if r.height() < MIN_ITEM_SIZE:
            r.setHeight(MIN_ITEM_SIZE)

        self.prepareGeometryChange()
        self._rect = r
        self.update()

    # ------------------------------------------------------------------
    # Snap
    # ------------------------------------------------------------------

    def _snap_position(self) -> None:
        """Snap the item's scene position to the grid."""
        p: QPointF = self.pos()
        sx: float = round(p.x() / self._snap_size) * self._snap_size
        sy: float = round(p.y() / self._snap_size) * self._snap_size
        self.setPos(sx, sy)

    def _snap_rect(self) -> None:
        """Snap the item's top-left corner to the grid after resize."""
        if not self._snap_enabled:
            return
        p: QPointF = self.pos()
        sx: float = round(p.x() / self._snap_size) * self._snap_size
        sy: float = round(p.y() / self._snap_size) * self._snap_size
        self.setPos(sx, sy)

    # ------------------------------------------------------------------
    # Alignment guides
    # ------------------------------------------------------------------

    def _update_guides(self, event: QGraphicsSceneMouseEvent) -> None:
        """Draw temporary alignment guides while dragging/resizing."""
        self._clear_guides()
        scene: QGraphicsScene | None = self.scene()
        if scene is None:
            return

        sr: QRectF = scene.sceneRect()
        cx: float = sr.center().x()
        cy: float = sr.center().y()
        pc: QPointF = self._rect.center() + self.pos()
        lines: list[tuple[float, float, float, float]] = []

        # Card centre vertical guide
        if abs(pc.x() - cx) < SNAP_THRESHOLD:
            lines.append((cx, sr.top(), cx, sr.bottom()))

        # Card centre horizontal guide
        if abs(pc.y() - cy) < SNAP_THRESHOLD:
            lines.append((sr.left(), cy, sr.right(), cy))

        for x1, y1, x2, y2 in lines:
            line: QGraphicsItem = scene.addLine(x1, y1, x2, y2, GUIDE_PEN)
            line.setZValue(9999)
            self._guide_lines.append(line)

    def _clear_guides(self) -> None:
        """Remove all temporary guide lines from the scene."""
        scene: QGraphicsScene | None = self.scene()
        if scene is not None:
            for line in self._guide_lines:
                scene.removeItem(line)
        self._guide_lines.clear()

    # ------------------------------------------------------------------
    # Item changes
    # ------------------------------------------------------------------

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):  # noqa: N802
        """Emit signals when selection or position changes."""
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            if value:
                self.item_selected.emit(self)
        return super().itemChange(change, value)

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:  # noqa: N802
        """Show the right-click context menu."""
        menu: QMenu = QMenu()

        menu.addAction("Delete", self._delete_action)
        menu.addAction("Duplicate", self._duplicate_action)
        menu.addSeparator()

        menu.addAction("Bring to Front", self._bring_to_front_action)
        menu.addAction("Send to Back", self._send_to_back_action)
        menu.addAction("Move Forward", self._move_forward_action)
        menu.addAction("Move Backward", self._move_backward_action)
        menu.addSeparator()

        if self._locked:
            menu.addAction("Unlock", lambda: self.set_locked(False))
        else:
            menu.addAction("Lock", lambda: self.set_locked(True))
        menu.addSeparator()

        menu.addAction("Properties", self._properties_action)

        menu.exec(event.screenPos())

    # ------------------------------------------------------------------
    # Context menu actions
    # ------------------------------------------------------------------

    def _delete_action(self) -> None:
        """Remove this item from the scene."""
        self.item_deleted.emit(self)
        scene: QGraphicsScene | None = self.scene()
        if scene is not None:
            scene.removeItem(self)

    def _duplicate_action(self) -> None:
        """Create a copy of this item offset by 20 px."""
        scene: QGraphicsScene | None = self.scene()
        if scene is None:
            return
        clone: BaseCanvasItem = self._clone()
        clone.setPos(self.pos() + QPointF(20, 20))
        clone.set_snap(self._snap_enabled, self._snap_size)
        scene.addItem(clone)

    def _bring_to_front_action(self) -> None:
        """Set this item's Z value above all siblings."""
        scene = self.scene()
        if scene is None:
            return
        max_z: float = max(
            (i.zValue() for i in scene.items()),
            default=0.0,
        )
        self.setZValue(max_z + 1.0)

    def _send_to_back_action(self) -> None:
        """Set this item's Z value below all siblings."""
        scene = self.scene()
        if scene is None:
            return
        min_z: float = min(
            (i.zValue() for i in scene.items()),
            default=0.0,
        )
        self.setZValue(min_z - 1.0)

    def _move_forward_action(self) -> None:
        """Raise this item by one layer."""
        self.setZValue(self.zValue() + 1.0)

    def _move_backward_action(self) -> None:
        """Lower this item by one layer."""
        self.setZValue(self.zValue() - 1.0)

    def _properties_action(self) -> None:
        """Open a placeholder properties dialog."""
        from PySide6.QtWidgets import QMessageBox  # noqa: PLC0415

        QMessageBox.information(
            None,
            "Properties",
            f"Properties for {type(self).__name__}\n\n"
            f"Position: ({self.pos().x():.0f}, {self.pos().y():.0f})\n"
            f"Size: {self._rect.width():.0f} × {self._rect.height():.0f}",
        )

    # ------------------------------------------------------------------
    # Clone (overridden by subclasses)
    # ------------------------------------------------------------------

    def _clone(self) -> BaseCanvasItem:
        """Return a copy of this item (overridden by subclasses)."""
        return BaseCanvasItem(0, 0, self._rect.width(), self._rect.height())

    # ------------------------------------------------------------------
    # Handle hit-test
    # ------------------------------------------------------------------

    def _handle_at(self, pos: QPointF) -> int:
        """Return the index of the handle at *pos*, or -1."""
        for i, hr in enumerate(_handle_rects(self._rect)):
            if hr.contains(pos):
                return i
        return -1


# ===================================================================
# Concrete item types
# ===================================================================


class TextFieldItem(BaseCanvasItem):
    """An editable text field on the card canvas.

    Supports two modes:
    - **Dynamic** (``is_static=False``): Label shows the field name,
      linked to Card Generator form data via ``mapped_field``.
    - **Static** (``is_static=True``): Hardcoded text that never changes.

    Dynamic fields show a light-blue background; static fields use
    light-yellow.
    """

    _DYNAMIC_BRUSH: QBrush = QBrush(QColor("#f0f8ff"))
    _STATIC_BRUSH: QBrush = QBrush(QColor("#fffff0"))
    _BORDER_PEN: QPen = QPen(QColor("#bbbbbb"), 1)

    def __init__(
        self,
        x: float,
        y: float,
        is_static: bool = False,
        mapped_field: str = "",
        static_text: str = "",
    ) -> None:
        """Initialise a text field at *(x, y)*.

        Args:
            x: Scene X position.
            y: Scene Y position.
            is_static: ``True`` for static labels, ``False`` for dynamic.
            mapped_field: Semantic field name for dynamic fields
                (e.g. ``"employee_name"``).
            static_text: Literal text for static labels.
        """
        super().__init__(x, y, 180, 32)
        self._font: QFont = QFont("Arial", 12)
        self._is_static: bool = is_static
        self._mapped_field: str = mapped_field
        self._text: str = static_text if is_static else (mapped_field.replace("_", " ").title() if mapped_field else "Text Field")
        self._editing: bool = False
        self._text_item: QGraphicsTextItem | None = None

    def paint(
        self,
        painter: QPainter,
        option: QStyle,
        widget: QWidget | None = None,
    ) -> None:
        """Draw the field background, text, and selection handles."""
        painter.setBrush(self._DYNAMIC_BRUSH if not self._is_static else self._STATIC_BRUSH)
        painter.setPen(self._BORDER_PEN)
        painter.drawRect(self._rect)

        if not self._editing:
            painter.setFont(self._font)
            painter.setPen(QColor("#333333"))
            tr: QRectF = self._rect.adjusted(6, 4, -6, -4)
            painter.drawText(tr, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._text)

            # Show mapping indicator for dynamic fields
            if self._is_static:
                painter.setFont(QFont("Segoe UI", 7))
                painter.setPen(QColor("#999999"))
                painter.drawText(tr.adjusted(0, 0, 0, -14), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight, "static")
            elif self._mapped_field:
                painter.setFont(QFont("Segoe UI", 7))
                painter.setPen(QColor("#8888cc"))
                field_label: str = self._mapped_field.replace("_", " ")
                painter.drawText(tr.adjusted(0, 0, 0, -14), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight, field_label)

        super().paint(painter, option, widget)

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:  # noqa: N802
        """Enter text-editing mode on double-click."""
        self._editing = True
        self._text_item = QGraphicsTextItem(self._text, self)
        self._text_item.setFont(self._font)
        self._text_item.setPos(6, 4)
        self._text_item.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextEditorInteraction
        )
        self._text_item.setFocus()
        self._text_item.document().contentsChanged.connect(self._on_text_changed)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.update()

    def _on_text_changed(self) -> None:
        """Update internal text from the editor widget."""
        if self._text_item is not None:
            self._text = self._text_item.toPlainText()

    def _finish_editing(self) -> None:
        """Exit text-editing mode."""
        self._editing = False
        if self._text_item is not None:
            self._text = self._text_item.toPlainText()
            self.scene().removeItem(self._text_item)
            self._text_item = None
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.update()

    def _clone(self) -> TextFieldItem:
        """Return a copy of this text field."""
        item = TextFieldItem(
            0, 0,
            is_static=self._is_static,
            mapped_field=self._mapped_field,
            static_text=self._text if self._is_static else "",
        )
        item._font = QFont(self._font)
        return item


class PhotoFieldItem(BaseCanvasItem):
    """An image / photo placeholder on the card canvas.

    Shows a camera icon placeholder and a dashed border.
    Supports linking to the Card Generator photo via ``mapped_field``.
    """

    _PHOTO_BRUSH: QBrush = QBrush(QColor("#fafafa"))
    _DASHED_PEN: QPen = QPen(QColor("#aaaaaa"), 1.5, Qt.PenStyle.DashLine)

    def __init__(self, x: float, y: float, mapped_field: str = "") -> None:
        """Initialise a photo field at *(x, y)*.

        Args:
            x: Scene X position.
            y: Scene Y position.
            mapped_field: Semantic field name (e.g. ``"employee_photo"``).
        """
        super().__init__(x, y, 100, 120)
        self._mapped_field: str = mapped_field

    def paint(
        self,
        painter: QPainter,
        option: QStyle,
        widget: QWidget | None = None,
    ) -> None:
        """Draw the photo placeholder with icon and label."""
        painter.setBrush(self._PHOTO_BRUSH)
        painter.setPen(self._DASHED_PEN)
        painter.drawRect(self._rect)

        label: str = self._mapped_field.replace("_", " ").title() if self._mapped_field else "Photo"
        painter.setFont(QFont("Segoe UI", 10))
        painter.setPen(QColor("#999999"))
        painter.drawText(
            self._rect,
            Qt.AlignmentFlag.AlignCenter,
            f"📷\n{label}",
        )

        super().paint(painter, option, widget)

    def _clone(self) -> PhotoFieldItem:
        """Return a copy of this photo field."""
        return PhotoFieldItem(0, 0, mapped_field=self._mapped_field)


class RectangleItem(BaseCanvasItem):
    """A simple filled rectangle shape.

    Can be customised with different fill colours and border styles.
    """

    _FILL_BRUSH: QBrush = QBrush(QColor("#e8f0fe"))
    _BORDER_PEN: QPen = QPen(QColor("#1a73e8"), 1.5)

    def __init__(self, x: float, y: float) -> None:
        """Initialise a rectangle at *(x, y)*.

        Args:
            x: Scene X position.
            y: Scene Y position.
        """
        super().__init__(x, y, 120, 80)

    def paint(
        self,
        painter: QPainter,
        option: QStyle,
        widget: QWidget | None = None,
    ) -> None:
        """Draw the filled rectangle."""
        painter.setBrush(self._FILL_BRUSH)
        painter.setPen(self._BORDER_PEN)
        painter.drawRect(self._rect)

        super().paint(painter, option, widget)

    def _clone(self) -> RectangleItem:
        """Return a copy of this rectangle."""
        return RectangleItem(0, 0)


class CircleItem(BaseCanvasItem):
    """A circle / ellipse shape."""

    _FILL_BRUSH: QBrush = QBrush(QColor("#fce8e6"))
    _BORDER_PEN: QPen = QPen(QColor("#d93025"), 1.5)

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, 120, 80)

    def paint(
        self,
        painter: QPainter,
        option: QStyle,
        widget: QWidget | None = None,
    ) -> None:
        painter.setBrush(self._FILL_BRUSH)
        painter.setPen(self._BORDER_PEN)
        painter.drawEllipse(self._rect)
        super().paint(painter, option, widget)

    def _clone(self) -> CircleItem:
        return CircleItem(0, 0)


class LineItem(BaseCanvasItem):
    """A thin line shape drawn as a filled rectangle.

    Serves as a base for horizontal and vertical lines.
    """

    _FILL_BRUSH: QBrush = QBrush(QColor("#333333"))
    _BORDER_PEN: QPen = QPen(Qt.NoPen)

    def paint(
        self,
        painter: QPainter,
        option: QStyle,
        widget: QWidget | None = None,
    ) -> None:
        painter.setBrush(self._FILL_BRUSH)
        painter.setPen(self._BORDER_PEN)
        painter.drawRect(self._rect)
        super().paint(painter, option, widget)


class HorizontalLineItem(LineItem):
    """A horizontal divider line."""

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, 200, 4)

    def _clone(self) -> HorizontalLineItem:
        return HorizontalLineItem(0, 0)


class VerticalLineItem(LineItem):
    """A vertical divider line."""

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, 4, 150)

    def _clone(self) -> VerticalLineItem:
        return VerticalLineItem(0, 0)


class ImageItem(BaseCanvasItem):
    """An item that displays an image loaded from a file."""

    _BORDER_PEN: QPen = QPen(QColor("#1a73e8"), 1.5)

    def __init__(self, x: float, y: float, image_path: str = "") -> None:
        super().__init__(x, y, 160, 120)
        self._image_path: str = image_path
        self._pixmap: QPixmap | None = None
        if image_path:
            self._pixmap = QPixmap(image_path)

    @property
    def image_path(self) -> str:
        return self._image_path

    def set_image_path(self, path: str) -> None:
        self._image_path = path
        self._pixmap = QPixmap(path) if path else None
        self.update()

    def paint(
        self,
        painter: QPainter,
        option: QStyle,
        widget: QWidget | None = None,
    ) -> None:
        if self._pixmap and not self._pixmap.isNull():
            painter.drawPixmap(self._rect, self._pixmap, self._pixmap.rect())
        else:
            painter.setBrush(QBrush(QColor("#f1f3f4")))
            painter.setPen(self._BORDER_PEN)
            painter.drawRect(self._rect)
            painter.setPen(QColor("#5f6368"))
            painter.drawText(self._rect, Qt.AlignCenter, "Image")
        super().paint(painter, option, widget)

    def _clone(self) -> ImageItem:
        return ImageItem(0, 0, self._image_path)


class BackgroundItem(BaseCanvasItem):
    """A background image item for the card canvas.

    Behaves like a normal canvas item: selectable, draggable,
    resizable with handles.  Constrained to remain inside the
    card boundaries by default.
    """

    def __init__(self, x: float, y: float, w: float, h: float, image_path: str = "") -> None:
        super().__init__(x, y, w, h)
        self._image_path: str = image_path
        self._pixmap: QPixmap | None = None
        self._constraint_rect: QRectF | None = None
        if image_path:
            self._pixmap = QPixmap(image_path)

    @property
    def image_path(self) -> str:
        return self._image_path

    def set_image_path(self, path: str) -> None:
        self._image_path = path
        self._pixmap = QPixmap(path) if path else None
        self.update()

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self.update()

    def set_constraint_rect(self, rect: QRectF) -> None:
        self._constraint_rect = QRectF(rect)

    def paint(
        self,
        painter: QPainter,
        option: QStyle,
        widget: QWidget | None = None,
    ) -> None:
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                int(self._rect.width()),
                int(self._rect.height()),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            ox = (self._rect.width() - scaled.width()) / 2.0
            oy = (self._rect.height() - scaled.height()) / 2.0
            painter.drawPixmap(
                self._rect.x() + ox,
                self._rect.y() + oy,
                scaled,
            )
        else:
            painter.setBrush(QBrush(QColor("#f0f0f0")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(self._rect)
        super().paint(painter, option, widget)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):  # noqa: N802
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self._constraint_rect is not None:
            new_pos = QPointF(value) if not isinstance(value, QPointF) else value
            clamped_x = max(
                self._constraint_rect.left(),
                min(new_pos.x(), self._constraint_rect.right() - max(self._rect.width(), MIN_ITEM_SIZE)),
            )
            clamped_y = max(
                self._constraint_rect.top(),
                min(new_pos.y(), self._constraint_rect.bottom() - max(self._rect.height(), MIN_ITEM_SIZE)),
            )
            return QPointF(clamped_x, clamped_y)
        return super().itemChange(change, value)

    def _clone(self) -> BackgroundItem:
        item = BackgroundItem(0, 0, self._rect.width(), self._rect.height(), self._image_path)
        if self._constraint_rect is not None:
            item.set_constraint_rect(self._constraint_rect)
        return item
