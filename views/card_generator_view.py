"""Card generator view.

Dual-mode (Front / Back) input form and live preview for
generating ID cards.  The left panel uses a QStackedWidget
with two completely different layouts — one for Front (employee
data) and one for Back (dependents management).

Data flow
---------
Form widgets are bound to a ``BindingManager`` via ``FormBinder``.
All user input passes through the central ``CardDataModel`` before
reaching the preview or any downstream engine.

Layout
------
+----------------------------------------------------------+
| Page Header: Card Generator + description                |
+----------------------------------+-----------------------+
| LEFT QStackedWidget              | RIGHT Live Preview    |
|                                  |                       |
| FRONT PAGE (index 0):            | [Front] [Back]        |
|  Template                        | ┌─────────────────┐  |
|  Photo                           | │   Card Preview  │  |
|  Employee Information            │ │   (stretch=1)   │  |
|    Name, Designation, ...        │ └─────────────────┘  |
|  ──────────────────────          | [Fit][100%][+][-]    |
|  [Save][DL Front][DL PDF]        | Template | Info bar  |
|  [Reset Form]                    |                       |
|                                  |                       |
| BACK PAGE (index 1):             |                       |
|  [+ Add] [Edit] [Remove] [Clear] |                       |
|  Dependents Table                |                       |
|  ──────────────────────          |                       |
|  [DL Back][DL PDF]               |                       |
|  [Reset Form]                    |                       |
+----------------------------------+-----------------------+
"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from controllers.binding_manager import BindingManager
from controllers.form_binder import FormBinder
from controllers.template_controller import TemplateController
from services.export import ExportManager
from services.export.exceptions import ExportError
from services.export.file_name_generator import FileNameGenerator
from views.preview_manager import PreviewManager
from views.widgets.large_preview_dialog import LargePreviewDialog
from views.widgets.preview_canvas import PreviewCanvas
from views.widgets.wheel_ignoring_combo import WheelIgnoringComboBox

logger = logging.getLogger(__name__)


class CardGeneratorView(QWidget):
    """Card generation workspace with Front / Back mode switching.

    The left panel contains a QStackedWidget with two completely
    different layouts — Front (employee data entry) and Back
    (dependents management).  The right panel contains the live
    preview with zoom controls and info bar.
    """

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        """Initialise the view, data model, bindings, and preview."""
        super().__init__()
        self.setObjectName("cardGeneratorView")

        self._photo_path: str = ""
        self._active_side: str = "front"
        self._editing_dep_index: int | None = None

        # Template data access
        self._template_ctrl: TemplateController = TemplateController()

        # Central data management (created before UI to avoid late init)
        self._binding_manager: BindingManager = BindingManager(self)

        # Must be initialized before _setup_ui() because _build_front_fields
        # appends QLineEdit widgets to this list during UI construction.
        self._field_inputs: list[QLineEdit] = []

        self._setup_ui()

        # Populate template dropdown from database
        self._populate_template_combo()

        # Bind form widgets to the data model
        self._form_binder: FormBinder = FormBinder(self._binding_manager)
        self._bind_form_widgets()

        # Preview engine — consumes data model signals
        self._preview_manager: PreviewManager = PreviewManager(
            self._front_preview, self._back_preview
        )
        self._preview_manager.connect_binding_manager(self._binding_manager)

        # Export engine — high-resolution at EXPORT_DPI
        from config.constants import EXPORT_DPI  # noqa: PLC0415
        self._export_manager: ExportManager = ExportManager(
            self._binding_manager, TemplateController(), dpi=EXPORT_DPI
        )
        self._wire_download_buttons()

        # Track whether an export is in progress
        self._export_in_progress: bool = False

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Build the complete page layout."""
        root: QVBoxLayout = QVBoxLayout(self)
        root.setContentsMargins(24, 0, 24, 0)
        root.setSpacing(0)

        # --- Title & description ---
        header_widget: QWidget = QWidget()
        header_layout: QVBoxLayout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 20, 0, 0)
        header_layout.setSpacing(4)

        title: QLabel = QLabel("Card Generator")
        title.setObjectName("viewTitle")
        header_layout.addWidget(title)

        description: QLabel = QLabel(
            "Fill in the cardholder details below.  "
            "Switch between Front and Back to edit each side."
        )
        description.setObjectName("viewDescription")
        description.setWordWrap(True)
        header_layout.addWidget(description)
        root.addWidget(header_widget)

        # --- Body (splitter: left stack | preview) ---
        body: QWidget = QWidget()
        body.setObjectName("viewContent")
        body_layout: QVBoxLayout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)

        splitter: QSplitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_preview_panel())

        splitter.setStretchFactor(0, 35)
        splitter.setStretchFactor(1, 65)
        splitter.setSizes([350, 650])

        body_layout.addWidget(splitter)
        root.addWidget(body, stretch=1)

    # ------------------------------------------------------------------
    # Left panel (QStackedWidget: Front page / Back page)
    # ------------------------------------------------------------------

    def _build_left_panel(self) -> QWidget:
        """Construct the left panel with a stacked layout.

        The stack switches between Front (employee data) and Back
        (dependents management).  Each page has its own scroll area
        and a fixed action bar below it.

        Returns:
            A widget containing a scroll area with a QStackedWidget
            and mode-specific action bars.
        """
        panel: QWidget = QWidget()
        panel.setObjectName("leftPanel")

        layout: QVBoxLayout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Scroll area wrapping the stack ---
        scroll: QScrollArea = QScrollArea()
        scroll.setObjectName("formScroll")
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(280)

        container: QWidget = QWidget()
        container.setObjectName("formContainer")
        container_layout: QVBoxLayout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        self._left_stack: QStackedWidget = QStackedWidget()
        self._left_stack.addWidget(self._build_front_content())  # index 0
        self._left_stack.addWidget(self._build_back_content())   # index 1
        self._left_stack.setCurrentIndex(0)

        container_layout.addWidget(self._left_stack)
        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

        # --- Action bars (always visible below scroll) ---
        self._front_action_bar = self._build_front_action_bar()
        self._back_action_bar = self._build_back_action_bar()
        self._back_action_bar.setVisible(False)
        layout.addWidget(self._front_action_bar)
        layout.addWidget(self._back_action_bar)

        return panel

    def _build_front_content(self) -> QWidget:
        """Build the Front page content.

        Returns:
            A widget with Template, Photo, and Employee Information
            fields in a vertical layout.
        """
        widget: QWidget = QWidget()
        layout: QVBoxLayout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # -- Template --
        template_label: QLabel = QLabel("Template")
        template_label.setObjectName("formSectionTitle")
        layout.addWidget(template_label)

        self._template_combo = WheelIgnoringComboBox()
        self._template_combo.setObjectName("fieldInput")
        self._template_combo.addItem("-- Select Template --", 0)
        layout.addWidget(self._template_combo)

        # -- Photo --
        layout.addWidget(self._build_photo_section())

        # -- Employee Information --
        self._side_indicator_front: QLabel = QLabel("Employee Information")
        self._side_indicator_front.setObjectName("formSectionTitle")
        layout.addWidget(self._side_indicator_front)

        fields: QFormLayout = self._build_front_fields()
        layout.addLayout(fields)

        layout.addStretch()
        return widget

    def _build_back_content(self) -> QWidget:
        """Build the Back page content.

        Returns:
            A widget with dependents management heading, action
            buttons, inline form, and the dependents table.
        """
        widget: QWidget = QWidget()
        layout: QVBoxLayout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # -- Heading --
        heading_row: QWidget = QWidget()
        heading_layout: QHBoxLayout = QHBoxLayout(heading_row)
        heading_layout.setContentsMargins(0, 0, 0, 0)

        heading: QLabel = QLabel("Dependent Management")
        heading.setObjectName("formSectionTitle")
        heading_layout.addWidget(heading)
        heading_layout.addStretch()

        self._dependents_count: QLabel = QLabel("0 dependents")
        self._dependents_count.setObjectName("infoLabel")
        heading_layout.addWidget(self._dependents_count)
        layout.addWidget(heading_row)

        # -- Management buttons --
        btn_row: QWidget = QWidget()
        btn_layout: QHBoxLayout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)

        self._add_dep_btn = QPushButton("\u2795 Add")
        self._add_dep_btn.setObjectName("actionButton")
        self._add_dep_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_dep_btn.setToolTip("Add a new dependent record")
        self._add_dep_btn.clicked.connect(self._on_add_dependent)
        btn_layout.addWidget(self._add_dep_btn)

        self._edit_dep_btn = QPushButton("\u270f Edit")
        self._edit_dep_btn.setObjectName("actionButton")
        self._edit_dep_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._edit_dep_btn.setToolTip("Edit the selected dependent")
        self._edit_dep_btn.clicked.connect(self._on_edit_dependent)
        btn_layout.addWidget(self._edit_dep_btn)

        self._remove_dep_btn = QPushButton("\u2716 Remove")
        self._remove_dep_btn.setObjectName("actionButton")
        self._remove_dep_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._remove_dep_btn.setToolTip("Remove the selected dependent")
        self._remove_dep_btn.clicked.connect(self._on_remove_dependent)
        btn_layout.addWidget(self._remove_dep_btn)

        self._clear_all_btn = QPushButton("\U0001F9F9 Clear All")
        self._clear_all_btn.setObjectName("actionButton")
        self._clear_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_all_btn.setToolTip("Remove all dependents")
        self._clear_all_btn.clicked.connect(self._on_clear_all_dependents)
        btn_layout.addWidget(self._clear_all_btn)

        btn_layout.addStretch()
        layout.addWidget(btn_row)

        # -- Inline add/edit form (hidden by default) --
        self._dep_form_widget = QWidget()
        self._dep_form_widget.setObjectName("dependentForm")
        self._dep_form_widget.setVisible(False)

        dep_form_layout: QHBoxLayout = QHBoxLayout(self._dep_form_widget)
        dep_form_layout.setContentsMargins(0, 0, 0, 0)
        dep_form_layout.setSpacing(8)

        self._dep_name_input = QLineEdit()
        self._dep_name_input.setObjectName("fieldInput")
        self._dep_name_input.setPlaceholderText("Name")
        dep_form_layout.addWidget(self._dep_name_input)

        self._dep_relation_input = QLineEdit()
        self._dep_relation_input.setObjectName("fieldInput")
        self._dep_relation_input.setPlaceholderText("Relation")
        dep_form_layout.addWidget(self._dep_relation_input)

        self._dep_dob_input = QLineEdit()
        self._dep_dob_input.setObjectName("fieldInput")
        self._dep_dob_input.setPlaceholderText("Date of Birth")
        dep_form_layout.addWidget(self._dep_dob_input)

        self._dep_cnic_input = QLineEdit()
        self._dep_cnic_input.setObjectName("fieldInput")
        self._dep_cnic_input.setPlaceholderText("CNIC")
        dep_form_layout.addWidget(self._dep_cnic_input)

        self._dep_save_btn: QPushButton = QPushButton("Save")
        self._dep_save_btn.setObjectName("actionButton")
        self._dep_save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dep_save_btn.clicked.connect(self._on_save_dependent)
        dep_form_layout.addWidget(self._dep_save_btn)

        self._dep_cancel_btn: QPushButton = QPushButton("Cancel")
        self._dep_cancel_btn.setObjectName("actionButton")
        self._dep_cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dep_cancel_btn.clicked.connect(self._on_cancel_dependent)
        dep_form_layout.addWidget(self._dep_cancel_btn)

        layout.addWidget(self._dep_form_widget)

        # -- Dependents table --
        self._dependents_table: QTableWidget = QTableWidget()
        self._dependents_table.setObjectName("dependentsTable")
        self._dependents_table.setColumnCount(5)
        self._dependents_table.setHorizontalHeaderLabels(
            ["Sr#", "Name", "Relation", "Date of Birth", "CNIC"]
        )
        self._dependents_table.horizontalHeader().setStretchLastSection(True)
        self._dependents_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._dependents_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._dependents_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._dependents_table.setMinimumHeight(100)
        layout.addWidget(self._dependents_table, stretch=1)

        return widget

    def _build_front_action_bar(self) -> QWidget:
        """Build the fixed action bar for Front mode.

        Returns:
            A widget with Save, Download Front, Download PDF, and
            Reset Form buttons.
        """
        bar: QWidget = QWidget()
        bar.setObjectName("frontActionBar")

        layout: QHBoxLayout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 12, 20, 14)
        layout.setSpacing(8)

        self._save_btn = QPushButton("Save")
        self._save_btn.setObjectName("actionButton")
        self._save_btn.setEnabled(False)
        self._save_btn.setToolTip("Save the current card to history (coming soon)")
        layout.addWidget(self._save_btn)

        self._dl_front_btn = QPushButton("Download Front")
        self._dl_front_btn.setObjectName("actionButton")
        self._dl_front_btn.setEnabled(False)
        self._dl_front_btn.setToolTip("Export the front card as PNG or JPEG")
        layout.addWidget(self._dl_front_btn)

        self._dl_pdf_btn = QPushButton("Download PDF")
        self._dl_pdf_btn.setObjectName("actionButton")
        self._dl_pdf_btn.setEnabled(False)
        self._dl_pdf_btn.setToolTip("Export the combined front + back PDF")
        layout.addWidget(self._dl_pdf_btn)

        layout.addStretch()

        reset_front: QPushButton = QPushButton("Reset Form")
        reset_front.setObjectName("actionButton")
        reset_front.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_front.setToolTip("Reset all form fields to their default values")
        reset_front.clicked.connect(self._on_clear_form)
        layout.addWidget(reset_front)

        return bar

    def _build_back_action_bar(self) -> QWidget:
        """Build the fixed action bar for Back mode.

        Returns:
            A widget with Download Back, Download PDF, and Reset Form
            buttons.
        """
        bar: QWidget = QWidget()
        bar.setObjectName("backActionBar")

        layout: QHBoxLayout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 12, 20, 14)
        layout.setSpacing(8)

        self._dl_back_btn = QPushButton("Download Back")
        self._dl_back_btn.setObjectName("actionButton")
        self._dl_back_btn.setEnabled(False)
        self._dl_back_btn.setToolTip("Export the back card as PNG or JPEG")
        layout.addWidget(self._dl_back_btn)

        self._dl_pdf_back_btn = QPushButton("Download PDF")
        self._dl_pdf_back_btn.setObjectName("actionButton")
        self._dl_pdf_back_btn.setEnabled(False)
        self._dl_pdf_back_btn.setToolTip("Export the combined front + back PDF")
        layout.addWidget(self._dl_pdf_back_btn)

        layout.addStretch()

        reset_back: QPushButton = QPushButton("Reset Form")
        reset_back.setObjectName("actionButton")
        reset_back.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_back.setToolTip("Reset dependent form fields")
        reset_back.clicked.connect(self._on_reset_form)
        layout.addWidget(reset_back)

        return bar

    # ------------------------------------------------------------------
    # Front form
    # ------------------------------------------------------------------

    def _build_front_fields(self) -> QFormLayout:
        """Build the Front-side labelled input fields.

        Returns:
            A QFormLayout containing all 9 front fields:
            Employee Name, Employee Designation, Employee No,
            Date of Birth, CNIC, Employee Category, Blood Group,
            Location, and Dependents.
        """
        layout: QFormLayout = QFormLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self._name_input = QLineEdit()
        self._name_input.setObjectName("fieldInput")
        self._name_input.setPlaceholderText("e.g. John Doe")
        self._name_input.setToolTip("Employee full name (required)")
        layout.addRow("Employee Name:", self._name_input)
        self._field_inputs.append(self._name_input)

        self._designation_input = QLineEdit()
        self._designation_input.setObjectName("fieldInput")
        self._designation_input.setPlaceholderText("e.g. Software Engineer")
        self._designation_input.setToolTip("Employee designation (required)")
        layout.addRow("Employee Designation:", self._designation_input)
        self._field_inputs.append(self._designation_input)

        self._emp_no_input = QLineEdit()
        self._emp_no_input.setObjectName("fieldInput")
        self._emp_no_input.setPlaceholderText("e.g. EMP-001")
        self._emp_no_input.setToolTip("Employee number (required)")
        layout.addRow("Employee No:", self._emp_no_input)
        self._field_inputs.append(self._emp_no_input)

        self._dob_input = QLineEdit()
        self._dob_input.setObjectName("fieldInput")
        self._dob_input.setPlaceholderText("e.g. 15-08-1990")
        self._dob_input.setToolTip("Date of birth")
        layout.addRow("Date of Birth:", self._dob_input)

        self._cnic_input = QLineEdit()
        self._cnic_input.setObjectName("fieldInput")
        self._cnic_input.setPlaceholderText("e.g. 12345-6789012-3")
        self._cnic_input.setToolTip("CNIC number")
        layout.addRow("CNIC:", self._cnic_input)

        self._category_input = QLineEdit()
        self._category_input.setObjectName("fieldInput")
        self._category_input.setPlaceholderText("e.g. Permanent")
        self._category_input.setToolTip("Employee category (required)")
        layout.addRow("Employee Category:", self._category_input)
        self._field_inputs.append(self._category_input)

        self._blood_group_input = QLineEdit()
        self._blood_group_input.setObjectName("fieldInput")
        self._blood_group_input.setPlaceholderText("e.g. A+")
        self._blood_group_input.setToolTip("Blood group")
        layout.addRow("Blood Group:", self._blood_group_input)

        self._location_input = QLineEdit()
        self._location_input.setObjectName("fieldInput")
        self._location_input.setPlaceholderText("e.g. Head Office")
        self._location_input.setToolTip("Location (required)")
        layout.addRow("Location:", self._location_input)
        self._field_inputs.append(self._location_input)

        self._dependents_front_input = QLineEdit()
        self._dependents_front_input.setObjectName("fieldInput")
        self._dependents_front_input.setPlaceholderText("e.g. Self, Spouse, 2 Children")
        self._dependents_front_input.setToolTip("Dependents information")
        layout.addRow("Dependents:", self._dependents_front_input)

        return layout

    # ------------------------------------------------------------------
    # Photo section
    # ------------------------------------------------------------------

    def _build_photo_section(self) -> QWidget:
        """Build the photo selection area.

        Returns:
            A widget with a photo placeholder and a ``Choose Photo`` button.
        """
        section: QWidget = QWidget()
        section.setObjectName("photoSection")

        p_layout: QVBoxLayout = QVBoxLayout(section)
        p_layout.setContentsMargins(0, 0, 0, 0)
        p_layout.setSpacing(8)

        heading: QLabel = QLabel("Photo")
        heading.setObjectName("formSectionTitle")
        p_layout.addWidget(heading)

        self._photo_label: QLabel = QLabel()
        self._photo_label.setObjectName("photoPlaceholder")
        self._photo_label.setFixedSize(120, 120)
        self._photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._photo_label.setText("No photo\nselected")
        p_layout.addWidget(self._photo_label)

        choose_btn: QPushButton = QPushButton("Choose Photo")
        choose_btn.setObjectName("photoButton")
        choose_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        choose_btn.setToolTip("Select a photo for the card")
        choose_btn.clicked.connect(self._on_choose_photo)
        p_layout.addWidget(choose_btn)

        return section

    # ------------------------------------------------------------------
    # Preview panel (right)
    # ------------------------------------------------------------------

    def _build_preview_panel(self) -> QWidget:
        """Construct the live preview area (right panel).

        Returns:
            A widget containing front/back toggle tabs, preview
            canvases, zoom controls, and info bar.
        """
        panel: QWidget = QWidget()
        panel.setObjectName("previewPanel")
        panel.setMinimumWidth(380)

        layout: QVBoxLayout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # --- Preview title row with side tabs ---
        title_row: QWidget = QWidget()
        title_row_layout: QHBoxLayout = QHBoxLayout(title_row)
        title_row_layout.setContentsMargins(0, 0, 0, 0)
        title_row_layout.setSpacing(6)

        heading: QLabel = QLabel("Live Preview")
        heading.setObjectName("previewTitle")
        title_row_layout.addWidget(heading)

        title_row_layout.addStretch()

        self._side_tab_group: QButtonGroup = QButtonGroup(self)
        self._front_tab_btn: QPushButton = QPushButton("Front")
        self._front_tab_btn.setObjectName("sideTabBtn")
        self._front_tab_btn.setCheckable(True)
        self._front_tab_btn.setChecked(True)
        self._front_tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._side_tab_group.addButton(self._front_tab_btn, 0)

        self._back_tab_btn: QPushButton = QPushButton("Back")
        self._back_tab_btn.setObjectName("sideTabBtn")
        self._back_tab_btn.setCheckable(True)
        self._back_tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._side_tab_group.addButton(self._back_tab_btn, 1)

        title_row_layout.addWidget(self._front_tab_btn)
        title_row_layout.addWidget(self._back_tab_btn)

        expand_btn: QPushButton = QPushButton("Expand")
        expand_btn.setObjectName("previewToolBtn")
        expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        expand_btn.setToolTip("Open a larger preview window")
        expand_btn.clicked.connect(self._on_expand_preview)
        title_row_layout.addWidget(expand_btn)

        layout.addWidget(title_row)

        # --- Card preview canvases (stacked, only one visible) ---
        self._preview_stack: QStackedWidget = QStackedWidget()
        self._front_preview: PreviewCanvas = PreviewCanvas("")
        self._front_preview.set_placeholder("No Front Template Selected")
        self._preview_stack.addWidget(self._front_preview)

        self._back_preview: PreviewCanvas = PreviewCanvas("")
        self._back_preview.set_placeholder("No Back Template Selected")
        self._preview_stack.addWidget(self._back_preview)

        self._preview_stack.setCurrentIndex(0)
        layout.addWidget(self._preview_stack, stretch=1)

        self._side_tab_group.idClicked.connect(self._on_side_changed)

        # --- Zoom controls ---
        layout.addWidget(self._build_zoom_controls())

        # --- Information bar ---
        layout.addWidget(self._build_info_bar())

        return panel

    def _build_zoom_controls(self) -> QWidget:
        """Construct the zoom control bar for the preview.

        Returns:
            A widget with Fit to Screen, 100%, Zoom In, and Zoom Out buttons.
        """
        bar: QWidget = QWidget()
        bar.setObjectName("zoomToolbar")

        layout: QHBoxLayout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        fit_btn: QPushButton = QPushButton("Fit to Screen")
        fit_btn.setObjectName("zoomBtn")
        fit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fit_btn.setToolTip("Scale the preview to fit the viewport")
        fit_btn.clicked.connect(self._on_zoom_fit)
        layout.addWidget(fit_btn)

        reset_btn: QPushButton = QPushButton("100%")
        reset_btn.setObjectName("zoomBtn")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setToolTip("Reset zoom to 100%")
        reset_btn.clicked.connect(self._on_zoom_reset)
        layout.addWidget(reset_btn)

        zoom_in_btn: QPushButton = QPushButton("+")
        zoom_in_btn.setObjectName("zoomBtn")
        zoom_in_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        zoom_in_btn.setToolTip("Zoom in")
        zoom_in_btn.setFixedWidth(32)
        zoom_in_btn.clicked.connect(self._on_zoom_in)
        layout.addWidget(zoom_in_btn)

        zoom_out_btn: QPushButton = QPushButton("\u2212")
        zoom_out_btn.setObjectName("zoomBtn")
        zoom_out_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        zoom_out_btn.setToolTip("Zoom out")
        zoom_out_btn.setFixedWidth(32)
        zoom_out_btn.clicked.connect(self._on_zoom_out)
        layout.addWidget(zoom_out_btn)

        layout.addStretch()
        return bar

    def _on_zoom_fit(self) -> None:
        """Fit the active preview to the viewport."""
        self._active_preview().fit_to_window()

    def _on_zoom_reset(self) -> None:
        """Reset the active preview zoom to 100%."""
        self._active_preview().reset_zoom()

    def _on_zoom_in(self) -> None:
        """Zoom in on the active preview."""
        self._active_preview().zoom_in()

    def _on_zoom_out(self) -> None:
        """Zoom out on the active preview."""
        self._active_preview().zoom_out()

    def _active_preview(self) -> PreviewCanvas:
        """Return the currently visible preview canvas.

        Returns:
            The active PreviewCanvas based on the current side.
        """
        return self._front_preview if self._active_side == "front" else self._back_preview

    def _build_info_bar(self) -> QWidget:
        """Build the bottom information strip.

        Returns:
            A widget showing selected template, image size, card
            dimensions and preview status.
        """
        bar: QWidget = QWidget()
        bar.setObjectName("infoBar")

        b_layout: QHBoxLayout = QHBoxLayout(bar)
        b_layout.setContentsMargins(10, 6, 10, 6)
        b_layout.setSpacing(12)

        self._info_template: QLabel = QLabel("Template: None")
        self._info_template.setObjectName("infoLabel")
        b_layout.addWidget(self._info_template)

        self._info_image: QLabel = QLabel("Image: --")
        self._info_image.setObjectName("infoLabel")
        b_layout.addWidget(self._info_image)

        self._info_card: QLabel = QLabel("Card: 85.6 \u00d7 54.0 mm")
        self._info_card.setObjectName("infoLabel")
        b_layout.addWidget(self._info_card)

        self._info_dpi: QLabel = QLabel("Export DPI: 600")
        self._info_dpi.setObjectName("infoLabel")
        b_layout.addWidget(self._info_dpi)

        self._info_status: QLabel = QLabel("Status: Idle")
        self._info_status.setObjectName("infoLabel")
        b_layout.addWidget(self._info_status)

        b_layout.addStretch()
        return bar



    # ------------------------------------------------------------------
    # Form bindings
    # ------------------------------------------------------------------

    def _bind_form_widgets(self) -> None:
        """Connect every form widget to the ``BindingManager``."""
        # --- Front fields ---
        self._form_binder.bind_text_field(self._name_input, "employee_name")

        # Employee Designation — uses new key, backward compat with old "designation"
        self._form_binder.bind_text_field(
            self._designation_input, "employee_designation"
        )
        self._designation_input.textChanged.connect(
            lambda value: self._binding_manager.set_field("designation", value)  # noqa: B023
        )

        self._form_binder.bind_text_field(self._emp_no_input, "employee_no")
        self._form_binder.bind_text_field(self._dob_input, "date_of_birth")
        self._form_binder.bind_text_field(self._cnic_input, "cnic")
        self._form_binder.bind_text_field(
            self._category_input, "employee_category"
        )
        self._form_binder.bind_text_field(self._blood_group_input, "blood_group")
        self._form_binder.bind_text_field(self._location_input, "location")

        # Dependents — uses new key, backward compat with old "dependence"
        self._form_binder.bind_text_field(
            self._dependents_front_input, "dependents"
        )
        self._dependents_front_input.textChanged.connect(
            lambda value: self._binding_manager.set_field("dependence", value)  # noqa: B023
        )

        self._form_binder.bind_template_combo(self._template_combo)

    # ------------------------------------------------------------------
    # Side switching
    # ------------------------------------------------------------------

    def _on_side_changed(self, tab_id: int) -> None:
        """Switch between Front and Back mode.

        Updates the form stack, preview visibility, and side indicator.

        Args:
            tab_id: ``0`` for Front, ``1`` for Back.
        """
        self._active_side = "front" if tab_id == 0 else "back"
        is_front: bool = self._active_side == "front"
        self._preview_stack.setCurrentIndex(0 if is_front else 1)
        self._left_stack.setCurrentIndex(0 if is_front else 1)
        self._front_action_bar.setVisible(is_front)
        self._back_action_bar.setVisible(not is_front)

    # ------------------------------------------------------------------
    # Dependents management
    # ------------------------------------------------------------------

    def _on_add_dependent(self) -> None:
        """Show the inline form to add a new dependent."""
        self._editing_dep_index = None
        self._dep_form_widget.setVisible(True)
        self._add_dep_btn.setEnabled(False)
        self._dep_name_input.setFocus()

    def _on_save_dependent(self) -> None:
        """Save (add or update) the dependent and refresh everything."""
        name: str = self._dep_name_input.text().strip()
        relation: str = self._dep_relation_input.text().strip()
        dob: str = self._dep_dob_input.text().strip()
        cnic: str = self._dep_cnic_input.text().strip()

        if not name:
            QMessageBox.warning(
                self, "Validation Error",
                "Dependent name is required.",
            )
            self._dep_name_input.setFocus()
            return

        dependent: dict = {
            "name": name,
            "relation": relation,
            "date_of_birth": dob,
            "cnic": cnic,
        }

        if self._editing_dep_index is not None:
            self._binding_manager.update_dependent(
                self._editing_dep_index, dependent
            )
        else:
            self._binding_manager.add_dependent(dependent)

        self._editing_dep_index = None
        self._refresh_dependents_table()
        self._clear_dependent_form()
        self._dep_form_widget.setVisible(False)
        self._add_dep_btn.setEnabled(True)
        self._dep_name_input.setFocus()

    def _on_cancel_dependent(self) -> None:
        """Cancel adding/editing and hide the form."""
        self._editing_dep_index = None
        self._clear_dependent_form()
        self._dep_form_widget.setVisible(False)
        self._add_dep_btn.setEnabled(True)

    def _on_edit_dependent(self) -> None:
        """Load the selected row into the form for editing."""
        rows: set[int] = {
            r.row()
            for r in self._dependents_table.selectedIndexes()
        }
        if not rows:
            QMessageBox.information(
                self, "No Selection",
                "Please select a dependent first.",
            )
            return

        index: int = rows.pop()
        deps: list[dict] = self._binding_manager.model.dependents
        if index < 0 or index >= len(deps):
            return

        dep: dict = deps[index]
        self._dep_name_input.setText(dep.get("name", ""))
        self._dep_relation_input.setText(dep.get("relation", ""))
        self._dep_dob_input.setText(dep.get("date_of_birth", ""))
        self._dep_cnic_input.setText(dep.get("cnic", ""))

        self._editing_dep_index = index
        self._dep_form_widget.setVisible(True)
        self._add_dep_btn.setEnabled(False)
        self._dep_name_input.setFocus()

    def _on_remove_dependent(self) -> None:
        """Remove the selected dependent and renumber."""
        rows: set[int] = {
            r.row()
            for r in self._dependents_table.selectedIndexes()
        }
        if not rows:
            QMessageBox.information(
                self, "No Selection",
                "Please select a dependent first.",
            )
            return

        index: int = rows.pop()
        deps: list[dict] = self._binding_manager.model.dependents
        if index < 0 or index >= len(deps):
            return

        self._binding_manager.remove_dependent(index)
        self._refresh_dependents_table()

        if self._editing_dep_index is not None:
            if self._editing_dep_index == index:
                self._editing_dep_index = None
                self._clear_dependent_form()
                self._dep_form_widget.setVisible(False)
                self._add_dep_btn.setEnabled(True)
            elif self._editing_dep_index > index:
                self._editing_dep_index -= 1

    def _on_clear_all_dependents(self) -> None:
        """Remove all dependents after confirmation."""
        deps: list[dict] = self._binding_manager.model.dependents
        if not deps:
            return

        reply: QMessageBox.StandardButton = QMessageBox.question(
            self,
            "Clear All Dependents",
            "Are you sure you want to remove all dependents?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._binding_manager.clear_dependents()
        self._refresh_dependents_table()
        self._editing_dep_index = None
        self._clear_dependent_form()
        self._dep_form_widget.setVisible(False)
        self._add_dep_btn.setEnabled(True)

    def _on_reset_form(self) -> None:
        """Clear input fields only, keep dependents unchanged."""
        self._clear_dependent_form()
        self._dep_name_input.setFocus()

    def _clear_dependent_form(self) -> None:
        """Clear all fields in the dependent form."""
        self._dep_name_input.clear()
        self._dep_relation_input.clear()
        self._dep_dob_input.clear()
        self._dep_cnic_input.clear()

    def _refresh_dependents_table(self) -> None:
        """Rebuild the dependents table from the data model."""
        deps: list[dict] = self._binding_manager.model.dependents
        self._dependents_table.setRowCount(len(deps))
        for i, dep in enumerate(deps):
            self._dependents_table.setItem(
                i, 0, QTableWidgetItem(str(i + 1))
            )
            self._dependents_table.setItem(
                i, 1, QTableWidgetItem(dep.get("name", ""))
            )
            self._dependents_table.setItem(
                i, 2, QTableWidgetItem(dep.get("relation", ""))
            )
            self._dependents_table.setItem(
                i, 3, QTableWidgetItem(dep.get("date_of_birth", ""))
            )
            self._dependents_table.setItem(
                i, 4, QTableWidgetItem(dep.get("cnic", ""))
            )
        self._dependents_count.setText(f"{len(deps)} dependent{'s' if len(deps) != 1 else ''}")

    # ------------------------------------------------------------------
    # Expand preview
    # ------------------------------------------------------------------

    def _on_expand_preview(self) -> None:
        """Open the large preview dialog with the current card image."""
        dialog: LargePreviewDialog = LargePreviewDialog(self)

        if self._active_side == "front":
            pixmap: QPixmap = self._front_preview.current_pixmap()
            if pixmap.isNull():
                dialog.set_placeholder("No Front Template Selected")
            else:
                dialog.set_pixmap(pixmap)
        else:
            pixmap = self._back_preview.current_pixmap()
            if pixmap.isNull():
                dialog.set_placeholder("No Back Template Selected")
            else:
                dialog.set_pixmap(pixmap)

        dialog.exec()

    # ------------------------------------------------------------------
    # Export workflow
    # ------------------------------------------------------------------

    def _wire_download_buttons(self) -> None:
        """Connect download and save buttons to the export workflow."""
        self._dl_front_btn.setEnabled(True)
        self._dl_front_btn.clicked.connect(
            lambda: self._on_download("front")
        )

        self._dl_back_btn.setEnabled(True)
        self._dl_back_btn.clicked.connect(
            lambda: self._on_download("back")
        )

        self._dl_pdf_btn.setEnabled(True)
        self._dl_pdf_btn.clicked.connect(
            lambda: self._on_download("combined")
        )

        self._dl_pdf_back_btn.setEnabled(True)
        self._dl_pdf_back_btn.clicked.connect(
            lambda: self._on_download("combined")
        )

    # ------------------------------------------------------------------
    # Template dropdown population
    # ------------------------------------------------------------------

    def _populate_template_combo(self) -> None:
        """Load all templates from the database into the template combo.

        Preserves the current selection if it still exists.
        """
        current_id: int = self._template_combo.currentData() or 0
        self._template_combo.blockSignals(True)
        self._template_combo.clear()
        self._template_combo.addItem("-- Select Template --", 0)

        try:
            templates = self._template_ctrl.get_all_templates()
            for tpl in templates:
                self._template_combo.addItem(tpl.template_name, tpl.id)
        except Exception:
            logger.exception("Failed to populate template combo")

        if current_id > 0:
            idx: int = self._template_combo.findData(current_id)
            if idx >= 0:
                self._template_combo.setCurrentIndex(idx)
        self._template_combo.blockSignals(False)

    def showEvent(self, event) -> None:  # noqa: N802
        """Refresh the template dropdown every time the page becomes visible."""
        super().showEvent(event)
        self._populate_template_combo()

    # ------------------------------------------------------------------
    # Download / Export
    # ------------------------------------------------------------------

    def _on_download(self, mode: str) -> None:
        """Open a save dialog, export the card, and show the result.

        Validates required fields before export, shows a progress
        dialog, and prevents duplicate clicks while exporting.

        Args:
            mode: ``"front"``, ``"back"``, or ``"combined"``.
        """
        errors: list[str] = self._validate_form()
        if errors:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please fix the following before exporting:\n\n"
                + "\n".join(f"\u2022 {e}" for e in errors),
            )
            return

        self._set_export_buttons_enabled(False)
        self._export_in_progress = True

        progress: QProgressDialog = QProgressDialog(
            "Exporting card...", "Cancel", 0, 0, self,
        )
        progress.setWindowTitle("Exporting")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.canceled.connect(lambda: None)
        progress.show()

        try:
            self._info_status.setText("Status: Exporting...")
            logger.info("Export started: mode=%s", mode)

            while True:
                path: str | None = self._get_export_path(mode)
                if not path:
                    break

                try:
                    if mode == "combined":
                        result: str = self._export_manager.export_combined_pdf(
                            path
                        )
                    elif mode == "front":
                        result = self._export_manager.export_front(path)
                    else:
                        result = self._export_manager.export_back(path)

                    logger.info(
                        "Export completed: mode=%s path=%s", mode, result
                    )
                    if not self._show_export_success(result):
                        break

                except ExportError as exc:
                    logger.warning("Export failed: %s", exc)
                    QMessageBox.warning(
                        self, "Export Failed", str(exc)
                    )
                    break

            self._info_status.setText("Status: Idle")

        except Exception as exc:
            logger.exception("Unexpected export error")
            QMessageBox.warning(
                self, "Export Error",
                f"An unexpected error occurred:\n{exc}",
            )
        finally:
            progress.close()
            self._export_in_progress = False
            self._set_export_buttons_enabled(True)

    def _set_export_buttons_enabled(self, enabled: bool) -> None:
        """Enable or disable all export-related buttons.

        Args:
            enabled: ``True`` to enable, ``False`` to disable.
        """
        self._dl_front_btn.setEnabled(enabled)
        self._dl_back_btn.setEnabled(enabled)
        self._dl_pdf_btn.setEnabled(enabled)
        self._dl_pdf_back_btn.setEnabled(enabled)
        self._save_btn.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_form(self) -> list[str]:
        """Check that all required fields are filled before export.

        Validates all front fields plus template and photo regardless
        of which side is currently active, since export needs data
        from both sides.

        Returns:
            A list of user-friendly error messages (empty = valid).
        """
        errors: list[str] = []
        self._clear_field_highlights()

        if not self._name_input.text().strip():
            errors.append("Employee Name is required")
            self._highlight_field(self._name_input)

        if not self._designation_input.text().strip():
            errors.append("Employee Designation is required")
            self._highlight_field(self._designation_input)

        if not self._emp_no_input.text().strip():
            errors.append("Employee No is required")
            self._highlight_field(self._emp_no_input)

        if not self._category_input.text().strip():
            errors.append("Employee Category is required")
            self._highlight_field(self._category_input)

        if not self._location_input.text().strip():
            errors.append("Location is required")
            self._highlight_field(self._location_input)

        if self._template_combo.currentIndex() <= 0:
            errors.append("Please select a template")

        if not self._photo_path:
            errors.append("Please select a photo")

        if errors:
            self._info_status.setText("Status: Validation Failed")
            logger.info("Form validation failed: %s", errors)

        return errors

    def _highlight_field(self, field: QWidget) -> None:
        """Apply a red border to indicate an invalid field.

        Uses a dynamic property so the stylesheet rule
        ``#fieldInput[invalid="true"]`` can style it without
        losing the application-wide style.

        Args:
            field: The widget to highlight.
        """
        field.setProperty("invalid", True)
        field.style().unpolish(field)
        field.style().polish(field)

    def _clear_field_highlights(self) -> None:
        """Remove validation highlights from all form fields."""
        for field in self._field_inputs:
            field.setProperty("invalid", False)
            field.style().unpolish(field)
            field.style().polish(field)

    # ------------------------------------------------------------------
    # Export path helpers
    # ------------------------------------------------------------------

    def _get_export_path(self, mode: str) -> str | None:
        """Show a ``QFileDialog.getSaveFileName`` for the given mode.

        Args:
            mode: ``"front"``, ``"back"``, or ``"combined"``.

        Returns:
            The chosen file path, or ``None`` if the user cancelled.
        """
        model = self._binding_manager.model
        field_data = model.all_values

        if mode == "combined":
            suggested: str = FileNameGenerator.generate_combined_name(
                field_data
            )
            path: str
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Combined PDF",
                suggested,
                "PDF (*.pdf)",
            )
            return path or None

        ext: str = ".png"
        if mode == "front":
            suggested = FileNameGenerator.generate_front_name(
                field_data, ext
            )
        else:
            suggested = FileNameGenerator.generate_back_name(
                field_data, ext
            )

        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            f"Export {'Front' if mode == 'front' else 'Back'} Card",
            suggested,
            "PNG (*.png);;JPEG (*.jpg *.jpeg)",
        )
        return path or None

    def _show_export_success(self, path: str) -> bool:
        """Display an export-success dialog.

        Args:
            path: The path the file was saved to.

        Returns:
            ``True`` if the user clicked "Export Another",
            ``False`` otherwise.
        """
        msg: QMessageBox = QMessageBox(self)
        msg.setWindowTitle("Export Successful")
        msg.setText("Card exported successfully.")
        msg.setInformativeText(str(path))

        open_btn: QPushButton = msg.addButton(
            "Open Folder", QMessageBox.ButtonRole.ActionRole
        )
        retry_btn: QPushButton = msg.addButton(
            "Export Another", QMessageBox.ButtonRole.ActionRole
        )
        ok_btn: QPushButton = msg.addButton(
            "OK", QMessageBox.ButtonRole.AcceptRole
        )
        msg.setDefaultButton(ok_btn)
        msg.exec()

        clicked: QPushButton | None = msg.clickedButton()
        if clicked == open_btn:
            import subprocess  # noqa: PLC0415
            subprocess.Popen(
                ["explorer", "/select,", str(path)]
            )
        return clicked == retry_btn

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_choose_photo(self) -> None:
        """Open a file dialog to pick a photo, then update the model."""

        path: str
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Photo",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)",
        )
        if path:
            self._photo_path = path
            self._photo_label.setText(
                f"Photo selected\n{path.split('/')[-1].split('\\\\')[-1]}"
            )
            self._binding_manager.set_photo(path)

    def _on_clear_form(self) -> None:
        """Reset every input field to its default state after confirmation."""
        reply: QMessageBox.StandardButton = QMessageBox.question(
            self,
            "Clear Form",
            "Are you sure you want to clear all form fields?\n"
            "Any unsaved data will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._name_input.clear()
        self._designation_input.clear()
        self._emp_no_input.clear()
        self._dob_input.clear()
        self._cnic_input.clear()
        self._category_input.clear()
        self._blood_group_input.clear()
        self._location_input.clear()
        self._dependents_front_input.clear()
        self._template_combo.setCurrentIndex(0)

        self._photo_path = ""
        self._photo_label.setText("No photo\nselected")

        # Clear dependents
        self._editing_dep_index = None
        self._binding_manager.clear_dependents()
        self._refresh_dependents_table()
        self._clear_dependent_form()
        self._dep_form_widget.setVisible(False)
        self._add_dep_btn.setEnabled(True)

        # Reset the central data model (emits form_reset -> preview clears)
        self._binding_manager.clear()

        self._info_template.setText("Template: None")
        self._info_image.setText("Image: --")
        self._info_status.setText("Status: Idle")
        self._clear_field_highlights()
        logger.info("Form cleared by user")
