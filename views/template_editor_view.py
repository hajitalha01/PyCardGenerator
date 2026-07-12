"""Template editor view.

Provides a full-screen editing workspace similar to professional
design tools: a top toolbar, left properties panel, central
QGraphicsView canvas, right field toolbox, bottom properties
inspector, and an editor-specific status bar.
"""

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
from views.widgets.editor_canvas import EditorCanvas


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
        name_input: QLineEdit = QLineEdit()
        name_input.setObjectName("fieldInput")
        name_input.setPlaceholderText("Enter template name")
        layout.addWidget(name_input)

        card_side: QComboBox = QComboBox()
        card_side.setObjectName("fieldInput")
        card_side.addItems(["Front", "Back"])
        layout.addWidget(self._make_field_row("Card Side:", card_side))

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
            "Add QR Field",
            "Add Barcode Field",
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

        media_buttons: list[str] = ["Image", "Logo"]
        for text in media_buttons:
            btn = QPushButton(text)
            btn.setObjectName("fieldToolboxBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(btn)

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
            PhotoFieldItem,
            RectangleItem,
            TextFieldItem,
        )

        if isinstance(item, TextFieldItem):
            name: str = "Text Field"
        elif isinstance(item, PhotoFieldItem):
            name = "Photo Field"
        elif isinstance(item, RectangleItem):
            name = "Rectangle"
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
