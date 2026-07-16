"""Card generator view.

Provides a dual-mode (Front / Back) input form and live preview
for generating ID cards.  The page is split into a left scrollable
form panel (35 %) and a right card-preview panel (65 %) via a
QSplitter.  Switching between Front and Back mode changes the form
fields and the visible preview accordingly.

Data flow
---------
Form widgets are bound to a ``BindingManager`` via ``FormBinder``.
All user input passes through the central ``CardDataModel`` before
reaching the preview or any downstream engine.
"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
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
    QSizePolicy,
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

logger = logging.getLogger(__name__)


class CardGeneratorView(QWidget):
    """Card generation workspace with Front / Back mode switching.

    The form fields are bound to a ``BindingManager`` so that
    every keystroke, date change, photo selection, and template
    switch flows through the central ``CardDataModel`` before
    reaching the preview engine or any future consumer.

    Two tabs at the top control the active side:
    - **Front mode**:  Front-only form fields + Front preview.
    - **Back mode**:   Dependents management + Back preview.

    The download buttons open a save dialog and delegate the
    actual export to ``ExportManager``.
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

        # Template data access
        self._template_ctrl: TemplateController = TemplateController()

        # Central data management (created before UI to avoid late init)
        self._binding_manager: BindingManager = BindingManager(self)

        # Must be initialized before _setup_ui() because _build_form_fields
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

        # Export engine
        self._export_manager: ExportManager = ExportManager(
            self._binding_manager, TemplateController()
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
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(16)

        title: QLabel = QLabel("Card Generator")
        title.setObjectName("viewTitle")
        root.addWidget(title)

        description: QLabel = QLabel(
            "Fill in the cardholder details below.  "
            "Switch between Front and Back to edit each side."
        )
        description.setObjectName("viewDescription")
        description.setWordWrap(True)
        root.addWidget(description)

        # --- Front / Back mode selector tabs ---
        tab_row: QWidget = QWidget()
        tab_layout: QHBoxLayout = QHBoxLayout(tab_row)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(4)

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

        tab_layout.addWidget(self._front_tab_btn)
        tab_layout.addWidget(self._back_tab_btn)
        tab_layout.addStretch()
        root.addWidget(tab_row)

        # --- Body (splitter) ---
        body: QWidget = QWidget()
        body.setObjectName("viewContent")
        body_layout: QVBoxLayout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)

        splitter: QSplitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        splitter.addWidget(self._build_form_panel())
        splitter.addWidget(self._build_preview_panel())

        splitter.setStretchFactor(0, 35)
        splitter.setStretchFactor(1, 65)
        splitter.setSizes([350, 650])

        body_layout.addWidget(splitter)
        root.addWidget(body, stretch=1)

        # Wire side tabs
        self._side_tab_group.idClicked.connect(self._on_side_changed)

    # ------------------------------------------------------------------
    # Form panel (left)
    # ------------------------------------------------------------------

    def _build_form_panel(self) -> QWidget:
        """Construct the scrollable input form (left panel).

        Returns:
            A QScrollArea containing a shared template selector,
            a stacked widget for Front/Back forms, and action buttons.
        """
        scroll: QScrollArea = QScrollArea()
        scroll.setObjectName("formScroll")
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(300)

        container: QWidget = QWidget()
        container.setObjectName("formContainer")
        form_vbox: QVBoxLayout = QVBoxLayout(container)
        form_vbox.setContentsMargins(24, 24, 24, 24)
        form_vbox.setSpacing(16)

        # --- Template selector (shared across modes) ---
        template_label: QLabel = QLabel("Template")
        template_label.setObjectName("formSectionTitle")
        form_vbox.addWidget(template_label)

        self._template_combo = QComboBox()
        self._template_combo.setObjectName("fieldInput")
        self._template_combo.addItem("-- Select Template --", 0)
        form_vbox.addWidget(self._template_combo)

        # --- Stacked form: Front / Back ---
        self._form_stack: QStackedWidget = QStackedWidget()
        self._front_form: QWidget = self._build_front_form()
        self._back_form: QWidget = self._build_back_form()
        self._form_stack.addWidget(self._front_form)
        self._form_stack.addWidget(self._back_form)
        form_vbox.addWidget(self._form_stack)

        # --- Divider and action buttons ---
        form_vbox.addWidget(self._build_divider())
        form_vbox.addLayout(self._build_action_buttons())

        form_vbox.addStretch()
        scroll.setWidget(container)
        return scroll

    # ------------------------------------------------------------------
    # Front form
    # ------------------------------------------------------------------

    def _build_front_form(self) -> QWidget:
        """Build the Front-side input form.

        Returns:
            A widget containing photo selection and all Front fields.
        """
        container: QWidget = QWidget()
        layout: QVBoxLayout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        layout.addWidget(self._build_photo_section())

        self._side_indicator_front: QLabel = QLabel("Front Side Information")
        self._side_indicator_front.setObjectName("formSectionTitle")
        layout.addWidget(self._side_indicator_front)

        fields_layout: QFormLayout = self._build_front_fields()
        layout.addLayout(fields_layout)

        return container

    def _build_front_fields(self) -> QFormLayout:
        """Build the Front-side labelled input fields.

        Returns:
            A QFormLayout containing all 9 front fields:
            Employee Name, Employee Designation, Employee No,
            Date of Birth, CNIC, Employee Category, Blood Group,
            Location, and Dependents.
        """
        layout: QFormLayout = QFormLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        # --- Employee Name ---
        self._name_input = QLineEdit()
        self._name_input.setObjectName("fieldInput")
        self._name_input.setPlaceholderText("e.g. John Doe")
        self._name_input.setToolTip("Employee full name (required)")
        layout.addRow("Employee Name:", self._name_input)
        self._field_inputs.append(self._name_input)

        # --- Employee Designation ---
        self._designation_input = QLineEdit()
        self._designation_input.setObjectName("fieldInput")
        self._designation_input.setPlaceholderText("e.g. Software Engineer")
        self._designation_input.setToolTip("Employee designation (required)")
        layout.addRow("Employee Designation:", self._designation_input)
        self._field_inputs.append(self._designation_input)

        # --- Employee No ---
        self._emp_no_input = QLineEdit()
        self._emp_no_input.setObjectName("fieldInput")
        self._emp_no_input.setPlaceholderText("e.g. EMP-001")
        self._emp_no_input.setToolTip("Employee number (required)")
        layout.addRow("Employee No:", self._emp_no_input)
        self._field_inputs.append(self._emp_no_input)

        # --- Date of Birth ---
        self._dob_input = QLineEdit()
        self._dob_input.setObjectName("fieldInput")
        self._dob_input.setPlaceholderText("e.g. 15-08-1990")
        self._dob_input.setToolTip("Date of birth")
        layout.addRow("Date of Birth:", self._dob_input)

        # --- CNIC ---
        self._cnic_input = QLineEdit()
        self._cnic_input.setObjectName("fieldInput")
        self._cnic_input.setPlaceholderText("e.g. 12345-6789012-3")
        self._cnic_input.setToolTip("CNIC number")
        layout.addRow("CNIC:", self._cnic_input)

        # --- Employee Category ---
        self._category_input = QLineEdit()
        self._category_input.setObjectName("fieldInput")
        self._category_input.setPlaceholderText("e.g. Permanent")
        self._category_input.setToolTip("Employee category (required)")
        layout.addRow("Employee Category:", self._category_input)
        self._field_inputs.append(self._category_input)

        # --- Blood Group ---
        self._blood_group_input = QLineEdit()
        self._blood_group_input.setObjectName("fieldInput")
        self._blood_group_input.setPlaceholderText("e.g. A+")
        self._blood_group_input.setToolTip("Blood group")
        layout.addRow("Blood Group:", self._blood_group_input)

        # --- Location ---
        self._location_input = QLineEdit()
        self._location_input.setObjectName("fieldInput")
        self._location_input.setPlaceholderText("e.g. Head Office")
        self._location_input.setToolTip("Location (required)")
        layout.addRow("Location:", self._location_input)
        self._field_inputs.append(self._location_input)

        # --- Dependents ---
        self._dependents_front_input = QLineEdit()
        self._dependents_front_input.setObjectName("fieldInput")
        self._dependents_front_input.setPlaceholderText("e.g. Self, Spouse, 2 Children")
        self._dependents_front_input.setToolTip("Dependents information")
        layout.addRow("Dependents:", self._dependents_front_input)

        return layout

    # ------------------------------------------------------------------
    # Back form
    # ------------------------------------------------------------------

    def _build_back_form(self) -> QWidget:
        """Build the Back-side input form with dependents management.

        Returns:
            A widget containing the dependents table, add form,
            and Add Dependent button.
        """
        container: QWidget = QWidget()
        layout: QVBoxLayout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self._side_indicator_back: QLabel = QLabel("Back Side Information")
        self._side_indicator_back.setObjectName("formSectionTitle")
        layout.addWidget(self._side_indicator_back)

        dependents_title: QLabel = QLabel("Dependents")
        dependents_title.setObjectName("formSectionTitle")
        layout.addWidget(dependents_title)

        # --- Inline add-dependent form (hidden by default) ---
        self._dep_form_widget = QWidget()
        self._dep_form_widget.setObjectName("dependentForm")
        self._dep_form_widget.setVisible(False)
        dep_form_layout: QFormLayout = QFormLayout(self._dep_form_widget)
        dep_form_layout.setSpacing(8)
        dep_form_layout.setContentsMargins(0, 0, 0, 0)

        self._dep_name_input = QLineEdit()
        self._dep_name_input.setObjectName("fieldInput")
        self._dep_name_input.setPlaceholderText("e.g. Ali")
        dep_form_layout.addRow("Name:", self._dep_name_input)

        self._dep_relation_input = QLineEdit()
        self._dep_relation_input.setObjectName("fieldInput")
        self._dep_relation_input.setPlaceholderText("e.g. Son")
        dep_form_layout.addRow("Relation:", self._dep_relation_input)

        self._dep_dob_input = QLineEdit()
        self._dep_dob_input.setObjectName("fieldInput")
        self._dep_dob_input.setPlaceholderText("e.g. 10-10-2015")
        dep_form_layout.addRow("Date of Birth:", self._dep_dob_input)

        self._dep_cnic_input = QLineEdit()
        self._dep_cnic_input.setObjectName("fieldInput")
        self._dep_cnic_input.setPlaceholderText("e.g. 12345-6789012-3")
        dep_form_layout.addRow("CNIC:", self._dep_cnic_input)

        # Save / Cancel buttons
        dep_btn_row: QHBoxLayout = QHBoxLayout()
        self._dep_save_btn: QPushButton = QPushButton("Save")
        self._dep_save_btn.setObjectName("actionButton")
        self._dep_save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dep_save_btn.clicked.connect(self._on_save_dependent)
        dep_btn_row.addWidget(self._dep_save_btn)

        self._dep_cancel_btn: QPushButton = QPushButton("Cancel")
        self._dep_cancel_btn.setObjectName("actionButton")
        self._dep_cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dep_cancel_btn.clicked.connect(self._on_cancel_dependent)
        dep_btn_row.addWidget(self._dep_cancel_btn)

        dep_form_layout.addRow(dep_btn_row)

        layout.addWidget(self._dep_form_widget)

        # --- Add Dependent button ---
        self._add_dep_btn: QPushButton = QPushButton("Add Dependent")
        self._add_dep_btn.setObjectName("actionButton")
        self._add_dep_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_dep_btn.setToolTip("Add a new dependent record")
        self._add_dep_btn.clicked.connect(self._on_add_dependent)
        layout.addWidget(self._add_dep_btn)

        # --- Dependents table ---
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
        self._dependents_table.setMinimumHeight(120)
        layout.addWidget(self._dependents_table)

        return container

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
    # Action buttons (shared)
    # ------------------------------------------------------------------

    def _build_action_buttons(self) -> QVBoxLayout:
        """Build the form action buttons.

        Returns:
            A vertical layout with two rows of buttons.
        """
        layout: QVBoxLayout = QVBoxLayout()
        layout.setSpacing(8)

        # Row one — clear
        row1: QHBoxLayout = QHBoxLayout()
        row1.setSpacing(8)

        clear_btn: QPushButton = QPushButton("Clear Form")
        clear_btn.setObjectName("actionButton")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setToolTip("Reset all form fields to their default values")
        clear_btn.clicked.connect(self._on_clear_form)
        row1.addWidget(clear_btn)

        row1.addStretch()
        layout.addLayout(row1)

        # Row two — download actions
        row2: QHBoxLayout = QHBoxLayout()
        row2.setSpacing(8)

        self._save_btn: QPushButton = QPushButton("Save")
        self._save_btn.setObjectName("actionButton")
        self._save_btn.setEnabled(False)
        self._save_btn.setToolTip("Save the current card to history (coming soon)")
        row2.addWidget(self._save_btn)

        self._dl_front_btn: QPushButton = QPushButton("Download Front")
        self._dl_front_btn.setObjectName("actionButton")
        self._dl_front_btn.setEnabled(False)
        self._dl_front_btn.setToolTip("Export the front card as PNG or JPEG")
        row2.addWidget(self._dl_front_btn)

        self._dl_back_btn: QPushButton = QPushButton("Download Back")
        self._dl_back_btn.setObjectName("actionButton")
        self._dl_back_btn.setEnabled(False)
        self._dl_back_btn.setToolTip("Export the back card as PNG or JPEG")
        row2.addWidget(self._dl_back_btn)

        self._dl_pdf_btn: QPushButton = QPushButton("Download PDF")
        self._dl_pdf_btn.setObjectName("actionButton")
        self._dl_pdf_btn.setEnabled(False)
        self._dl_pdf_btn.setToolTip("Export the combined front + back PDF")
        row2.addWidget(self._dl_pdf_btn)

        layout.addLayout(row2)
        return layout

    # ------------------------------------------------------------------
    # Preview panel (right)
    # ------------------------------------------------------------------

    def _build_preview_panel(self) -> QWidget:
        """Construct the live preview area (right panel).

        Returns:
            A widget containing the preview heading with expand button,
            front and back preview canvases (one visible at a time),
            and an information bar at the bottom.
        """
        panel: QWidget = QWidget()
        panel.setObjectName("previewPanel")
        panel.setMinimumWidth(400)

        layout: QVBoxLayout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # --- Preview title row with expand button ---
        title_row: QWidget = QWidget()
        title_row_layout: QHBoxLayout = QHBoxLayout(title_row)
        title_row_layout.setContentsMargins(0, 0, 0, 0)
        title_row_layout.setSpacing(8)

        heading: QLabel = QLabel("Live Preview")
        heading.setObjectName("previewTitle")
        title_row_layout.addWidget(heading)

        title_row_layout.addStretch()

        self._expand_preview_btn: QPushButton = QPushButton("Expand Preview")
        self._expand_preview_btn.setObjectName("actionButton")
        self._expand_preview_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._expand_preview_btn.setToolTip("Open a larger preview window")
        self._expand_preview_btn.clicked.connect(self._on_expand_preview)
        title_row_layout.addWidget(self._expand_preview_btn)

        layout.addWidget(title_row)

        # --- Card preview canvases (only one visible at a time) ---
        self._front_preview: PreviewCanvas = PreviewCanvas("Front Card")
        self._front_preview.set_placeholder("No Front Template Selected")
        layout.addWidget(self._front_preview, stretch=1)

        self._back_preview: PreviewCanvas = PreviewCanvas("Back Card")
        self._back_preview.set_placeholder("No Back Template Selected")
        self._back_preview.setVisible(False)
        layout.addWidget(self._back_preview, stretch=1)

        # --- Information bar ---
        layout.addWidget(self._build_info_bar())

        return panel

    def _build_info_bar(self) -> QWidget:
        """Build the bottom information strip.

        Returns:
            A widget showing selected template, image size, card
            dimensions and preview status.
        """
        bar: QWidget = QWidget()
        bar.setObjectName("infoBar")

        b_layout: QHBoxLayout = QHBoxLayout(bar)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(24)

        self._info_template: QLabel = QLabel("Template: None")
        self._info_template.setObjectName("infoLabel")
        b_layout.addWidget(self._info_template)

        self._info_image: QLabel = QLabel("Image: --")
        self._info_image.setObjectName("infoLabel")
        b_layout.addWidget(self._info_image)

        self._info_card: QLabel = QLabel("Card: 85.6 × 54.0 mm")
        self._info_card.setObjectName("infoLabel")
        b_layout.addWidget(self._info_card)

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
        showing_front: bool = self._active_side == "front"

        # Switch form
        self._form_stack.setCurrentIndex(0 if showing_front else 1)

        # Switch preview
        self._front_preview.setVisible(showing_front)
        self._back_preview.setVisible(not showing_front)

    # ------------------------------------------------------------------
    # Dependents management
    # ------------------------------------------------------------------

    def _on_add_dependent(self) -> None:
        """Show the inline add-dependent form."""
        self._dep_form_widget.setVisible(True)
        self._add_dep_btn.setEnabled(False)

    def _on_save_dependent(self) -> None:
        """Save the current dependent entry and refresh the table."""
        name: str = self._dep_name_input.text().strip()
        relation: str = self._dep_relation_input.text().strip()
        dob: str = self._dep_dob_input.text().strip()
        cnic: str = self._dep_cnic_input.text().strip()

        if not name:
            QMessageBox.warning(
                self, "Validation Error",
                "Dependent name is required.",
            )
            return

        dependent: dict = {
            "name": name,
            "relation": relation,
            "date_of_birth": dob,
            "cnic": cnic,
        }
        self._binding_manager.add_dependent(dependent)
        self._refresh_dependents_table()
        self._clear_dependent_form()
        self._dep_form_widget.setVisible(False)
        self._add_dep_btn.setEnabled(True)

    def _on_cancel_dependent(self) -> None:
        """Cancel adding a dependent and hide the form."""
        self._clear_dependent_form()
        self._dep_form_widget.setVisible(False)
        self._add_dep_btn.setEnabled(True)

    def _clear_dependent_form(self) -> None:
        """Clear all fields in the add-dependent form."""
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

    # ------------------------------------------------------------------
    # Expand preview
    # ------------------------------------------------------------------

    def _on_expand_preview(self) -> None:
        """Open the large preview dialog with the current card image."""
        dialog: LargePreviewDialog = LargePreviewDialog(self)

        # Determine which pixmap to show
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
    # Helpers
    # ------------------------------------------------------------------

    def _build_divider(self) -> QWidget:
        """A thin horizontal line used to separate sections."""
        line: QWidget = QWidget()
        line.setObjectName("divider")
        line.setFixedHeight(1)
        line.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        return line

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
                + "\n".join(f"• {e}" for e in errors),
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
