"""Template editor view.

Provides a full-screen editing workspace similar to professional
design tools: a top toolbar, left properties panel, central
QGraphicsView canvas, right field toolbox, bottom properties
inspector, and an editor-specific status bar.
"""

import logging
import traceback

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from config.constants import (
    CARD_HEIGHT_MM,
    CARD_HEIGHT_PX,
    CARD_WIDTH_MM,
    CARD_WIDTH_PX,
)
from config.settings import resolve_template_image
from controllers.template_controller import TemplateController
from models.template import CardTemplate
from utils.logger import setup_logger
from views.widgets.editor_canvas import EditorCanvas

logger = setup_logger(__name__)


class TemplateEditorView(QWidget):
    """Full card-template editing workspace.

    Signals
    -------
    save_requested:
        Emitted when the Save Layout button is clicked.
    open_requested:
        Emitted when the Open Template button is clicked.
    """

    save_requested = Signal()
    open_requested = Signal()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        """Initialise the editor, toolbar, panels and canvas."""
        super().__init__()
        self.setObjectName("templateEditorView")

        self._template_ctrl: TemplateController = TemplateController()
        self._current_template_id: int | None = None
        self._front_image: str = ""
        self._back_image: str = ""

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Build the complete editor workspace layout."""
        root: QVBoxLayout = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_toolbar())

        body: QSplitter = QSplitter(Qt.Orientation.Horizontal)
        body.setObjectName("editorBody")
        body.setHandleWidth(1)
        body.setChildrenCollapsible(False)

        body.addWidget(self._build_properties_panel())
        body.addWidget(self._build_canvas_panel())
        body.addWidget(self._build_field_toolbox())

        body.setStretchFactor(0, 0)
        body.setStretchFactor(1, 1)
        body.setStretchFactor(2, 0)
        body.setSizes([300, 600, 220])

        root.addWidget(body, stretch=1)
        root.addWidget(self._build_inspector())
        root.addWidget(self._build_status_bar())

    # ------------------------------------------------------------------
    # Top toolbar
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> QWidget:
        """Construct the editor toolbar.

        Returns:
            A widget containing file, edit, zoom and view buttons.
        """
        bar: QWidget = QWidget()
        bar.setObjectName("editorToolbar")
        bar.setFixedHeight(42)

        layout: QHBoxLayout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(4)

        file_actions: list[tuple[str, str, str, str]] = [
            ("Open Template", "SP_DialogOpenButton", "open", "Open an existing template from the database"),
            ("Save Layout", "SP_DialogSaveButton", "save", "Save the current template layout"),
        ]
        for text, pixmap_name, action, tooltip in file_actions:
            btn: QPushButton = QPushButton(
                QApplication.style().standardIcon(
                    getattr(QStyle.StandardPixmap, pixmap_name)
                ),
                text,
            )
            btn.setObjectName("editorToolbarBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.clicked.connect(
                lambda checked=False, a=action: self._on_toolbar_action(a)
            )
            layout.addWidget(btn)

        layout.addWidget(self._make_separator())

        edit_actions: list[tuple[str, str, str, str]] = [
            ("Undo", "SP_ArrowBack", "undo", "Undo the last action"),
            ("Redo", "SP_ArrowForward", "redo", "Redo the last undone action"),
        ]
        for text, pixmap_name, action, tooltip in edit_actions:
            btn = QPushButton(
                QApplication.style().standardIcon(
                    getattr(QStyle.StandardPixmap, pixmap_name)
                ),
                text,
            )
            btn.setObjectName("editorToolbarBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.clicked.connect(
                lambda checked=False, a=action: self._on_toolbar_action(a)
            )
            layout.addWidget(btn)

        layout.addWidget(self._make_separator())

        zoom_actions: list[tuple[str, str, str, str]] = [
            ("Zoom In", "SP_ArrowUp", "zoom_in", "Zoom into the canvas"),
            ("Zoom Out", "SP_ArrowDown", "zoom_out", "Zoom out of the canvas"),
            ("Reset Zoom", "SP_BrowserReload", "reset_zoom", "Reset zoom to 100%"),
            ("Fit to Screen", "SP_FileDialogInfoView", "fit_screen", "Fit the card to the canvas area"),
        ]
        for text, pixmap_name, action, tooltip in zoom_actions:
            btn = QPushButton(
                QApplication.style().standardIcon(
                    getattr(QStyle.StandardPixmap, pixmap_name)
                ),
                text,
            )
            btn.setObjectName("editorToolbarBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.clicked.connect(
                lambda checked=False, a=action: self._on_toolbar_action(a)
            )
            layout.addWidget(btn)

        layout.addWidget(self._make_separator())

        self._grid_btn: QPushButton = QPushButton("Grid")
        self._grid_btn.setObjectName("editorToolbarBtn")
        self._grid_btn.setCheckable(True)
        self._grid_btn.setChecked(True)
        self._grid_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._grid_btn.setToolTip("Toggle grid snapping on/off")
        layout.addWidget(self._grid_btn)

        layout.addStretch()
        return bar

    @staticmethod
    def _make_separator() -> QFrame:
        """A small vertical line used between toolbar groups."""
        sep: QFrame = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setObjectName("editorToolbarSep")
        sep.setFixedWidth(12)
        return sep

    # ------------------------------------------------------------------
    # Left panel — properties
    # ------------------------------------------------------------------

    def _build_properties_panel(self) -> QWidget:
        """Construct the properties panel (left side).

        Returns:
            A scrollable widget with template name, card side,
            canvas size, grid and zoom controls.
        """
        panel: QWidget = QWidget()
        panel.setObjectName("propertiesPanel")
        panel.setMinimumWidth(260)
        panel.setMaximumWidth(340)

        scroll: QScrollArea = QScrollArea()
        scroll.setObjectName("formScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        container: QWidget = QWidget()
        container.setObjectName("formContainer")
        layout: QVBoxLayout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # --- Template section ---
        layout.addWidget(self._make_section_title("Template"))
        self._editor_name_input: QLineEdit = QLineEdit()
        self._editor_name_input.setObjectName("fieldInput")
        self._editor_name_input.setPlaceholderText("Enter template name")
        layout.addWidget(self._editor_name_input)

        self._editor_card_side: QComboBox = QComboBox()
        self._editor_card_side.setObjectName("fieldInput")
        self._editor_card_side.addItems(["Front", "Back"])
        layout.addWidget(self._make_field_row("Card Side:", self._editor_card_side))

        # --- Canvas Size section ---
        layout.addWidget(self._make_section_title("Canvas Size"))

        form: QFormLayout = QFormLayout()
        form.setSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self._width_spin: QDoubleSpinBox = QDoubleSpinBox()
        self._width_spin.setObjectName("fieldInput")
        self._width_spin.setRange(10.0, 200.0)
        self._width_spin.setValue(CARD_WIDTH_MM)
        self._width_spin.setSuffix(" mm")
        form.addRow("Card Width:", self._width_spin)

        self._height_spin: QDoubleSpinBox = QDoubleSpinBox()
        self._height_spin.setObjectName("fieldInput")
        self._height_spin.setRange(10.0, 150.0)
        self._height_spin.setValue(CARD_HEIGHT_MM)
        self._height_spin.setSuffix(" mm")
        form.addRow("Card Height:", self._height_spin)

        layout.addLayout(form)

        # --- Grid section ---
        layout.addWidget(self._make_section_title("Grid"))

        self._grid_spin: QSpinBox = QSpinBox()
        self._grid_spin.setObjectName("fieldInput")
        self._grid_spin.setRange(1, 100)
        self._grid_spin.setValue(10)
        self._grid_spin.setSuffix(" px")
        layout.addWidget(self._make_field_row("Grid Size:", self._grid_spin))

        self._zoom_spin: QSpinBox = QSpinBox()
        self._zoom_spin.setObjectName("fieldInput")
        self._zoom_spin.setRange(10, 800)
        self._zoom_spin.setValue(100)
        self._zoom_spin.setSuffix(" %")
        self._zoom_spin.setReadOnly(True)
        self._zoom_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        layout.addWidget(self._make_field_row("Zoom:", self._zoom_spin))

        self._snap_check: QCheckBox = QCheckBox("Snap to Grid")
        self._snap_check.setObjectName("fieldInput")
        self._snap_check.setChecked(True)
        layout.addWidget(self._snap_check)

        layout.addStretch()
        scroll.setWidget(container)

        panel_layout: QVBoxLayout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addWidget(scroll)

        return panel

    # ------------------------------------------------------------------
    # Centre panel — canvas
    # ------------------------------------------------------------------

    def _build_canvas_panel(self) -> QWidget:
        """Construct the central editing canvas.

        Returns:
            A widget containing the EditorCanvas.
        """
        panel: QWidget = QWidget()
        panel.setObjectName("canvasPanel")

        layout: QVBoxLayout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self._canvas: EditorCanvas = EditorCanvas()
        self._canvas.zoom_changed.connect(self._on_zoom_changed)
        self._canvas.mouse_position_changed.connect(
            self._on_mouse_position_changed
        )

        layout.addWidget(self._canvas)

        return panel

    # ------------------------------------------------------------------
    # Right panel — field toolbox
    # ------------------------------------------------------------------

    def _build_field_toolbox(self) -> QWidget:
        """Construct the field toolbox (right side).

        Returns:
            A scrollable widget with buttons for each field type.
        """
        panel: QWidget = QWidget()
        panel.setObjectName("fieldToolbox")
        panel.setMinimumWidth(190)
        panel.setMaximumWidth(250)

        scroll: QScrollArea = QScrollArea()
        scroll.setObjectName("formScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        container: QWidget = QWidget()
        container.setObjectName("formContainer")
        layout: QVBoxLayout = QVBoxLayout(container)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(4)

        # --- Fields section ---
        layout.addWidget(self._make_section_title("Fields"))

        self._field_buttons: dict[str, QPushButton] = {}
        field_buttons: list[str] = [
            "Add Text Field",
            "Add Photo Field",
        ]
        for text in field_buttons:
            btn: QPushButton = QPushButton(text)
            btn.setObjectName("fieldToolboxBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(
                lambda checked=False, t=text: self._on_field_button(t)
            )
            layout.addWidget(btn)
            self._field_buttons[text] = btn

        layout.addSpacing(12)

        # --- Shapes section ---
        layout.addWidget(self._make_section_title("Shapes"))

        self._shape_buttons: dict[str, QPushButton] = {}
        shape_buttons: list[str] = [
            "Horizontal Line",
            "Vertical Line",
            "Rectangle",
            "Circle",
        ]
        for text in shape_buttons:
            btn = QPushButton(text)
            btn.setObjectName("fieldToolboxBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(
                lambda checked=False, t=text: self._on_field_button(t)
            )
            layout.addWidget(btn)
            self._shape_buttons[text] = btn

        layout.addSpacing(12)

        # --- Media section ---
        layout.addWidget(self._make_section_title("Media"))

        self._media_buttons: dict[str, QPushButton] = {}
        media_buttons: list[str] = ["Image", "Logo"]
        for text in media_buttons:
            btn = QPushButton(text)
            btn.setObjectName("fieldToolboxBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(
                lambda checked=False, t=text: self._on_field_button(t)
            )
            layout.addWidget(btn)
            self._media_buttons[text] = btn

        layout.addStretch()
        scroll.setWidget(container)

        panel_layout: QVBoxLayout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addWidget(scroll)

        return panel

    # ------------------------------------------------------------------
    # Bottom panel — inspector
    # ------------------------------------------------------------------

    def _build_inspector(self) -> QWidget:
        """Construct the bottom properties inspector.

        Returns:
            A widget showing placeholder fields for object
            properties (X, Y, Width, Height, Rotation, etc.).
        """
        panel: QWidget = QWidget()
        panel.setObjectName("inspectorPanel")
        panel.setFixedHeight(90)

        layout: QHBoxLayout = QHBoxLayout(panel)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        self._inspector_label: QLabel = QLabel("No object selected")
        self._inspector_label.setObjectName("inspectorLabel")
        self._inspector_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(self._inspector_label)

        layout.addStretch()

        return panel

    # ------------------------------------------------------------------
    # Editor status bar
    # ------------------------------------------------------------------

    def _build_status_bar(self) -> QWidget:
        """Construct the editor-specific status bar.

        Returns:
            A widget showing mouse position, canvas size, zoom
            and selected object info.
        """
        bar: QWidget = QWidget()
        bar.setObjectName("editorStatusBar")
        bar.setFixedHeight(28)

        layout: QHBoxLayout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(16)

        self._status_pos: QLabel = QLabel("X: 0  Y: 0")
        self._status_pos.setObjectName("editorStatusLabel")
        layout.addWidget(self._status_pos)

        self._status_size: QLabel = QLabel(
            f"{CARD_WIDTH_PX} × {CARD_HEIGHT_PX} px"
        )
        self._status_size.setObjectName("editorStatusLabel")
        layout.addWidget(self._status_size)

        self._status_zoom: QLabel = QLabel("Zoom: 100 %")
        self._status_zoom.setObjectName("editorStatusLabel")
        layout.addWidget(self._status_zoom)

        self._status_object: QLabel = QLabel("Object: None")
        self._status_object.setObjectName("editorStatusLabel")
        layout.addWidget(self._status_object)

        layout.addStretch()
        return bar

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_section_title(text: str) -> QLabel:
        """Create a bold section heading label.

        Args:
            text: The heading text.

        Returns:
            A styled QLabel.
        """
        label: QLabel = QLabel(text)
        label.setObjectName("propertiesSectionTitle")
        return label

    @staticmethod
    def _make_field_row(label_text: str, widget: QWidget) -> QWidget:
        """Create a labelled field row.

        Args:
            label_text: Text for the label.
            widget: The input widget placed to the right.

        Returns:
            A horizontally laid-out row widget.
        """
        row: QWidget = QWidget()
        row_layout: QHBoxLayout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        label: QLabel = QLabel(label_text)
        label.setObjectName("fieldLabel")
        row_layout.addWidget(label)

        row_layout.addWidget(widget, stretch=1)
        return row

    # ------------------------------------------------------------------
    # Signal connections
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        """Wire controls to canvas methods and update displays."""
        # Snap checkbox
        self._snap_check.toggled.connect(self._canvas.set_snap_enabled)
        self._snap_check.toggled.connect(self._grid_btn.setChecked)

        # Grid button in toolbar
        self._grid_btn.toggled.connect(self._canvas.set_snap_enabled)
        self._grid_btn.toggled.connect(self._snap_check.setChecked)

        # Grid size spinbox
        self._grid_spin.valueChanged.connect(self._canvas.set_snap_size)

        # Canvas selection signals
        self._canvas.object_selected.connect(self._on_object_selected)
        self._canvas.selection_changed.connect(self._on_selection_changed)

        # Card side switching
        self._editor_card_side.currentIndexChanged.connect(
            self._on_card_side_changed
        )

        # Save / open toolbar buttons
        self.save_requested.connect(self._on_save)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_template(self, template_id: int) -> None:
        """Load a template into the editor."""
        logger.info("=== load_template START id=%d ===", template_id)
        print(f"[TRACE] load_template START id={template_id}")

        try:
            template: CardTemplate | None = self._template_ctrl.get_template_by_id(
                template_id
            )
            print(f"[TRACE] get_template_by_id returned: {template}")
            if template is None:
                logger.warning("Template id=%d not found", template_id)
                QMessageBox.warning(
                    self, "Error",
                    f"Template id={template_id} not found."
                )
                return

            self._current_template_id = template_id
            print(f"[TRACE] template_name='{template.template_name}'")
            print(f"[TRACE] front_image='{template.front_image}' back_image='{template.back_image}'")
            print(f"[TRACE] canvas_width={template.canvas_width} canvas_height={template.canvas_height}")
            print(f"[TRACE] grid_size={template.grid_size} snap_to_grid={template.snap_to_grid}")

            self._front_image = resolve_template_image(template.front_image) or ""
            self._back_image = resolve_template_image(template.back_image) or ""
            self._editor_name_input.setText(template.template_name)
            self._width_spin.setValue(template.canvas_width)
            self._height_spin.setValue(template.canvas_height)
            self._grid_spin.setValue(template.grid_size)
            self._snap_check.setChecked(template.snap_to_grid)
            self._canvas.set_snap_enabled(template.snap_to_grid)
            self._canvas.set_snap_size(template.grid_size)
            print("[TRACE] Properties panel updated. Calling setCurrentIndex(0)")
            self._editor_card_side.setCurrentIndex(0)

            # Always clear old background first, then load new one.
            # Note: setCurrentIndex(0) above may NOT trigger _on_card_side_changed
            # if the index is already 0, so we must explicitly load here.
            self._canvas._clear_background()
            if self._front_image:
                self._canvas.set_background_image(self._front_image)

            # Load fields onto canvas
            print("[TRACE] Calling load_layout...")
            fields = self._template_ctrl.load_layout(template_id)
            print(f"[TRACE] load_layout returned {len(fields)} fields")
            for i, f in enumerate(fields):
                print(f"  field[{i}]: type={f.object_type} name={f.field_name} x={f.x} y={f.y} w={f.width} h={f.height}")
            print("[TRACE] Calling load_fields...")
            self._canvas.load_fields(fields)
            print("[TRACE] load_fields completed")

            logger.info(
                "Loaded template id=%d '%s' into editor",
                template_id, template.template_name
            )
            print(f"[TRACE] === load_template SUCCESS id={template_id} ===")

        except Exception as exc:
            print(f"[TRACE] === load_template EXCEPTION: {exc} ===")
            traceback.print_exc()
            logger.exception("load_template failed for id=%d", template_id)
            QMessageBox.critical(
                self, "Template Load Error",
                f"Failed to load template id={template_id}:\n\n{exc}\n\n"
                f"See logs/application.log for details."
            )

    def _on_save(self) -> None:
        """Save the current template layout."""
        if self._current_template_id is None:
            QMessageBox.information(
                self, "No Template",
                "No template is currently loaded in the editor."
            )
            return

        template: CardTemplate | None = self._template_ctrl.get_template_by_id(
            self._current_template_id
        )
        if template is None:
            QMessageBox.warning(self, "Error", "Template not found in database.")
            return

        name: str = self._editor_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Template name cannot be empty.")
            return

        template.template_name = name
        template.canvas_width = self._width_spin.value()
        template.canvas_height = self._height_spin.value()
        template.grid_size = self._grid_spin.value()
        template.snap_to_grid = self._snap_check.isChecked()

        fields = self._canvas.get_fields(self._current_template_id)

        try:
            self._template_ctrl.save_full_template(template, fields)
            QMessageBox.information(
                self, "Saved",
                f"Template '{name}' saved successfully."
            )
            logger.info("Editor saved template id=%d", self._current_template_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Error", str(exc))

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_toolbar_action(self, action: str) -> None:
        """Dispatch toolbar button clicks.

        Args:
            action: One of ``'open'``, ``'save'``, ``'undo'``,
                ``'redo'``, ``'zoom_in'``, ``'zoom_out'``,
                ``'reset_zoom'``, ``'fit_screen'``.
        """
        if action == "open":
            self.open_requested.emit()
        elif action == "save":
            self.save_requested.emit()
        elif action == "zoom_in":
            self._canvas.zoom_in()
        elif action == "zoom_out":
            self._canvas.zoom_out()
        elif action == "reset_zoom":
            self._canvas.reset_zoom()
        elif action == "fit_screen":
            self._canvas.fit_to_screen()

    def _on_zoom_changed(self, zoom: float) -> None:
        """Update the zoom display when the canvas zoom changes.

        Args:
            zoom: Current zoom factor (1.0 = 100 %).
        """
        percent: int = round(zoom * 100)
        self._zoom_spin.setValue(percent)
        self._status_zoom.setText(f"Zoom: {percent} %")

    def _on_mouse_position_changed(self, x: float, y: float) -> None:
        """Update the status bar mouse-position display.

        Args:
            x: Scene-space X coordinate.
            y: Scene-space Y coordinate.
        """
        self._status_pos.setText(f"X: {x:.0f}  Y: {y:.0f}")

    # ------------------------------------------------------------------
    # Toolbox button handler
    # ------------------------------------------------------------------

    def _on_add_image(self) -> None:
        """Open a file dialog to select an image and add it to the canvas."""
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.svg);;All Files (*.*)"
        )
        if path:
            self._canvas.add_image_item(path)

    def _on_field_button(self, button_text: str) -> None:
        """Handle field / shape toolbox button clicks.

        Args:
            button_text: The label of the button clicked.
        """
        if button_text == "Add Text Field":
            self._canvas.add_text_field()
        elif button_text == "Add Photo Field":
            self._canvas.add_photo_field()
        elif button_text == "Rectangle":
            self._canvas.add_rectangle()
        elif button_text == "Circle":
            self._canvas.add_circle()
        elif button_text == "Horizontal Line":
            self._canvas.add_horizontal_line()
        elif button_text == "Vertical Line":
            self._canvas.add_vertical_line()
        elif button_text in ("Image", "Logo"):
            self._on_add_image()

    # ------------------------------------------------------------------
    # Card side switching
    # ------------------------------------------------------------------

    def _on_card_side_changed(self, index: int) -> None:
        """Switch the canvas background between front and back."""
        self._canvas._clear_background()
        if index == 0 and self._front_image:
            self._canvas.set_background_image(self._front_image)
        elif index == 1 and self._back_image:
            self._canvas.set_background_image(self._back_image)

    # ------------------------------------------------------------------
    # Selection display
    # ------------------------------------------------------------------

    def _on_object_selected(self, item: object) -> None:
        """Update the status bar and inspector with the selected object.

        Args:
            item: The selected canvas item.
        """
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

        if isinstance(item, TextFieldItem):
            name: str = "Text Field"
        elif isinstance(item, PhotoFieldItem):
            name = "Photo Field"
        elif isinstance(item, RectangleItem):
            name = "Rectangle"
        elif isinstance(item, CircleItem):
            name = "Circle"
        elif isinstance(item, HorizontalLineItem):
            name = "Horizontal Line"
        elif isinstance(item, VerticalLineItem):
            name = "Vertical Line"
        elif isinstance(item, ImageItem):
            name = "Image"
        elif isinstance(item, BaseCanvasItem):
            name = "Canvas Item"
        else:
            name = "Unknown"

        self._status_object.setText(f"Object: {name}")
        self._inspector_label.setText(f"Selected: {name}")

    def _on_selection_changed(self) -> None:
        """Update UI when the scene selection changes."""
        selected = self._canvas.selected_canvas_items()
        if selected:
            self._on_object_selected(selected[-1])
        else:
            self._status_object.setText("Object: None")
            self._inspector_label.setText("No object selected")
