"""Template manager view.

Provides a split-panel workspace for managing card templates:
a left-hand table lists all templates, and the right-hand panel
shows front/back design previews, template information, and
action buttons for upload and management.
"""

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
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

from views.widgets.card_preview_widget import CardPreviewWidget

logger = logging.getLogger(__name__)


class TemplateManagerView(QWidget):
    """Template library with list, previews and management actions.

    Signals
    -------
    template_selected:
        Emitted when a row in the template table is clicked.
        Carries the template id.
    template_created:
        Emitted when the ``New Template`` button is clicked.
    template_deleted:
        Emitted when the ``Delete Template`` button is clicked.
        Carries the template id.
    template_updated:
        Emitted when the ``Save Template`` button is clicked.
        Carries the template id.
    front_uploaded:
        Emitted when a front-design image is selected.
        Carries the file path.
    back_uploaded:
        Emitted when a back-design image is selected.
        Carries the file path.
    """

    template_selected = Signal(int)
    template_created = Signal()
    template_deleted = Signal(int)
    template_updated = Signal(int)
    front_uploaded = Signal(str)
    back_uploaded = Signal(str)

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        """Initialise the view, toolbar, list and details panels."""
        super().__init__()
        self.setObjectName("templateManagerView")

        self._current_template_id: int | None = None
        self._info_name: QLabel = QLabel()
        self._info_resolution: QLabel = QLabel()
        self._info_card_size: QLabel = QLabel()
        self._info_created: QLabel = QLabel()
        self._info_updated: QLabel = QLabel()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the complete page layout."""
        root: QVBoxLayout = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
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
        layout.addWidget(self._front_preview)

        # --- Back preview ---
        self._back_preview: CardPreviewWidget = CardPreviewWidget("Back Design")
        self._back_preview.set_placeholder("No back image selected")
        self._back_preview.setMinimumHeight(140)
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

        upload_front: QPushButton = QPushButton("Upload Front Design")
        upload_front.setObjectName("actionButton")
        upload_front.setCursor(Qt.CursorShape.PointingHandCursor)
        upload_front.clicked.connect(lambda: self._on_upload_image("front"))
        row1.addWidget(upload_front)

        upload_back: QPushButton = QPushButton("Upload Back Design")
        upload_back.setObjectName("actionButton")
        upload_back.setCursor(Qt.CursorShape.PointingHandCursor)
        upload_back.clicked.connect(lambda: self._on_upload_image("back"))
        row1.addWidget(upload_back)

        row1.addStretch()
        layout.addLayout(row1)

        # Row two — actions
        row2: QHBoxLayout = QHBoxLayout()
        row2.setSpacing(8)

        self._open_editor_btn: QPushButton = QPushButton("Open Template Editor")
        self._open_editor_btn.setObjectName("actionButton")
        self._open_editor_btn.setEnabled(False)
        row2.addWidget(self._open_editor_btn)

        self._save_btn: QPushButton = QPushButton("Save Template")
        self._save_btn.setObjectName("actionButton")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(
            lambda: self.template_updated.emit(self._current_template_id or 0)
        )
        row2.addWidget(self._save_btn)

        delete_btn: QPushButton = QPushButton("Delete Template")
        delete_btn.setObjectName("actionButton")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.clicked.connect(
            lambda: self.template_deleted.emit(self._current_template_id or 0)
        )
        row2.addWidget(delete_btn)

        duplicate_btn: QPushButton = QPushButton("Duplicate Template")
        duplicate_btn.setObjectName("actionButton")
        duplicate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        duplicate_btn.clicked.connect(
            lambda: self.template_created.emit()
        )
        row2.addWidget(duplicate_btn)

        row2.addStretch()
        layout.addLayout(row2)

        return section

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
    # Slots
    # ------------------------------------------------------------------

    def _on_toolbar_action(self, action: str) -> None:
        """Dispatch toolbar button clicks.

        Args:
            action: One of ``'new'``, ``'edit'``, ``'delete'``,
                ``'duplicate'``, ``'refresh'``.
        """
        if action == "new":
            self.template_created.emit()
        elif action == "edit" and self._current_template_id is not None:
            self.template_updated.emit(self._current_template_id)
        elif action == "delete" and self._current_template_id is not None:
            if self._confirm_delete(self._current_template_id):
                self.template_deleted.emit(self._current_template_id)
        elif action == "duplicate":
            self.template_created.emit()
        elif action == "refresh":
            pass  # will reload from database later

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

    def _on_selection_changed(self) -> None:
        """Update the details panel when a different row is selected."""
        rows: list[int] = self._table.selectedItems()
        if not rows:
            return
        row: int = rows[0].row()
        item: QTableWidgetItem | None = self._table.item(row, 0)
        if item is None:
            return

        self._current_template_id = row + 1  # placeholder id
        self.template_selected.emit(self._current_template_id)

        # Update information labels with dummy data
        self._info_name.setText(item.text())
        self._info_resolution.setText("600 \u00d7 379 px")
        self._info_created.setText("2026-07-12")
        self._info_updated.setText("2026-07-12")

    def _on_upload_image(self, side: str) -> None:
        """Open a file dialog to select a design image.

        Loads the selected image into the corresponding preview
        widget and emits the appropriate signal.

        Args:
            side: ``'front'`` or ``'back'``.
        """
        path: str
        path, _ = QFileDialog.getOpenFileName(
            self,
            f"Upload {side.title()} Design",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)",
        )
        if not path:
            return

        pixmap: QPixmap = QPixmap(path)
        if pixmap.isNull():
            return

        if side == "front":
            self._front_preview.set_pixmap(pixmap)
            self.front_uploaded.emit(path)
        else:
            self._back_preview.set_pixmap(pixmap)
            self.back_uploaded.emit(path)

        # Update resolution info
        self._info_resolution.setText(f"{pixmap.width()} \u00d7 {pixmap.height()} px")
