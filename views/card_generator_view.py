"""Card generator view.

Provides the input form and live preview area for generating
ID cards.  The page is split into a left scrollable form panel
(35 %) and a right card-preview panel (65 %) via a QSplitter.

Data flow
---------
Form widgets are bound to a ``BindingManager`` via ``FormBinder``.
All user input passes through the central ``CardDataModel`` before
reaching the preview or any downstream engine.
"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
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
from views.widgets.preview_canvas import PreviewCanvas

logger = logging.getLogger(__name__)


class CardGeneratorView(QWidget):
    """Card generation workspace with input form and dual previews.

    The form fields are bound to a ``BindingManager`` so that
    every keystroke, date change, photo selection, and template
    switch flows through the central ``CardDataModel`` before
    reaching the preview engine or any future consumer.

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

    def _setup_ui(self) -> None:
        """Build the complete page layout."""
        root: QVBoxLayout = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(16)

        title: QLabel = QLabel("Card Generator")
        title.setObjectName("viewTitle")
        root.addWidget(title)

        description: QLabel = QLabel(
            "Fill in the cardholder details below.  The preview area "
            "on the right will update as you type."
        )
        description.setObjectName("viewDescription")
        description.setWordWrap(True)
        root.addWidget(description)

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

    # ------------------------------------------------------------------
    # Form bindings
    # ------------------------------------------------------------------

    def _bind_form_widgets(self) -> None:
        """Connect every form widget to the ``BindingManager``."""
        self._form_binder.bind_text_field(self._name_input, "employee_name")
        self._form_binder.bind_text_field(
            self._designation_input, "designation"
        )
        self._form_binder.bind_text_field(
            self._category_input, "employee_category"
        )
        self._form_binder.bind_text_field(
            self._blood_group_input, "blood_group"
        )
        self._form_binder.bind_text_field(
            self._location_input, "location"
        )
        self._form_binder.bind_text_field(
            self._dependence_input, "dependence"
        )
        self._form_binder.bind_template_combo(self._template_combo)

    # ------------------------------------------------------------------
    # Left panel — scrollable form
    # ------------------------------------------------------------------

    def _build_form_panel(self) -> QWidget:
        """Construct the scrollable input form (left panel).

        Returns:
            A QScrollArea containing all form fields and buttons.
        """
        scroll: QScrollArea = QScrollArea()
        scroll.setObjectName("formScroll")
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(300)

        container: QWidget = QWidget()
        container.setObjectName("formContainer")
        form: QVBoxLayout = QVBoxLayout(container)
        form.setContentsMargins(24, 24, 24, 24)
        form.setSpacing(16)

        form.addWidget(self._build_photo_section())

        fields_layout: QFormLayout = self._build_form_fields()
        form.addLayout(fields_layout)

        form.addWidget(self._build_divider())

        form.addLayout(self._build_action_buttons())

        form.addStretch()
        scroll.setWidget(container)
        return scroll

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

        layout: QVBoxLayout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        heading: QLabel = QLabel("Photo")
        heading.setObjectName("formSectionTitle")
        layout.addWidget(heading)

        self._photo_label: QLabel = QLabel()
        self._photo_label.setObjectName("photoPlaceholder")
        self._photo_label.setFixedSize(120, 120)
        self._photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._photo_label.setText("No photo\nselected")
        layout.addWidget(self._photo_label)

        choose_btn: QPushButton = QPushButton("Choose Photo")
        choose_btn.setObjectName("photoButton")
        choose_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        choose_btn.setToolTip("Select a photo for the card")
        choose_btn.clicked.connect(self._on_choose_photo)
        layout.addWidget(choose_btn)

        return section

    # ------------------------------------------------------------------
    # Form fields  (widgets created here, bound in _bind_form_widgets)
    # ------------------------------------------------------------------

    def _build_form_fields(self) -> QFormLayout:
        """Build the labelled input fields.

        Returns:
            A QFormLayout containing Employee Name, Designation,
            Employee Category, Blood Group, Location, Dependence
            and Template selector.
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

        # --- Designation ---
        self._designation_input = QLineEdit()
        self._designation_input.setObjectName("fieldInput")
        self._designation_input.setPlaceholderText("e.g. Software Engineer")
        self._designation_input.setToolTip("Designation (required)")
        layout.addRow("Designation:", self._designation_input)
        self._field_inputs.append(self._designation_input)

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

        # --- Dependence ---
        self._dependence_input = QLineEdit()
        self._dependence_input.setObjectName("fieldInput")
        self._dependence_input.setPlaceholderText("e.g. Self")
        self._dependence_input.setToolTip("Dependence")
        layout.addRow("Dependence:", self._dependence_input)

        # --- Template ---
        self._template_combo = QComboBox()
        self._template_combo.setObjectName("fieldInput")
        self._template_combo.addItem("-- Select Template --", 0)
        layout.addRow("Template:", self._template_combo)

        return layout

    # ------------------------------------------------------------------
    # Action buttons
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

        # Row two — disabled actions
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
    # Right panel — live preview
    # ------------------------------------------------------------------

    def _build_preview_panel(self) -> QWidget:
        """Construct the live preview area (right panel).

        Returns:
            A widget containing front / back card previews and an
            information bar at the bottom.
        """
        panel: QWidget = QWidget()
        panel.setObjectName("previewPanel")
        panel.setMinimumWidth(400)

        layout: QVBoxLayout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        heading: QLabel = QLabel("Live Preview")
        heading.setObjectName("previewTitle")
        layout.addWidget(heading)

        # --- Card preview canvases ---
        self._front_preview: PreviewCanvas = PreviewCanvas(
            "Front Card"
        )
        self._front_preview.set_placeholder("No Front Template Selected")
        layout.addWidget(self._front_preview, stretch=1)

        self._back_preview: PreviewCanvas = PreviewCanvas(
            "Back Card"
        )
        self._back_preview.set_placeholder("No Back Template Selected")
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

        layout: QHBoxLayout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)

        self._info_template: QLabel = QLabel("Template: None")
        self._info_template.setObjectName("infoLabel")
        layout.addWidget(self._info_template)

        self._info_image: QLabel = QLabel("Image: --")
        self._info_image.setObjectName("infoLabel")
        layout.addWidget(self._info_image)

        self._info_card: QLabel = QLabel("Card: 85.6 × 54.0 mm")
        self._info_card.setObjectName("infoLabel")
        layout.addWidget(self._info_card)

        self._info_status: QLabel = QLabel("Status: Idle")
        self._info_status.setObjectName("infoLabel")
        layout.addWidget(self._info_status)

        layout.addStretch()
        return bar

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

        # Restore previous selection
        if current_id > 0:
            idx: int = self._template_combo.findData(current_id)
            if idx >= 0:
                self._template_combo.setCurrentIndex(idx)
        self._template_combo.blockSignals(False)

    def showEvent(self, event) -> None:  # noqa: N802
        """Refresh the template dropdown every time the page becomes visible."""
        super().showEvent(event)
        self._populate_template_combo()

    def _on_download(self, mode: str) -> None:
        """Open a save dialog, export the card, and show the result.

        Validates required fields before export, shows a progress
        dialog, and prevents duplicate clicks while exporting.

        Args:
            mode: ``"front"``, ``"back"``, or ``"combined"``.
        """
        # Validate required fields before export
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

    def _validate_form(self) -> list[str]:
        """Check that all required fields are filled.

        Returns:
            A list of user-friendly error messages (empty = valid).
        """
        errors: list[str] = []
        self._clear_field_highlights()

        if not self._name_input.text().strip():
            errors.append("Employee Name is required")
            self._highlight_field(self._name_input)

        if not self._designation_input.text().strip():
            errors.append("Designation is required")
            self._highlight_field(self._designation_input)

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
        self._category_input.clear()
        self._blood_group_input.clear()
        self._location_input.clear()
        self._dependence_input.clear()
        self._template_combo.setCurrentIndex(0)

        self._photo_path = ""
        self._photo_label.setText("No photo\nselected")

        # Reset the central data model (emits form_reset → preview clears)
        self._binding_manager.clear()

        self._info_template.setText("Template: None")
        self._info_image.setText("Image: --")
        self._info_status.setText("Status: Idle")
        self._clear_field_highlights()
        logger.info("Form cleared by user")
