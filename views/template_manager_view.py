"""Template manager view.

Provides a split-panel workspace for managing card templates:
a left-hand table lists all templates, and the right-hand panel
shows front/back design previews, template information, and
action buttons for upload and management.
"""

import logging
import shutil
import uuid as uuid_mod
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.settings import TEMPLATE_UPLOADS_DIR, is_managed_image, resolve_template_image
from controllers.template_controller import TemplateController
from models.template import CardTemplate
from views.widgets.card_preview_widget import CardPreviewWidget

logger = logging.getLogger(__name__)


class TemplateManagerView(QWidget):
    """Template library with list, previews and management actions.

    Signals
    -------
    open_in_editor:
        Emitted when the user wants to open a template in the editor.
        Carries the template id.
    """

    open_in_editor = Signal(int)

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        """Initialise the view, toolbar, list and details panels."""
        super().__init__()
        self.setObjectName("templateManagerView")

        self._template_ctrl: TemplateController = TemplateController()
        self._current_template_id: int | None = None
        self._current_front_image: str | None = None
        self._current_back_image: str | None = None
        self._info_name: QLabel = QLabel()
        self._info_resolution: QLabel = QLabel()
        self._info_card_size: QLabel = QLabel()
        self._info_created: QLabel = QLabel()
        self._info_updated: QLabel = QLabel()
        self._setup_ui()
        self._populate_template_table()

    def _setup_ui(self) -> None:
        """Build the complete page layout."""
        root: QVBoxLayout = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title: QLabel = QLabel("Template Manager")
        title.setObjectName("viewTitle")
        root.addWidget(title)

        description: QLabel = QLabel(
            "Browse, organise and manage your saved card templates."
        )
        description.setObjectName("viewDescription")
        description.setWordWrap(True)
        root.addWidget(description)

        body: QWidget = QWidget()
        body.setObjectName("viewContent")
        body_layout: QVBoxLayout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        body_layout.addWidget(self._build_toolbar())

        splitter: QSplitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        splitter.addWidget(self._build_list_panel())
        splitter.addWidget(self._build_details_panel())

        splitter.setStretchFactor(0, 40)
        splitter.setStretchFactor(1, 60)
        splitter.setSizes([400, 600])

        body_layout.addWidget(splitter, stretch=1)
        root.addWidget(body, stretch=1)

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> QWidget:
        """Construct the top action toolbar.

        Returns:
            A widget containing New, Edit, Delete, Duplicate and
            Refresh buttons.
        """
        bar: QWidget = QWidget()
        bar.setObjectName("templateToolbar")

        layout: QHBoxLayout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(6)

        buttons: list[tuple[str, str, str]] = [
            ("New Template", "new", "Create a new blank template"),
            ("Edit Template", "edit", "Open the selected template in the editor"),
            ("Delete Template", "delete", "Remove the selected template permanently"),
            ("Duplicate Template", "duplicate", "Create a copy of the selected template"),
            ("Refresh", "refresh", "Reload the template list from the database"),
        ]

        for text, action, tooltip in buttons:
            btn: QPushButton = QPushButton(text)
            btn.setObjectName("toolbarButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.clicked.connect(lambda checked=False, a=action: self._on_toolbar_action(a))
            layout.addWidget(btn)

        layout.addStretch()
        return bar

    # ------------------------------------------------------------------
    # Left panel — template list
    # ------------------------------------------------------------------

    def _build_list_panel(self) -> QWidget:
        """Construct the template table (left panel).

        Returns:
            A widget containing a QTableWidget with columns
            ``Template Name``, ``Status``, and ``Updated``.
        """
        panel: QWidget = QWidget()
        panel.setObjectName("templateListPanel")
        panel.setMinimumWidth(280)

        layout: QVBoxLayout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 8, 16)
        layout.setSpacing(8)

        heading: QLabel = QLabel("Templates")
        heading.setObjectName("previewTitle")
        layout.addWidget(heading)

        self._table: QTableWidget = QTableWidget(0, 3)
        self._table.setObjectName("templateTable")
        self._table.setHorizontalHeaderLabels(["Template Name", "Status", "Updated"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)

        header: QHeaderView = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        self._table.itemSelectionChanged.connect(self._on_selection_changed)

        layout.addWidget(self._table)
        return panel

    # ------------------------------------------------------------------
    # Right panel — template details
    # ------------------------------------------------------------------

    def _build_details_panel(self) -> QWidget:
        """Construct the template details panel (right side).

        Returns:
            A scrollable widget containing front/back previews,
            template information and action buttons.
        """
        scroll: QScrollArea = QScrollArea()
        scroll.setObjectName("formScroll")
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(380)

        container: QWidget = QWidget()
        container.setObjectName("detailsContainer")
        layout: QVBoxLayout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # --- Preview heading ---
        preview_heading: QLabel = QLabel("Design Preview")
        preview_heading.setObjectName("previewTitle")
        layout.addWidget(preview_heading)

        # --- Front preview ---
        self._front_preview: CardPreviewWidget = CardPreviewWidget("Front Design")
        self._front_preview.set_placeholder("No front image selected")
        self._front_preview.setMinimumHeight(140)
        self._front_preview.image_deleted.connect(self._on_front_image_deleted)
        layout.addWidget(self._front_preview)

        # --- Back preview ---
        self._back_preview: CardPreviewWidget = CardPreviewWidget("Back Design")
        self._back_preview.set_placeholder("No back image selected")
        self._back_preview.setMinimumHeight(140)
        self._back_preview.image_deleted.connect(self._on_back_image_deleted)
        layout.addWidget(self._back_preview)

        # --- Info section ---
        layout.addWidget(self._build_info_section())

        # --- Action buttons ---
        layout.addWidget(self._build_detail_buttons())

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    # ------------------------------------------------------------------
    # Template information section
    # ------------------------------------------------------------------

    def _build_info_section(self) -> QWidget:
        """Build the template information labels.

        Returns:
            A widget showing Template Name, Image Resolution,
            Card Size, Created and Updated fields.
        """
        section: QWidget = QWidget()
        section.setObjectName("templateInfoSection")

        layout: QVBoxLayout = QVBoxLayout(section)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)

        heading: QLabel = QLabel("Template Information")
        heading.setObjectName("formSectionTitle")
        layout.addWidget(heading)

        self._info_name = QLabel("--")
        self._info_resolution = QLabel("--")
        self._info_card_size = QLabel("85.6 \u00d7 54.0 mm")
        self._info_created = QLabel("--")
        self._info_updated = QLabel("--")

        layout.addWidget(self._build_info_row("Name:", self._info_name))
        layout.addWidget(self._build_info_row("Resolution:", self._info_resolution))
        layout.addWidget(self._build_info_row("Card Size:", self._info_card_size))
        layout.addWidget(self._build_info_row("Created:", self._info_created))
        layout.addWidget(self._build_info_row("Updated:", self._info_updated))

        return section

    @staticmethod
    def _build_info_row(label_text: str, value_label: QLabel) -> QWidget:
        """Build a single labelled information row.

        Args:
            label_text: The field name displayed on the left.
            value_label: The QLabel that shows the value on the right.

        Returns:
            A horizontally laid-out row widget.
        """
        row: QWidget = QWidget()
        row_layout: QHBoxLayout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        label: QLabel = QLabel(label_text)
        label.setObjectName("templateInfoLabel")
        row_layout.addWidget(label)

        value_label.setObjectName("templateInfoValue")
        row_layout.addWidget(value_label, stretch=1)

        return row

    # ------------------------------------------------------------------
    # Detail action buttons
    # ------------------------------------------------------------------

    def _build_detail_buttons(self) -> QWidget:
        """Build the action buttons below the preview.

        Returns:
            A widget containing upload, editor, save and delete
            buttons arranged in two rows.
        """
        section: QWidget = QWidget()
        section.setObjectName("detailButtons")

        layout: QVBoxLayout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Row one — uploads
        row1: QHBoxLayout = QHBoxLayout()
        row1.setSpacing(8)

        self._upload_front_btn: QPushButton = QPushButton("Upload Front Design")
        self._upload_front_btn.setObjectName("actionButton")
        self._upload_front_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._upload_front_btn.clicked.connect(lambda: self._on_upload_image("front"))
        row1.addWidget(self._upload_front_btn)

        self._upload_back_btn: QPushButton = QPushButton("Upload Back Design")
        self._upload_back_btn.setObjectName("actionButton")
        self._upload_back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._upload_back_btn.clicked.connect(lambda: self._on_upload_image("back"))
        row1.addWidget(self._upload_back_btn)

        row1.addStretch()
        layout.addLayout(row1)

        # Row two — actions
        row2: QHBoxLayout = QHBoxLayout()
        row2.setSpacing(8)

        self._open_editor_btn: QPushButton = QPushButton("Open Template Editor")
        self._open_editor_btn.setObjectName("actionButton")
        self._open_editor_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_editor_btn.setEnabled(False)
        self._open_editor_btn.clicked.connect(self._on_open_editor)
        row2.addWidget(self._open_editor_btn)

        self._save_btn: QPushButton = QPushButton("Save Template")
        self._save_btn.setObjectName("actionButton")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._on_save_template)
        row2.addWidget(self._save_btn)

        self._delete_btn: QPushButton = QPushButton("Delete Template")
        self._delete_btn.setObjectName("actionButton")
        self._delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete_selected)
        row2.addWidget(self._delete_btn)

        self._duplicate_btn: QPushButton = QPushButton("Duplicate Template")
        self._duplicate_btn.setObjectName("actionButton")
        self._duplicate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._duplicate_btn.setEnabled(False)
        self._duplicate_btn.clicked.connect(self._on_duplicate_selected)
        row2.addWidget(self._duplicate_btn)

        row2.addStretch()
        layout.addLayout(row2)

        return section

    # ------------------------------------------------------------------
    # Table population
    # ------------------------------------------------------------------

    def _populate_template_table(self) -> None:
        """Load all templates from the database and populate the table."""
        self._table.setRowCount(0)
        templates: list[CardTemplate] = self._template_ctrl.get_all_templates()

        for row_idx, tpl in enumerate(templates):
            self._table.insertRow(row_idx)

            name_item: QTableWidgetItem = QTableWidgetItem(tpl.template_name)
            name_item.setData(Qt.ItemDataRole.UserRole, tpl.id)
            self._table.setItem(row_idx, 0, name_item)

            has_front: bool = bool(tpl.front_image)
            has_back: bool = bool(tpl.back_image)
            if has_front and has_back:
                status: str = "Ready"
            elif has_front or has_back:
                status = "Partial"
            else:
                status = "Empty"
            status_item: QTableWidgetItem = QTableWidgetItem(status)
            status_item.setData(Qt.ItemDataRole.UserRole, tpl.id)
            self._table.setItem(row_idx, 1, status_item)

            updated_str: str = tpl.updated_at or "--"
            updated_item: QTableWidgetItem = QTableWidgetItem(updated_str)
            updated_item.setData(Qt.ItemDataRole.UserRole, tpl.id)
            self._table.setItem(row_idx, 2, updated_item)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_divider() -> QWidget:
        """A thin horizontal line used to separate sections."""
        line: QWidget = QWidget()
        line.setObjectName("divider")
        line.setFixedHeight(1)
        line.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        return line

    # ------------------------------------------------------------------
    # Slots — toolbar
    # ------------------------------------------------------------------

    def _on_toolbar_action(self, action: str) -> None:
        """Dispatch toolbar button clicks.

        Args:
            action: One of ``'new'``, ``'edit'``, ``'delete'``,
                ``'duplicate'``, ``'refresh'``.
        """
        if action == "new":
            self._on_new_template()
        elif action == "edit":
            self._on_open_editor()
        elif action == "delete":
            self._on_delete_selected()
        elif action == "duplicate":
            self._on_duplicate_selected()
        elif action == "refresh":
            self._populate_template_table()
            self._clear_details()
            logger.info("Template list refreshed")

    # ------------------------------------------------------------------
    # Slots — actions
    # ------------------------------------------------------------------

    def _on_new_template(self) -> None:
        """Create a new blank template."""
        name: str
        ok: bool
        name, ok = QInputDialog.getText(
            self, "New Template", "Enter template name:"
        )
        if not ok or not name.strip():
            return

        try:
            tpl: CardTemplate = self._template_ctrl.create_template(name.strip())
            self._populate_template_table()
            self._current_template_id = tpl.id
            self._current_front_image = None
            self._current_back_image = None
            self._save_btn.setEnabled(True)
            self._open_editor_btn.setEnabled(True)
            logger.info("Created new template id=%d name='%s'", tpl.id, tpl.template_name)
        except ValueError as exc:
            QMessageBox.warning(self, "Error", str(exc))

    def _on_open_editor(self) -> None:
        """Open the selected template in the Template Editor."""
        if self._current_template_id is None:
            QMessageBox.information(
                self, "No Selection",
                "Please select a template first."
            )
            return
        self.open_in_editor.emit(self._current_template_id)

    def _on_save_template(self) -> None:
        """Save the current template configuration."""
        if self._current_template_id is None:
            return

        template: CardTemplate | None = self._template_ctrl.get_template_by_id(
            self._current_template_id
        )
        if template is None:
            QMessageBox.warning(self, "Error", "Template not found in database.")
            return

        try:
            if self._current_front_image is not None:
                template.front_image = self._current_front_image
            if self._current_back_image is not None:
                template.back_image = self._current_back_image
            self._template_ctrl.update_template(template)
            self._populate_template_table()
            QMessageBox.information(
                self, "Saved",
                f"Template '{template.template_name}' saved successfully. "
                "Ready to create a new template."
            )
            logger.info("Saved template id=%d", template.id)
            self._clear_details()
            self._table.clearSelection()
        except ValueError as exc:
            QMessageBox.warning(self, "Error", str(exc))

    def _on_delete_selected(self) -> None:
        """Delete the selected template after confirmation."""
        if self._current_template_id is None:
            QMessageBox.information(
                self, "No Selection",
                "Please select a template first."
            )
            return

        if not self._confirm_delete(self._current_template_id):
            return

        # Capture image paths for cleanup after deletion
        template: CardTemplate | None = self._template_ctrl.get_template_by_id(
            self._current_template_id
        )

        try:
            self._template_ctrl.delete_template(self._current_template_id)
            self._populate_template_table()
            self._clear_details()
            logger.info("Deleted template id=%d", self._current_template_id)
            self._current_template_id = None
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"Could not delete template:\n{exc}")
            return

        # Clean up managed images if no other template references them
        if template is not None:
            self._delete_managed_image_if_unused(template.front_image)
            self._delete_managed_image_if_unused(template.back_image)

    def _on_duplicate_selected(self) -> None:
        """Duplicate the selected template with a new name."""
        if self._current_template_id is None:
            QMessageBox.information(
                self, "No Selection",
                "Please select a template first."
            )
            return

        source: CardTemplate | None = self._template_ctrl.get_template_by_id(
            self._current_template_id
        )
        if source is None:
            QMessageBox.warning(self, "Error", "Source template not found.")
            return

        name: str
        ok: bool
        name, ok = QInputDialog.getText(
            self, "Duplicate Template",
            f"Enter a name for the copy of '{source.template_name}':",
            text=f"{source.template_name} (Copy)",
        )
        if not ok or not name.strip():
            return

        try:
            self._template_ctrl.duplicate_template(
                self._current_template_id, name.strip()
            )
            self._populate_template_table()
            logger.info(
                "Duplicated template id=%d as '%s'",
                self._current_template_id, name.strip()
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Error", str(exc))

    # ------------------------------------------------------------------
    # Slots — upload
    # ------------------------------------------------------------------

    def _on_upload_image(self, side: str) -> None:
        """Open a file dialog to select a design image.

        Copies the selected image into the project's managed upload
        directory (``uploads/templates/``) with a unique filename,
        then stores the relative path for later saving.

        Args:
            side: ``'front'`` or ``'back'``.
        """
        source_path: str
        source_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Upload {side.title()} Design",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)",
        )
        if not source_path:
            return

        pixmap: QPixmap = QPixmap(source_path)
        if pixmap.isNull():
            return

        # Copy the file into the managed uploads directory
        ext: str = Path(source_path).suffix or ".png"
        unique_name: str = f"{uuid_mod.uuid4().hex}_{side}{ext}"
        dest: Path = TEMPLATE_UPLOADS_DIR / unique_name
        try:
            shutil.copy2(source_path, str(dest))
        except OSError as exc:
            QMessageBox.warning(
                self, "Upload Error",
                f"Failed to copy image:\n{exc}"
            )
            return

        # Build the relative path for database storage
        relative_dest: str = str(dest.relative_to(TEMPLATE_UPLOADS_DIR.parent.parent))
        # relative_dest is e.g. "uploads/templates/abc123_front.png"

        # Remove the old managed file if one existed for this slot
        old_path: str | None = (
            self._current_front_image if side == "front" else self._current_back_image
        )
        self._delete_managed_image(old_path)

        if side == "front":
            self._front_preview.set_pixmap(pixmap)
            self._current_front_image = relative_dest
        else:
            self._back_preview.set_pixmap(pixmap)
            self._current_back_image = relative_dest

        self._info_resolution.setText(f"{pixmap.width()} \u00d7 {pixmap.height()} px")
        self._save_btn.setEnabled(self._current_template_id is not None)

    # ------------------------------------------------------------------
    # Image deletion
    # ------------------------------------------------------------------

    def _on_front_image_deleted(self) -> None:
        """Clear the front image selection and remove the managed copy."""
        self._delete_managed_image(self._current_front_image)
        self._current_front_image = None
        self._front_preview.set_pixmap(None)

    def _on_back_image_deleted(self) -> None:
        """Clear the back image selection and remove the managed copy."""
        self._delete_managed_image(self._current_back_image)
        self._current_back_image = None
        self._back_preview.set_pixmap(None)

    # ------------------------------------------------------------------
    # Image file management
    # ------------------------------------------------------------------

    @staticmethod
    def _delete_managed_image(path: str | None) -> None:
        """Delete a managed image file from the uploads directory.

        Only files inside :attr:`TEMPLATE_UPLOADS_DIR` are removed.
        The user's original source file is never touched.
        """
        if not is_managed_image(path):
            return
        try:
            Path(path).unlink(missing_ok=True)
            logger.debug("Deleted managed image: %s", path)
        except OSError as exc:
            logger.warning("Could not delete managed image %s: %s", path, exc)

    def _delete_managed_image_if_unused(self, path: str | None) -> None:
        """Delete a managed image only if no other template references it."""
        if not is_managed_image(path):
            return
        count: int = self._template_ctrl.count_templates_by_image(path)
        if count == 0:
            self._delete_managed_image(path)

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _on_selection_changed(self) -> None:
        """Update the details panel when a different row is selected."""
        selected: list[QTableWidgetItem] = self._table.selectedItems()
        if not selected:
            return

        row: int = selected[0].row()
        name_item: QTableWidgetItem | None = self._table.item(row, 0)
        if name_item is None:
            return

        template_id: int = name_item.data(Qt.ItemDataRole.UserRole)
        if template_id is None:
            return

        self._current_template_id = template_id
        self._current_front_image = None
        self._current_back_image = None

        template: CardTemplate | None = self._template_ctrl.get_template_by_id(
            template_id
        )
        if template is None:
            return

        # Update information labels
        self._info_name.setText(template.template_name)
        self._info_card_size.setText(
            f"{template.canvas_width} \u00d7 {template.canvas_height} mm"
        )
        self._info_created.setText(template.created_at or "--")
        self._info_updated.setText(template.updated_at or "--")

        # Update front preview
        front_path: str | None = resolve_template_image(template.front_image)
        if front_path:
            pix: QPixmap = QPixmap(front_path)
            if not pix.isNull():
                self._front_preview.set_pixmap(pix)
                self._info_resolution.setText(f"{pix.width()} \u00d7 {pix.height()} px")
            else:
                self._front_preview.set_placeholder("No front image selected")
        else:
            if template.front_image:
                logger.warning("Front image missing: %s", template.front_image)
            self._front_preview.set_placeholder("No front image selected")

        # Update back preview
        back_path: str | None = resolve_template_image(template.back_image)
        if back_path:
            pix = QPixmap(back_path)
            if not pix.isNull():
                self._back_preview.set_pixmap(pix)
            else:
                self._back_preview.set_placeholder("No back image selected")
        else:
            if template.back_image:
                logger.warning("Back image missing: %s", template.back_image)
            self._back_preview.set_placeholder("No back image selected")

        # Enable detail buttons
        self._open_editor_btn.setEnabled(True)
        self._save_btn.setEnabled(True)
        self._delete_btn.setEnabled(True)
        self._duplicate_btn.setEnabled(True)

    def _clear_details(self) -> None:
        """Reset the details panel to its default state."""
        self._current_template_id = None
        self._current_front_image = None
        self._current_back_image = None
        self._info_name.setText("--")
        self._info_resolution.setText("--")
        self._info_card_size.setText("85.6 \u00d7 54.0 mm")
        self._info_created.setText("--")
        self._info_updated.setText("--")
        self._front_preview.set_placeholder("No front image selected")
        self._back_preview.set_placeholder("No back image selected")
        self._open_editor_btn.setEnabled(False)
        self._save_btn.setEnabled(False)
        self._delete_btn.setEnabled(False)
        self._duplicate_btn.setEnabled(False)

    # ------------------------------------------------------------------
    # Confirmation
    # ------------------------------------------------------------------

    @staticmethod
    def _confirm_delete(template_id: int) -> bool:
        """Show a confirmation dialog before deleting a template.

        Args:
            template_id: The identifier of the template to delete.

        Returns:
            ``True`` if the user confirms deletion.
        """
        result: QMessageBox.StandardButton = QMessageBox.warning(
            None,
            "Confirm Template Deletion",
            f"Are you sure you want to delete template #{template_id}?\n\n"
            "This action is irreversible. Cards using this template "
            "will have their template reference set to null.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return result == QMessageBox.StandardButton.Yes
