"""Template editor view.

Provides a full-screen editing workspace similar to professional
design tools: a top toolbar, left properties panel, central
QGraphicsView canvas, right field toolbox, bottom properties
inspector, and an editor-specific status bar.
"""

import logging
import traceback

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
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

# Mapping from display name → (mapped_field, field_type) for dynamic fields.
_DYNAMIC_FIELD_DEFS: list[tuple[str, str, str]] = [
    ("Employee Name", "employee_name", "text"),
    ("Employee Designation", "employee_designation", "text"),
    ("Employee No", "employee_no", "text"),
    ("Date of Birth", "date_of_birth", "date"),
    ("CNIC", "cnic", "text"),
    ("Employee Category", "employee_category", "text"),
    ("Blood Group", "blood_group", "text"),
    ("Location", "location", "text"),
    ("Dependents", "dependents", "text"),
    ("Employee Photo", "employee_photo", "photo"),
]

_BACK_DYNAMIC_FIELD_DEFS: list[tuple[str, str, str]] = [
    ("Sr No", "sr_no", "text"),
    ("Name", "dependent_name", "text"),
    ("Relation", "relation", "text"),
    ("Date of Birth", "dependent_date_of_birth", "date"),
    ("CNIC", "dependent_cnic", "text"),
    ("Dependents Table", "__dependents_table__", "text"),
]


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
        self._current_page_side: str = "front"
        self._front_bg_info: dict[str, float | None] = {
            "pos_x": None, "pos_y": None, "width": None, "height": None,
        }
        self._back_bg_info: dict[str, float | None] = {
            "pos_x": None, "pos_y": None, "width": None, "height": None,
        }

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
        self._width_spin.setEnabled(False)
        form.addRow("Card Width:", self._width_spin)

        self._height_spin: QDoubleSpinBox = QDoubleSpinBox()
        self._height_spin.setObjectName("fieldInput")
        self._height_spin.setRange(10.0, 150.0)
        self._height_spin.setValue(CARD_HEIGHT_MM)
        self._height_spin.setSuffix(" mm")
        self._height_spin.setEnabled(False)
        form.addRow("Card Height:", self._height_spin)

        layout.addLayout(form)

        # Lock toggle
        self._size_lock_btn: QPushButton = QPushButton("🔒")
        self._size_lock_btn.setObjectName("sizeLockBtn")
        self._size_lock_btn.setCheckable(True)
        self._size_lock_btn.setChecked(True)
        self._size_lock_btn.setFixedSize(32, 28)
        self._size_lock_btn.setToolTip("Lock / Unlock card size")
        self._size_lock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        lock_row: QWidget = QWidget()
        lock_layout: QHBoxLayout = QHBoxLayout(lock_row)
        lock_layout.setContentsMargins(0, 0, 0, 0)
        lock_layout.addStretch()
        lock_layout.addWidget(self._size_lock_btn)
        layout.addWidget(lock_row)

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

        # --- Text Formatting section ---
        self._text_format_widget: QWidget = self._build_text_format_section()
        layout.addWidget(self._text_format_widget)
        self._text_format_widget.setVisible(False)

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

        # --- Dynamic Fields section ---
        layout.addWidget(self._make_section_title("Dynamic Fields"))

        self._dynamic_fields_layout = QVBoxLayout()
        layout.addLayout(self._dynamic_fields_layout)

        self._populate_dynamic_fields("front")

        layout.addSpacing(12)

        # --- Static Elements section ---
        layout.addWidget(self._make_section_title("Static Elements"))

        self._static_buttons: dict[str, QPushButton] = {}
        static_buttons: list[tuple[str, str]] = [
            ("Static Text", "static_text"),
            ("Horizontal Line", "horizontal_line"),
            ("Vertical Line", "vertical_line"),
            ("Rectangle", "rectangle"),
            ("Circle", "circle"),
            ("Image", "image"),
            ("Logo", "logo"),
        ]
        for text, action in static_buttons:
            btn = QPushButton(text)
            btn.setObjectName("fieldToolboxBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(
                lambda checked=False, a=action: self._on_static_element(a)
            )
            layout.addWidget(btn)
            self._static_buttons[text] = btn

        layout.addStretch()
        scroll.setWidget(container)

        panel_layout: QVBoxLayout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addWidget(scroll)

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
    # Text Formatting panel
    # ------------------------------------------------------------------

    def _build_text_format_section(self) -> QWidget:
        """Build the text formatting control section for the properties panel.

        Returns:
            A widget containing font, size, style, color, and alignment
            controls.  Initially hidden; shown when a ``TextFieldItem``
            is selected.
        """
        container: QWidget = QWidget()
        container.setObjectName("textFormatContainer")
        layout: QVBoxLayout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(self._make_section_title("Text Formatting"))

        # Font Family
        self._text_font_family: QComboBox = QComboBox()
        self._text_font_family.setObjectName("fieldInput")
        self._text_font_family.addItems([
            "Arial", "Calibri", "Times New Roman", "Verdana",
            "Tahoma", "Segoe UI", "Georgia", "Courier New",
            "Trebuchet MS", "Comic Sans MS",
        ])
        layout.addWidget(self._make_field_row("Font:", self._text_font_family))

        # Font Size
        self._text_font_size: QSpinBox = QSpinBox()
        self._text_font_size.setObjectName("fieldInput")
        self._text_font_size.setRange(1, 200)
        self._text_font_size.setValue(12)
        layout.addWidget(self._make_field_row("Size:", self._text_font_size))

        # Style row: Bold / Italic / Underline
        style_row: QWidget = QWidget()
        style_layout: QHBoxLayout = QHBoxLayout(style_row)
        style_layout.setContentsMargins(0, 0, 0, 0)
        style_layout.setSpacing(4)

        self._text_bold: QCheckBox = QCheckBox("B")
        self._text_bold.setObjectName("textStyleCb")
        self._text_bold.setToolTip("Bold")
        self._text_bold.setCursor(Qt.CursorShape.PointingHandCursor)

        self._text_italic: QCheckBox = QCheckBox("I")
        self._text_italic.setObjectName("textStyleCb")
        self._text_italic.setToolTip("Italic")
        self._text_italic.setCursor(Qt.CursorShape.PointingHandCursor)

        self._text_underline: QCheckBox = QCheckBox("U")
        self._text_underline.setObjectName("textStyleCb")
        self._text_underline.setToolTip("Underline")
        self._text_underline.setCursor(Qt.CursorShape.PointingHandCursor)

        style_layout.addWidget(self._text_bold)
        style_layout.addWidget(self._text_italic)
        style_layout.addWidget(self._text_underline)
        style_layout.addStretch()
        layout.addWidget(style_row)

        # Text Color
        color_row: QWidget = QWidget()
        color_layout: QHBoxLayout = QHBoxLayout(color_row)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.setSpacing(8)

        color_label: QLabel = QLabel("Color:")
        color_label.setObjectName("fieldLabel")
        color_layout.addWidget(color_label)

        self._text_color_btn: QPushButton = QPushButton()
        self._text_color_btn.setFixedSize(32, 24)
        self._text_color_btn.setToolTip("Click to change text colour")
        self._text_color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._text_color_btn.setStyleSheet(
            "background-color: #000000; border: 1px solid #ccc; border-radius: 3px;"
        )
        color_layout.addWidget(self._text_color_btn)
        color_layout.addStretch()
        layout.addWidget(color_row)

        # Alignment
        self._text_alignment: QComboBox = QComboBox()
        self._text_alignment.setObjectName("fieldInput")
        self._text_alignment.addItems(["Left", "Center", "Right"])
        layout.addWidget(self._make_field_row("Align:", self._text_alignment))

        return container

    def _get_selected_text_item(
        self,
    ) -> "TextFieldItem | None":  # noqa: F821
        """Return the first selected ``TextFieldItem``, or ``None``."""
        from views.widgets.canvas_items import TextFieldItem  # noqa: PLC0415

        selected = self._canvas.selected_canvas_items()
        for s in selected:
            if isinstance(s, TextFieldItem):
                return s
        return None

    def _populate_text_format_panel(self, item: "TextFieldItem") -> None:  # noqa: F821
        """Fill the text formatting controls from *item* without firing signals."""
        from views.widgets.canvas_items import TextFieldItem  # noqa: PLC0415

        # Block signals so population does not trigger update slots
        self._text_font_family.blockSignals(True)
        self._text_font_size.blockSignals(True)
        self._text_bold.blockSignals(True)
        self._text_italic.blockSignals(True)
        self._text_underline.blockSignals(True)
        self._text_alignment.blockSignals(True)

        self._text_font_family.setCurrentText(item.font_family)
        self._text_font_size.setValue(item.font_size)
        self._text_bold.setChecked(item.bold)
        self._text_italic.setChecked(item.italic)
        self._text_underline.setChecked(item.underline)

        align_map: dict[str, int] = {"left": 0, "center": 1, "right": 2}
        self._text_alignment.setCurrentIndex(align_map.get(item.alignment, 0))

        self._update_color_button(item.font_color)

        self._text_font_family.blockSignals(False)
        self._text_font_size.blockSignals(False)
        self._text_bold.blockSignals(False)
        self._text_italic.blockSignals(False)
        self._text_underline.blockSignals(False)
        self._text_alignment.blockSignals(False)

    def _update_color_button(self, hex_color: str) -> None:
        """Update the colour button's swatch to reflect *hex_color*."""
        self._text_color_btn.setStyleSheet(
            f"background-color: {hex_color}; border: 1px solid #ccc; border-radius: 3px;"
        )

    # ------------------------------------------------------------------
    # Text formatting signal handlers
    # ------------------------------------------------------------------

    def _on_text_font_family_changed(self, family: str) -> None:
        item = self._get_selected_text_item()
        if item is not None:
            item.font_family = family

    def _on_text_font_size_changed(self, size: int) -> None:
        item = self._get_selected_text_item()
        if item is not None:
            item.font_size = size

    def _on_text_bold_changed(self, checked: bool) -> None:
        item = self._get_selected_text_item()
        if item is not None:
            item.bold = checked

    def _on_text_italic_changed(self, checked: bool) -> None:
        item = self._get_selected_text_item()
        if item is not None:
            item.italic = checked

    def _on_text_underline_changed(self, checked: bool) -> None:
        item = self._get_selected_text_item()
        if item is not None:
            item.underline = checked

    def _on_text_alignment_changed(self, text: str) -> None:
        item = self._get_selected_text_item()
        if item is not None:
            align_map: dict[str, str] = {"Left": "left", "Center": "center", "Right": "right"}
            item.alignment = align_map.get(text, "left")

    def _on_text_color_clicked(self) -> None:
        """Open a colour picker and apply the chosen colour."""
        item = self._get_selected_text_item()
        if item is None:
            return
        initial: QColor = QColor(item.font_color)
        color: QColor = QColorDialog.getColor(initial, self, "Select Text Colour")
        if color.isValid():
            hex_color: str = color.name()
            item.font_color = hex_color
            self._update_color_button(hex_color)

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

        # Card size changes
        self._width_spin.valueChanged.connect(self._on_card_size_changed)
        self._height_spin.valueChanged.connect(self._on_card_size_changed)
        self._size_lock_btn.toggled.connect(self._on_size_lock_toggled)

        # Canvas card resize signal
        self._canvas.card_resized.connect(self._on_canvas_card_resized)

        # Text formatting controls
        self._text_font_family.currentTextChanged.connect(
            self._on_text_font_family_changed
        )
        self._text_font_size.valueChanged.connect(
            self._on_text_font_size_changed
        )
        self._text_bold.toggled.connect(self._on_text_bold_changed)
        self._text_italic.toggled.connect(self._on_text_italic_changed)
        self._text_underline.toggled.connect(self._on_text_underline_changed)
        self._text_alignment.currentTextChanged.connect(
            self._on_text_alignment_changed
        )
        self._text_color_btn.clicked.connect(self._on_text_color_clicked)

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

            # Store per-side background positions from the template
            self._front_bg_info = {
                "pos_x": template.front_bg_pos_x,
                "pos_y": template.front_bg_pos_y,
                "width": template.front_bg_width,
                "height": template.front_bg_height,
            }
            self._back_bg_info = {
                "pos_x": template.back_bg_pos_x,
                "pos_y": template.back_bg_pos_y,
                "width": template.back_bg_width,
                "height": template.back_bg_height,
            }

            # Block signals to avoid double resize during initial setup
            self._width_spin.blockSignals(True)
            self._height_spin.blockSignals(True)
            self._width_spin.setValue(template.canvas_width)
            self._height_spin.setValue(template.canvas_height)
            # Manually apply card size once
            self._canvas.resize_card(template.canvas_width, template.canvas_height)
            self._width_spin.blockSignals(False)
            self._height_spin.blockSignals(False)

            self._grid_spin.setValue(template.grid_size)
            self._snap_check.setChecked(template.snap_to_grid)
            self._canvas.set_snap_enabled(template.snap_to_grid)
            self._canvas.set_snap_size(template.grid_size)

            # Restore size lock state
            self._size_lock_btn.blockSignals(True)
            self._size_lock_btn.setChecked(template.size_locked)
            self._size_lock_btn.blockSignals(False)
            self._on_size_lock_toggled(template.size_locked)

            # Set current page side
            self._current_page_side = "front"
            print("[TRACE] Properties panel updated. Calling setCurrentIndex(0)")
            self._editor_card_side.setCurrentIndex(0)

            # Always clear old background first, then load front side.
            # Note: setCurrentIndex(0) above may NOT trigger _on_card_side_changed
            # if the index is already 0, so we must explicitly load here.
            self._canvas._clear_background()
            if self._front_image:
                self._canvas.set_background_image(
                    self._front_image,
                    pos_x_mm=template.front_bg_pos_x,
                    pos_y_mm=template.front_bg_pos_y,
                    width_mm=template.front_bg_width,
                    height_mm=template.front_bg_height,
                )

            # Load front-side fields onto canvas
            print("[TRACE] Calling load_layout(side=front)...")
            fields = self._template_ctrl.load_layout(template_id, page_side="front")
            print(f"[TRACE] load_layout returned {len(fields)} fields")
            for i, f in enumerate(fields):
                print(f"  field[{i}]: type={f.object_type} name={f.field_name} x={f.x} y={f.y} w={f.width} h={f.height}")
            print("[TRACE] Calling load_fields...")
            self._canvas.load_fields(fields)
            print("[TRACE] load_fields completed")

            # Ensure dynamic fields panel shows Front fields
            self._refresh_dynamic_fields()

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
        template.size_locked = self._size_lock_btn.isChecked()

        # Update per-side bg info from current canvas state
        current_bg = self._canvas.get_background_info()
        if self._current_page_side == "front":
            if current_bg:
                self._front_bg_info.update(current_bg)
            template.front_bg_pos_x = self._front_bg_info.get("pos_x", 0.0)
            template.front_bg_pos_y = self._front_bg_info.get("pos_y", 0.0)
            template.front_bg_width = self._front_bg_info.get("width", template.canvas_width)
            template.front_bg_height = self._front_bg_info.get("height", template.canvas_height)
        else:
            if current_bg:
                self._back_bg_info.update(current_bg)
            template.back_bg_pos_x = self._back_bg_info.get("pos_x", 0.0)
            template.back_bg_pos_y = self._back_bg_info.get("pos_y", 0.0)
            template.back_bg_width = self._back_bg_info.get("width", template.canvas_width)
            template.back_bg_height = self._back_bg_info.get("height", template.canvas_height)

        # Persist the opposite side's bg from stored info too
        if self._current_page_side == "front":
            template.back_bg_pos_x = self._back_bg_info.get("pos_x", 0.0)
            template.back_bg_pos_y = self._back_bg_info.get("pos_y", 0.0)
            template.back_bg_width = self._back_bg_info.get("width", template.canvas_width)
            template.back_bg_height = self._back_bg_info.get("height", template.canvas_height)
        else:
            template.front_bg_pos_x = self._front_bg_info.get("pos_x", 0.0)
            template.front_bg_pos_y = self._front_bg_info.get("pos_y", 0.0)
            template.front_bg_width = self._front_bg_info.get("width", template.canvas_width)
            template.front_bg_height = self._front_bg_info.get("height", template.canvas_height)

        fields = self._canvas.get_fields(self._current_template_id, self._current_page_side)

        try:
            self._template_ctrl.save_full_template(template, fields, self._current_page_side)
            QMessageBox.information(
                self, "Saved",
                f"Template '{name}' saved successfully."
            )
            logger.info("Editor saved template id=%d side=%s", self._current_template_id, self._current_page_side)
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
        elif action == "undo":
            self._canvas.undo()
        elif action == "redo":
            self._canvas.redo()
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

    def _on_card_size_changed(self) -> None:
        """React to Card Width / Height spinbox changes."""
        width_mm: float = self._width_spin.value()
        height_mm: float = self._height_spin.value()
        self._canvas.resize_card(width_mm, height_mm)

    def _on_canvas_card_resized(self) -> None:
        """Update the status bar when the canvas resizes."""
        card_w = self._canvas._card_w
        card_h = self._canvas._card_h
        self._status_size.setText(f"{card_w:.0f} × {card_h:.0f} px")

    # ------------------------------------------------------------------
    # Size lock toggle
    # ------------------------------------------------------------------

    def _on_size_lock_toggled(self, locked: bool) -> None:
        """Enable or disable the card size controls."""
        self._size_lock_btn.setText("🔒" if locked else "🔓")
        self._width_spin.setEnabled(not locked)
        self._height_spin.setEnabled(not locked)

    # ------------------------------------------------------------------
    # Toolbox button handlers
    # ------------------------------------------------------------------

    def _on_dynamic_field(
        self, display_name: str, mapped_field: str, field_type: str
    ) -> None:
        """Add a dynamic field pre-linked to a Card Generator form field.

        Args:
            display_name: Human-readable name (e.g. ``"Employee Name"``).
            mapped_field: Semantic field name (e.g. ``"employee_name"``).
            field_type: ``"text"`` or ``"photo"``.
        """
        if mapped_field == "__dependents_table__":
            self._create_dependents_table()
            return
        if field_type == "photo":
            self._canvas.add_dynamic_photo_field(mapped_field)
        else:
            self._canvas.add_dynamic_text_field(display_name, mapped_field)

    def _create_dependents_table(self) -> None:
        """Auto-create 5 pre-positioned fields forming one row template.

        The renderer repeats this row for each dependent, automatically
        calculating Y positions below the template row.
        """
        from views.widgets.canvas_items import TextFieldItem  # noqa: PLC0415

        col_defs: list[tuple[str, str, int]] = [
            ("sr_no",                "Sr No",    50),
            ("dependent_name",       "Name",    170),
            ("dependent_relation",   "Relation", 120),
            ("dependent_date_of_birth", "DOB", 120),
            ("dependent_cnic",       "CNIC",    130),
        ]

        canvas = self._canvas
        card_x: float = canvas._card_item.pos().x()
        card_y: float = canvas._card_item.pos().y()
        row_y: float = card_y + canvas._card_h * 0.35
        row_h: float = 30.0

        cx: float = card_x + 5.0
        for mapped_field, display_name, col_w in col_defs:
            item = TextFieldItem(
                cx, row_y,
                is_static=False,
                mapped_field=mapped_field,
                static_text="",
                font_family="Arial",
                font_size=10,
                font_color="#000000",
            )
            item._rect = QRectF(0, 0, float(col_w), row_h)
            item.setZValue(0)
            canvas._configure_item(item)
            cx += col_w + 3.0

    def _on_static_element(self, action: str) -> None:
        """Add a static element to the canvas.

        Args:
            action: Element type identifier.
        """
        if action == "static_text":
            self._canvas.add_static_text()
        elif action == "rectangle":
            self._canvas.add_rectangle()
        elif action == "circle":
            self._canvas.add_circle()
        elif action == "horizontal_line":
            self._canvas.add_horizontal_line()
        elif action == "vertical_line":
            self._canvas.add_vertical_line()
        elif action in ("image", "logo"):
            from PySide6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getOpenFileName(
                self, "Select Image", "",
                "Images (*.png *.jpg *.jpeg *.bmp *.gif *.svg);;All Files (*.*)"
            )
            if path:
                self._canvas.add_image_item(path)

    # ------------------------------------------------------------------
    # Dynamic fields helpers
    # ------------------------------------------------------------------

    def _clear_dynamic_fields_layout(self) -> None:
        """Remove all widget items from the dynamic fields layout."""
        if not hasattr(self, '_dynamic_fields_layout'):
            return
        while self._dynamic_fields_layout.count():
            item = self._dynamic_fields_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _populate_dynamic_fields(self, side: str) -> None:
        """Populate the dynamic fields toolbox for the given card side.

        Args:
            side: ``"front"`` or ``"back"``.
        """
        self._clear_dynamic_fields_layout()

        field_defs = (
            _DYNAMIC_FIELD_DEFS if side == "front" else _BACK_DYNAMIC_FIELD_DEFS
        )

        self._dynamic_buttons: dict[str, QPushButton] = {}
        for display_name, mapped_field, field_type in field_defs:
            btn: QPushButton = QPushButton(display_name)
            btn.setObjectName("fieldToolboxBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(
                lambda checked=False, d=display_name, m=mapped_field, ft=field_type:
                    self._on_dynamic_field(d, m, ft)
            )
            self._dynamic_fields_layout.addWidget(btn)
            self._dynamic_buttons[display_name] = btn

    def _refresh_dynamic_fields(self) -> None:
        """Refresh the dynamic fields panel to match the current card side."""
        self._populate_dynamic_fields(self._current_page_side)

    # ------------------------------------------------------------------
    # Card side switching
    # ------------------------------------------------------------------

    def _on_card_side_changed(self, index: int) -> None:
        """Switch between front and back card sides."""
        old_side: str = self._current_page_side
        new_side: str = "front" if index == 0 else "back"

        if old_side == new_side:
            return

        if self._current_template_id is None:
            self._current_page_side = new_side
            self._refresh_dynamic_fields()
            return

        # Save current side's fields and bg info before switching
        current_bg = self._canvas.get_background_info()
        if current_bg:
            if old_side == "front":
                self._front_bg_info.update(current_bg)
            else:
                self._back_bg_info.update(current_bg)

        old_fields = self._canvas.get_fields(self._current_template_id, old_side)
        try:
            self._template_ctrl.save_layout(self._current_template_id, old_fields, old_side)
        except ValueError:
            pass

        # Clear canvas and background
        self._canvas._clear_background()
        self._canvas.load_fields([])

        # Load new side background
        bg_info = self._front_bg_info if new_side == "front" else self._back_bg_info
        image = self._front_image if new_side == "front" else self._back_image
        if image:
            self._canvas.set_background_image(
                image,
                pos_x_mm=bg_info.get("pos_x"),
                pos_y_mm=bg_info.get("pos_y"),
                width_mm=bg_info.get("width"),
                height_mm=bg_info.get("height"),
            )

        # Load new side fields
        fields = self._template_ctrl.load_layout(self._current_template_id, new_side)
        self._canvas.load_fields(fields)

        self._current_page_side = new_side

        self._refresh_dynamic_fields()

    # ------------------------------------------------------------------
    # Selection display
    # ------------------------------------------------------------------

    def _on_object_selected(self, item: object) -> None:
        """Update the status bar, inspector, and text formatting panel.

        Args:
            item: The selected canvas item.
        """
        from views.widgets.canvas_items import (
            BackgroundItem,
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
            self._text_format_widget.setVisible(True)
            self._populate_text_format_panel(item)
        elif isinstance(item, PhotoFieldItem):
            name = "Photo Field"
            self._text_format_widget.setVisible(False)
        elif isinstance(item, RectangleItem):
            name = "Rectangle"
            self._text_format_widget.setVisible(False)
        elif isinstance(item, CircleItem):
            name = "Circle"
            self._text_format_widget.setVisible(False)
        elif isinstance(item, HorizontalLineItem):
            name = "Horizontal Line"
            self._text_format_widget.setVisible(False)
        elif isinstance(item, VerticalLineItem):
            name = "Vertical Line"
            self._text_format_widget.setVisible(False)
        elif isinstance(item, ImageItem):
            name = "Image"
            self._text_format_widget.setVisible(False)
        elif isinstance(item, BackgroundItem):
            name = "Background Image"
            self._text_format_widget.setVisible(False)
        elif isinstance(item, BaseCanvasItem):
            name = "Canvas Item"
            self._text_format_widget.setVisible(False)
        else:
            name = "Unknown"
            self._text_format_widget.setVisible(False)

        self._status_object.setText(f"Object: {name}")

    def _on_selection_changed(self) -> None:
        """Update UI when the scene selection changes."""
        selected = self._canvas.selected_canvas_items()
        if selected:
            self._on_object_selected(selected[-1])
        else:
            self._text_format_widget.setVisible(False)
            self._status_object.setText("Object: None")
