"""Card editor canvas widget.

Provides a QGraphicsView-based canvas with a checkerboard
background, centred card area, keyboard/mouse interaction,
multi-selection, zoom, and item-management methods.
"""
import traceback

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QResizeEvent,
    QTransform,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QWidget,
)

from config.constants import CARD_HEIGHT_PX, CARD_WIDTH_PX
from models.field import TemplateField
from views.widgets.canvas_items import (
    BaseCanvasItem,
    CircleItem,
    HorizontalLineItem,
    ImageItem,
    PhotoFieldItem,
    RectangleItem,
    TextFieldItem,
    VerticalLineItem,
)


class EditorCanvas(QGraphicsView):
    """Card editing canvas with checkerboard background.

    Supports adding, selecting, dragging, resizing, deleting, and
    duplicating interactive items via keyboard and mouse.

    Signals
    -------
    zoom_changed:
        Emitted when the zoom level changes.  Carries the
        current scale factor (1.0 = 100 %).
    mouse_position_changed:
        Emitted on mouse move over the scene.  Carries the
        scene-space ``(x, y)`` coordinates.
    object_selected:
        Emitted when an item is selected.  Carries the item.
    selection_changed:
        Emitted when the selection state changes.
    """

    zoom_changed = Signal(float)
    mouse_position_changed = Signal(float, float)
    object_selected = Signal(object)
    selection_changed = Signal()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise the canvas with a scene and checkerboard."""
        super().__init__(parent)
        self.setObjectName("editorCanvas")

        self._scene: QGraphicsScene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.SmartViewportUpdate
        )
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Snap settings
        self._snap_enabled: bool = True
        self._snap_size: float = 10.0

        # Clipboard for copy/paste
        self._clipboard: list[BaseCanvasItem] = []

        # Background image item
        self._background_item: QGraphicsItem | None = None

        self._setup_scene()

        # Connect scene selection signal
        self._scene.selectionChanged.connect(self._on_scene_selection_changed)

    # ------------------------------------------------------------------
    # Scene construction
    # ------------------------------------------------------------------

    def _setup_scene(self) -> None:
        """Build the scene: background brush, card rect, placeholder text."""
        checker: QPixmap = self._create_checkerboard(16)
        self._scene.setBackgroundBrush(QBrush(checker))

        margin: int = 60
        card_x: int = margin
        card_y: int = margin
        self._card_w: int = CARD_WIDTH_PX
        self._card_h: int = CARD_HEIGHT_PX

        self._card_item: QGraphicsRectItem = self._scene.addRect(
            card_x,
            card_y,
            self._card_w,
            self._card_h,
            QPen(QColor("#cccccc"), 1),
            QBrush(QColor("#ffffff")),
        )
        self._card_item.setData(0, "cardRect")
        self._card_item.setFlag(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True
        )
        self._card_item.setFlag(
            QGraphicsRectItem.GraphicsItemFlag.ItemClipsChildrenToShape, True
        )

        self._placeholder: QGraphicsSimpleTextItem = (
            self._scene.addSimpleText(
                "No Template Loaded",
                QFont("Segoe UI", 18, QFont.Weight.Normal),
            )
        )
        self._placeholder.setBrush(QBrush(QColor("#bbbbbb")))
        self._placeholder.setData(0, "canvasPlaceholder")

        text_w: float = self._placeholder.boundingRect().width()
        text_h: float = self._placeholder.boundingRect().height()
        self._placeholder.setPos(
            card_x + (self._card_w - text_w) / 2.0,
            card_y + (self._card_h - text_h) / 2.0,
        )

        self._scene.setSceneRect(
            0,
            0,
            self._card_w + margin * 2,
            self._card_h + margin * 2,
        )

    @staticmethod
    def _create_checkerboard(size: int = 16) -> QPixmap:
        """Create a checkerboard pattern pixmap.

        Args:
            size: Side length of each checker tile in pixels.

        Returns:
            A 2 × 2 tile QPixmap suitable as a scene background brush.
        """
        half: int = size // 2
        pix: QPixmap = QPixmap(size, size)
        pix.fill(QColor("#ffffff"))
        painter: QPainter = QPainter(pix)
        painter.fillRect(0, 0, half, half, QColor("#e0e0e0"))
        painter.fillRect(half, half, half, half, QColor("#e0e0e0"))
        painter.end()
        return pix

    # ------------------------------------------------------------------
    # Snap configuration
    # ------------------------------------------------------------------

    def set_snap_enabled(self, enabled: bool) -> None:
        """Enable or disable grid snapping for all items.

        Args:
            enabled: ``True`` to snap to grid.
        """
        self._snap_enabled = enabled
        for item in self._scene.items():
            if isinstance(item, BaseCanvasItem):
                item.set_snap(enabled, self._snap_size)

    def set_snap_size(self, size: float) -> None:
        """Set the grid snap size in scene units.

        Args:
            size: Grid cell size (minimum 2).
        """
        self._snap_size = max(2.0, size)
        if self._snap_enabled:
            for item in self._scene.items():
                if isinstance(item, BaseCanvasItem):
                    item.set_snap(True, self._snap_size)

    # ------------------------------------------------------------------
    # Item factory methods
    # ------------------------------------------------------------------

    def add_text_field(self, x: float | None = None, y: float | None = None) -> TextFieldItem:
        """Add a new text field item to the scene.

        Args:
            x: Scene X (defaults to card centre).
            y: Scene Y (defaults to card centre).

        Returns:
            The newly created TextFieldItem.
        """
        item: TextFieldItem = TextFieldItem(
            x or (self._card_w / 2 + 60),
            y or (self._card_h / 2 + 60),
        )
        self._configure_item(item)
        return item

    def add_photo_field(self, x: float | None = None, y: float | None = None) -> PhotoFieldItem:
        """Add a new photo field item to the scene.

        Args:
            x: Scene X (defaults to card centre).
            y: Scene Y (defaults to card centre).

        Returns:
            The newly created PhotoFieldItem.
        """
        item: PhotoFieldItem = PhotoFieldItem(
            x or (self._card_w / 2 + 60),
            y or (self._card_h / 2 + 60),
        )
        self._configure_item(item)
        return item

    def add_rectangle(self, x: float | None = None, y: float | None = None) -> RectangleItem:
        """Add a new rectangle shape to the scene.

        Args:
            x: Scene X (defaults to card centre).
            y: Scene Y (defaults to card centre).

        Returns:
            The newly created RectangleItem.
        """
        item: RectangleItem = RectangleItem(
            x or (self._card_w / 2 + 60),
            y or (self._card_h / 2 + 60),
        )
        self._configure_item(item)
        return item

    def add_circle(self, x: float | None = None, y: float | None = None) -> CircleItem:
        item: CircleItem = CircleItem(
            x or (self._card_w / 2 + 60),
            y or (self._card_h / 2 + 60),
        )
        self._configure_item(item)
        return item

    def add_horizontal_line(self, x: float | None = None, y: float | None = None) -> HorizontalLineItem:
        item: HorizontalLineItem = HorizontalLineItem(
            x or (self._card_w / 2 + 60),
            y or (self._card_h / 2 + 60),
        )
        self._configure_item(item)
        return item

    def add_vertical_line(self, x: float | None = None, y: float | None = None) -> VerticalLineItem:
        item: VerticalLineItem = VerticalLineItem(
            x or (self._card_w / 2 + 60),
            y or (self._card_h / 2 + 60),
        )
        self._configure_item(item)
        return item

    def add_image_item(self, image_path: str = "") -> ImageItem:
        item: ImageItem = ImageItem(
            self._card_w / 2 + 60,
            self._card_h / 2 + 60,
            image_path,
        )
        self._configure_item(item)
        return item

    def _configure_item(self, item: BaseCanvasItem) -> None:
        """Add an item to the scene and connect its signals.

        Args:
            item: The item to configure.
        """
        item.set_snap(self._snap_enabled, self._snap_size)
        item.item_selected.connect(self._on_item_selected)
        item.item_deleted.connect(self._on_item_deleted)
        self._scene.addItem(item)
        item.setSelected(True)
        self._hide_placeholder()
        self.object_selected.emit(item)

    def _hide_placeholder(self) -> None:
        """Hide the 'No Template Loaded' text when items or background exist."""
        all_items = list(self._scene.items())
        canvas_items = [i for i in all_items if isinstance(i, BaseCanvasItem)]
        has_items: bool = len(canvas_items) > 0
        has_bg: bool = self._background_item is not None
        visible: bool = not has_items and not has_bg
        print(f"[TRACE _hide_placeholder] scene items={len(all_items)} canvas_items={len(canvas_items)} has_bg={has_bg} -> placeholder visible={visible}")
        self._placeholder.setVisible(visible)

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------

    def selected_canvas_items(self) -> list[BaseCanvasItem]:
        """Return all currently selected BaseCanvasItem instances.

        Returns:
            A list of selected items (may be empty).
        """
        return [
            i for i in self._scene.selectedItems()
            if isinstance(i, BaseCanvasItem)
        ]

    def _on_scene_selection_changed(self) -> None:
        """Emit ``selection_changed`` when the scene selection updates."""
        self.selection_changed.emit()

    def _on_item_selected(self, item: object) -> None:
        """Emit ``object_selected`` with the chosen item.

        Args:
            item: The item that was selected.
        """
        self.object_selected.emit(item)

    def _on_item_deleted(self, item: object) -> None:
        """React to an item being deleted.

        Args:
            item: The item that was removed.
        """
        self._hide_placeholder()

    # ------------------------------------------------------------------
    # Background image
    # ------------------------------------------------------------------

    def _set_card_brush(self, color: QColor) -> None:
        self._card_item.setBrush(QBrush(color))

    def set_background_image(self, path: str) -> None:
        """Load and display a background image on the card area."""
        self._clear_background()
        print(f"[TRACE set_bg] path='{path}'")
        from PySide6.QtGui import QPixmap  # noqa: PLC0415

        pixmap: QPixmap = QPixmap(path)
        is_null: bool = pixmap.isNull()
        print(f"[TRACE set_bg] QPixmap.isNull()={is_null}")
        if is_null:
            print(f"[TRACE set_bg] PIXMAP IS NULL — image not found or invalid format")
            return

        card_rect = self._card_item.rect()
        scaled: QPixmap = pixmap.scaled(
            int(card_rect.width()),
            int(card_rect.height()),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        print(f"[TRACE set_bg] scaled size={scaled.width()}x{scaled.height()}")
        item = self._scene.addPixmap(scaled)
        item.setPos(self._card_item.pos())
        item.setZValue(-1)
        self._background_item = item
        self._set_card_brush(QColor(0, 0, 0, 0))
        print(f"[TRACE set_bg] background_item set, zValue=-1, calling _hide_placeholder")
        self._hide_placeholder()

    def _clear_background(self) -> None:
        """Remove the current background image from the scene."""
        if self._background_item is not None and self._background_item.scene() is not None:
            self._scene.removeItem(self._background_item)
            self._background_item = None
        self._set_card_brush(QColor("#ffffff"))

    # ------------------------------------------------------------------
    # Load / save fields
    # ------------------------------------------------------------------

    def load_fields(self, fields: list[TemplateField]) -> None:
        """Clear existing items and recreate them from *fields*."""
        print(f"[TRACE load_fields] START: {len(fields)} fields")
        # Remove existing canvas items
        removed: int = 0
        for item in list(self._scene.items()):
            if isinstance(item, BaseCanvasItem):
                self._scene.removeItem(item)
                removed += 1
        print(f"[TRACE load_fields] removed {removed} existing items")

        card_pos = self._card_item.pos()
        print(f"[TRACE load_fields] card_pos=({card_pos.x()}, {card_pos.y()})")

        created: int = 0
        for field in fields:
            x: float = card_pos.x() + field.x * CARD_WIDTH_PX / 85.6
            y: float = card_pos.y() + field.y * CARD_HEIGHT_PX / 54.0
            w: float = field.width * CARD_WIDTH_PX / 85.6
            h: float = field.height * CARD_HEIGHT_PX / 54.0

            obj_type: str = field.object_type
            print(f"[TRACE load_fields] creating field type='{obj_type}' pos=({x:.1f},{y:.1f}) size=({w:.1f},{h:.1f})")

            if obj_type == "text_field":
                item: BaseCanvasItem = TextFieldItem(x, y)
                item._rect = QRectF(0, 0, max(w, 20), max(h, 20))
            elif obj_type == "photo_field":
                item = PhotoFieldItem(x, y)
                item._rect = QRectF(0, 0, max(w, 20), max(h, 20))
            elif obj_type in ("rectangle", "line"):
                item = RectangleItem(x, y)
                item._rect = QRectF(0, 0, max(w, 20), max(h, 20))
            elif obj_type == "circle":
                item = CircleItem(x, y)
                item._rect = QRectF(0, 0, max(w, 20), max(h, 20))
            elif obj_type == "horizontal_line":
                item = HorizontalLineItem(x, y)
                item._rect = QRectF(0, 0, max(w, 20), max(h, 20))
            elif obj_type == "vertical_line":
                item = VerticalLineItem(x, y)
                item._rect = QRectF(0, 0, max(w, 20), max(h, 20))
            elif obj_type == "image":
                img_path = field.field_name if field.field_name and field.field_name.startswith(("C:", "D:", "E:", "/", "\\")) else ""
                item = ImageItem(x, y, img_path)
                item._rect = QRectF(0, 0, max(w, 20), max(h, 20))
            else:
                print(f"[TRACE load_fields] UNKNOWN type '{obj_type}' — SKIPPING")
                continue

            item.setZValue(float(field.z_order))
            item.set_snap(self._snap_enabled, self._snap_size)
            item.item_selected.connect(self._on_item_selected)
            item.item_deleted.connect(self._on_item_deleted)
            self._scene.addItem(item)
            created += 1

        print(f"[TRACE load_fields] created {created} items, calling _hide_placeholder")
        self._hide_placeholder()
        print(f"[TRACE load_fields] DONE")

    def get_fields(self, template_id: int) -> list[TemplateField]:
        """Extract ``TemplateField`` objects from the current canvas items.

        Args:
            template_id: The owning template's id.

        Returns:
            A list of ``TemplateField`` objects.
        """
        from utils.helpers import timestamp_now  # noqa: PLC0415

        now: str = timestamp_now()
        fields: list[TemplateField] = []
        card_pos = self._card_item.pos()

        for i, scene_item in enumerate(self._scene.items()):
            if not isinstance(scene_item, BaseCanvasItem):
                continue

            x_mm: float = (scene_item.pos().x() - card_pos.x()) * 85.6 / CARD_WIDTH_PX
            y_mm: float = (scene_item.pos().y() - card_pos.y()) * 54.0 / CARD_HEIGHT_PX
            w_mm: float = scene_item.item_rect.width() * 85.6 / CARD_WIDTH_PX
            h_mm: float = scene_item.item_rect.height() * 54.0 / CARD_HEIGHT_PX

            obj_type: str = "text_field"

            if isinstance(scene_item, TextFieldItem):
                obj_type = "text_field"
            elif isinstance(scene_item, PhotoFieldItem):
                obj_type = "photo_field"
            elif isinstance(scene_item, RectangleItem):
                obj_type = "rectangle"
            elif isinstance(scene_item, CircleItem):
                obj_type = "circle"
            elif isinstance(scene_item, HorizontalLineItem):
                obj_type = "horizontal_line"
            elif isinstance(scene_item, VerticalLineItem):
                obj_type = "vertical_line"
            elif isinstance(scene_item, ImageItem):
                obj_type = "image"

            field_name: str = f"field_{i}"
            if isinstance(scene_item, ImageItem):
                field_name = scene_item.image_path or f"field_{i}"

            field = TemplateField(
                template_id=template_id,
                object_type=obj_type,
                field_name=field_name,
                display_name=f"Field {i}",
                field_type="text" if obj_type == "text_field" else "photo",
                x=round(x_mm, 2),
                y=round(y_mm, 2),
                width=round(max(w_mm, 5.0), 2),
                height=round(max(h_mm, 5.0), 2),
                z_order=i,
                page_side="front",
                created_at=now,
            )
            fields.append(field)

        return fields

    # ------------------------------------------------------------------
    # Keyboard handling
    # ------------------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """Handle keyboard shortcuts for editing operations.

        - Arrow keys: move selected items (Shift = 10 px).
        - Delete / Backspace: delete selected items.
        - Ctrl+C: copy selected items.
        - Ctrl+V: paste copied items.
        - Ctrl+D: duplicate selected items.
        """
        modifiers: Qt.KeyboardModifier = event.modifiers()
        key: int = event.key()

        selected: list[BaseCanvasItem] = self.selected_canvas_items()

        # --- Arrow-key nudge ---
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down) and selected:
            step: float = 10.0 if modifiers & Qt.KeyboardModifier.ShiftModifier else 1.0
            dx: float = 0.0
            dy: float = 0.0
            if key == Qt.Key.Key_Left:
                dx = -step
            elif key == Qt.Key.Key_Right:
                dx = step
            elif key == Qt.Key.Key_Up:
                dy = -step
            elif key == Qt.Key.Key_Down:
                dy = step
            for item in selected:
                item.moveBy(dx, dy)
            event.accept()
            return

        # --- Delete ---
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and selected:
            for item in selected:
                item._delete_action()
            event.accept()
            return

        # --- Copy (Ctrl+C) ---
        if key == Qt.Key.Key_C and modifiers & Qt.KeyboardModifier.ControlModifier and selected:
            self._clipboard = [item._clone() for item in selected]
            event.accept()
            return

        # --- Paste (Ctrl+V) ---
        if key == Qt.Key.Key_V and modifiers & Qt.KeyboardModifier.ControlModifier and self._clipboard:
            for item in self._clipboard:
                clone: BaseCanvasItem = item._clone()
                clone.setPos(item.pos() + QPointF(20, 20))
                self._configure_item(clone)
            self._clipboard = []
            event.accept()
            return

        # --- Duplicate (Ctrl+D) ---
        if key == Qt.Key.Key_D and modifiers & Qt.KeyboardModifier.ControlModifier and selected:
            for item in selected:
                item._duplicate_action()
            event.accept()
            return

        super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Zoom API
    # ------------------------------------------------------------------

    def zoom_in(self) -> None:
        """Zoom in by 15 %."""
        self._apply_zoom(1.15)

    def zoom_out(self) -> None:
        """Zoom out by 15 %."""
        self._apply_zoom(1.0 / 1.15)

    def reset_zoom(self) -> None:
        """Restore the default 100 % zoom level."""
        self.resetTransform()
        self.zoom_changed.emit(1.0)

    def fit_to_screen(self) -> None:
        """Scale and centre the view so the entire card is visible."""
        self.fitInView(
            self._card_item,
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        self.zoom_changed.emit(self._current_zoom())

    def _apply_zoom(self, factor: float) -> None:
        """Scale the view by *factor* and emit the new zoom level.

        Args:
            factor: Multiplicative zoom factor (>1 to zoom in).
        """
        self.scale(factor, factor)
        self.zoom_changed.emit(self._current_zoom())

    def _current_zoom(self) -> float:
        """Return the current zoom level (1.0 = 100 %)."""
        t: QTransform = self.transform()
        return t.m11()

    # ------------------------------------------------------------------
    # Event overrides
    # ------------------------------------------------------------------

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        """Zoom with Ctrl + mouse-wheel."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta: float = event.angleDelta().y()
            factor: float = 1.0 + (delta / 1200.0)
            self._apply_zoom(factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Track mouse position in scene coordinates."""
        scene_pos = self.mapToScene(event.position().toPoint())
        self.mouse_position_changed.emit(scene_pos.x(), scene_pos.y())
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Handle Ctrl+click for multi-selection toggling."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            item = self.itemAt(event.position().toPoint())
            if item is not None and isinstance(item, QGraphicsItem):
                item.setSelected(not item.isSelected())
                event.accept()
                return
        super().mousePressEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        """Re-centre the view on the card after a resize."""
        super().resizeEvent(event)
        self.fit_to_screen()
