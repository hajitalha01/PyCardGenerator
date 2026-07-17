"""Card History & Search Manager view.

Provides a professional card-history interface with search,
filter, sort, preview, and bulk-action capabilities.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone, timedelta
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.constants import SUPPORTED_IMAGE_FORMATS
from controllers.card_controller import CardController
from controllers.template_controller import TemplateController
from models.card import GeneratedCard
from services.render_service import RenderService
from views.widgets.card_preview_panel import PreviewPanel
from views.widgets.wheel_ignoring_combo import WheelIgnoringComboBox

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _today_range() -> tuple[str, str]:
    """Return ISO-8601 strings for today 00:00:00 — 23:59:59 UTC."""
    now: datetime = datetime.now(timezone.utc)
    start: str = now.strftime("%Y-%m-%dT00:00:00")
    end: str = now.strftime("%Y-%m-%dT23:59:59")
    return start, end


def _week_range() -> tuple[str, str]:
    """Return ISO-8601 range for this week (Mon 00:00 — Sun 23:59 UTC)."""
    now: datetime = datetime.now(timezone.utc)
    monday: datetime = now - timedelta(days=now.weekday())
    start: str = monday.strftime("%Y-%m-%dT00:00:00")
    end: datetime = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return start, end.strftime("%Y-%m-%dT23:59:59")


def _month_range() -> tuple[str, str]:
    """Return ISO-8601 range for this month."""
    now: datetime = datetime.now(timezone.utc)
    start: str = now.replace(day=1).strftime("%Y-%m-%dT00:00:00")
    if now.month == 12:
        end: datetime = now.replace(year=now.year + 1, month=1, day=1)
    else:
        end: datetime = now.replace(month=now.month + 1, day=1)
    end_str: str = (end - timedelta(seconds=1)).strftime("%Y-%m-%dT23:59:59")
    return start, end_str


def _format_datetime(iso_str: str | None) -> str:
    """Format an ISO-8601 string for display (YYYY-MM-DD HH:MM)."""
    if not iso_str:
        return "--"
    try:
        dt: datetime = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return iso_str


# ------------------------------------------------------------------
# Edit-Information dialog
# ------------------------------------------------------------------


class _EditInfoDialog(QDialog):
    """Modal dialog for editing a card's text information fields."""

    def __init__(
        self, card: GeneratedCard, parent: QWidget | None = None
    ) -> None:
        """Initialise with the current card values.

        Args:
            card: The card record whose fields should be edited.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Edit Card Information")
        self.setMinimumWidth(380)

        self._card: GeneratedCard = card

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setSpacing(16)

        form: QFormLayout = QFormLayout()
        form.setSpacing(8)

        self._name_edit: QLineEdit = QLineEdit(card.employee_name or "")
        form.addRow("Employee Name:", self._name_edit)

        self._designation_edit: QLineEdit = QLineEdit(card.designation or "")
        form.addRow("Designation:", self._designation_edit)

        self._category_edit: QLineEdit = QLineEdit(card.employee_category or "")
        form.addRow("Employee Category:", self._category_edit)

        self._blood_group_edit: QLineEdit = QLineEdit(card.blood_group or "")
        form.addRow("Blood Group:", self._blood_group_edit)

        self._location_edit: QLineEdit = QLineEdit(card.location or "")
        form.addRow("Location:", self._location_edit)

        self._dependence_edit: QLineEdit = QLineEdit(card.dependence or "")
        form.addRow("Dependence:", self._dependence_edit)

        layout.addLayout(form)

        buttons: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------

    @property
    def updated_card(self) -> GeneratedCard:
        """Return a copy of the card with the edited fields applied."""
        card = GeneratedCard(
            id=self._card.id,
            template_id=self._card.template_id,
            photo_path=self._card.photo_path,
            employee_name=self._name_edit.text().strip(),
            designation=self._designation_edit.text().strip(),
            employee_category=self._category_edit.text().strip(),
            blood_group=self._blood_group_edit.text().strip(),
            location=self._location_edit.text().strip(),
            dependence=self._dependence_edit.text().strip(),
            front_output=self._card.front_output,
            back_output=self._card.back_output,
            combined_pdf=self._card.combined_pdf,
            created_at=self._card.created_at,
            updated_at=self._card.updated_at,
        )
        return card


# ------------------------------------------------------------------
# Empty-state widget
# ------------------------------------------------------------------


class _EmptyStateWidget(QWidget):
    """Shown when no card records exist or no results match."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise with a friendly placeholder message."""
        super().__init__(parent)
        self.setObjectName("emptyState")

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )

        self._icon_label: QLabel = QLabel("(no cards)")
        self._icon_label.setObjectName("emptyStateIcon")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet("font-size: 40px; color: #888;")
        layout.addWidget(self._icon_label)

        self._message: QLabel = QLabel(
            "No cards have been generated yet.\n"
            "Create a card from the Card Generator page."
        )
        self._message.setObjectName("emptyStateMessage")
        self._message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message.setWordWrap(True)
        layout.addWidget(self._message)

        self._result_count: QLabel = QLabel("")
        self._result_count.setObjectName("emptyStateCount")
        self._result_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_count.setVisible(False)
        layout.addWidget(self._result_count)

    def show_no_results(self, search_text: str) -> None:
        """Update the message for a search with no matches.

        Args:
            search_text: The search query that returned no results.
        """
        self._icon_label.setText("(no results)")
        self._message.setText(
            f"No cards match your search for \"{search_text}\"."
        )
        self._result_count.setVisible(False)

    def show_no_cards(self) -> None:
        """Show the default empty-state message."""
        self._icon_label.setText("(no cards)")
        self._message.setText(
            "No cards have been generated yet.\n"
            "Create a card from the Card Generator page."
        )
        self._result_count.setVisible(False)

    def show_filtered_empty(self, count: int = 0) -> None:
        """Show that filters produced no results.

        Args:
            count: Total card count before filtering.
        """
        self._icon_label.setText("(no matches)")
        if count > 0:
            self._message.setText(
                f"No cards match the current filters "
                f"(out of {count} total)."
            )
        else:
            self._message.setText("No cards match the current filters.")
        self._result_count.setVisible(False)


# ------------------------------------------------------------------
# Main view
# ------------------------------------------------------------------


class CardHistoryView(QWidget):
    """Card history page with search, filter, sort, preview and bulk actions.

    Signals
    -------
    navigate_to_generator:
        Emitted when the user wants to regenerate a card;
        carries (template_id, field_data dict).
    """

    navigate_to_generator = Signal(int, dict)

    # Column indices for the table
    _COL_CHECKBOX: int = 0
    _COL_CARD_ID: int = 1
    _COL_NAME: int = 2
    _COL_TEMPLATE: int = 3
    _COL_DATE: int = 4
    _COL_STATUS: int = 5
    _COL_COUNT: int = 6  # total columns

    def __init__(self) -> None:
        """Initialise the view, controllers and UI."""
        super().__init__()
        self.setObjectName("cardHistoryView")

        self._card_controller: CardController = CardController()
        self._template_controller: TemplateController = TemplateController()
        self._render_service: RenderService = RenderService()

        # Internal state
        self._all_cards: list[tuple[GeneratedCard, str]] = []
        self._current_search: str = ""
        self._current_filter: dict[str, Any] = {
            "date_preset": "all",
            "template_id": None,
        }
        self._current_sort: tuple[str, bool] = ("created_at", False)

        # Debounce timer for search
        self._search_timer: QTimer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._execute_search)

        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Build the complete page layout."""
        root: QVBoxLayout = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(16)

        # Title
        title: QLabel = QLabel("Card History")
        title.setObjectName("viewTitle")
        root.addWidget(title)

        description: QLabel = QLabel(
            "Browse, search and manage all previously generated cards."
        )
        description.setObjectName("viewDescription")
        description.setWordWrap(True)
        root.addWidget(description)

        # --- Search bar ---
        root.addWidget(self._build_search_bar())

        # --- Filter bar ---
        root.addWidget(self._build_filter_bar())

        # --- Stats row ---
        self._stats_label: QLabel = QLabel("")
        self._stats_label.setObjectName("historyStats")
        root.addWidget(self._stats_label)

        # --- Body: table + preview ---
        body: QWidget = QWidget()
        body.setObjectName("viewContent")
        body_layout: QVBoxLayout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        splitter: QSplitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        left_panel: QWidget = QWidget()
        left_layout: QVBoxLayout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        left_layout.addWidget(self._build_table())
        left_layout.addWidget(self._build_bulk_actions())

        splitter.addWidget(left_panel)
        self._preview_panel: PreviewPanel = PreviewPanel()
        splitter.addWidget(self._preview_panel)

        splitter.setStretchFactor(0, 55)
        splitter.setStretchFactor(1, 45)
        splitter.setSizes([600, 400])

        body_layout.addWidget(splitter, stretch=1)
        root.addWidget(body, stretch=1)

        # --- Empty state (overlaid via visibility) ---
        self._empty_state: _EmptyStateWidget = _EmptyStateWidget()
        self._empty_state.setVisible(False)
        root.addWidget(self._empty_state)

        # Initial load
        self._refresh()

    # ------------------------------------------------------------------
    # Search bar
    # ------------------------------------------------------------------

    def _build_search_bar(self) -> QWidget:
        """Construct the search input bar.

        Returns:
            A widget with a search icon and input field.
        """
        bar: QWidget = QWidget()
        bar.setObjectName("historySearchBar")

        layout: QHBoxLayout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)

        self._search_input: QLineEdit = QLineEdit()
        self._search_input.setObjectName("historySearchInput")
        self._search_input.setPlaceholderText(
            "Search by employee name, designation, category, template name or card ID..."
        )
        self._search_input.setClearButtonEnabled(True)
        self._search_input.textChanged.connect(self._on_search_text_changed)
        layout.addWidget(self._search_input, stretch=1)

        clear_btn: QPushButton = QPushButton("Clear")
        clear_btn.setObjectName("toolbarButton")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setToolTip("Clear the search text and show all cards")
        clear_btn.clicked.connect(self._on_clear_search)
        layout.addWidget(clear_btn)

        refresh_btn: QPushButton = QPushButton("Refresh")
        refresh_btn.setObjectName("toolbarButton")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setToolTip("Reload card history from the database")
        refresh_btn.clicked.connect(self._refresh)
        layout.addWidget(refresh_btn)

        return bar

    def _on_search_text_changed(self, text: str) -> None:
        """Restart the debounce timer when search text changes.

        Args:
            text: The new search text.
        """
        self._current_search = text.strip()
        self._search_timer.start()

    def _on_clear_search(self) -> None:
        """Clear the search input and refresh."""
        self._search_input.clear()
        self._current_search = ""

    def _execute_search(self) -> None:
        """Perform the search query and refresh the table."""
        self._refresh()

    # ------------------------------------------------------------------
    # Filter bar
    # ------------------------------------------------------------------

    def _build_filter_bar(self) -> QWidget:
        """Construct the filter bar with date presets and template dropdown.

        Returns:
            A widget containing filter controls.
        """
        bar: QWidget = QWidget()
        bar.setObjectName("historyFilterBar")

        layout: QHBoxLayout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)

        # Date filter group
        date_group: QWidget = QWidget()
        date_layout: QHBoxLayout = QHBoxLayout(date_group)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.setSpacing(4)

        date_label: QLabel = QLabel("Date:")
        date_label.setObjectName("filterLabel")
        date_layout.addWidget(date_label)

        self._date_group: QButtonGroup = QButtonGroup(self)
        date_presets: list[tuple[str, str]] = [
            ("all", "All Time"),
            ("today", "Today"),
            ("week", "This Week"),
            ("month", "This Month"),
        ]
        for preset_id, label_text in date_presets:
            btn: QPushButton = QPushButton(label_text)
            btn.setObjectName("filterButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if preset_id == "all":
                btn.setChecked(True)
            self._date_group.addButton(btn)
            self._date_group.setId(btn, {"all": 0, "today": 1, "week": 2, "month": 3}[preset_id])
            btn.clicked.connect(
                lambda checked=False, pid=preset_id: self._on_date_filter_changed(pid)
            )
            date_layout.addWidget(btn)

        layout.addWidget(date_group)

        # Separator
        sep: QLabel = QLabel("  |  ")
        sep.setObjectName("filterSeparator")
        layout.addWidget(sep)

        # Template filter
        tpl_label: QLabel = QLabel("Template:")
        tpl_label.setObjectName("filterLabel")
        layout.addWidget(tpl_label)

        self._template_filter: QComboBox = WheelIgnoringComboBox()
        self._template_filter.setObjectName("historyTemplateFilter")
        self._template_filter.setMinimumWidth(180)
        self._template_filter.currentIndexChanged.connect(
            self._on_template_filter_changed
        )
        layout.addWidget(self._template_filter)

        layout.addStretch()

        return bar

    def _on_date_filter_changed(self, preset: str) -> None:
        """Handle date-preset button clicks.

        Args:
            preset: One of ``'all'``, ``'today'``, ``'week'``, ``'month'``.
        """
        self._current_filter["date_preset"] = preset
        self._refresh()

    def _on_template_filter_changed(self, index: int) -> None:
        """Handle template combo-box changes.

        Args:
            index: The new combo-box index (0 = all).
        """
        if index <= 0:
            self._current_filter["template_id"] = None
        else:
            tpl_id: Any = self._template_filter.itemData(index)
            self._current_filter["template_id"] = (
                int(tpl_id) if tpl_id is not None else None
            )
        self._refresh()

    def _populate_template_filter(self) -> None:
        """Refresh the template combo-box from the database."""
        current_id: int | None = self._current_filter.get("template_id")
        self._template_filter.blockSignals(True)
        self._template_filter.clear()
        self._template_filter.addItem("All Templates", None)
        try:
            options: dict = self._card_controller.get_filter_options()
            for tpl_id, tpl_name in options.get("templates", []):
                self._template_filter.addItem(tpl_name, tpl_id)
            # Restore selection
            if current_id is not None:
                idx: int = self._template_filter.findData(current_id)
                if idx >= 0:
                    self._template_filter.setCurrentIndex(idx)
                else:
                    self._template_filter.setCurrentIndex(0)
            else:
                self._template_filter.setCurrentIndex(0)
        except Exception:
            self._template_filter.setCurrentIndex(0)
        finally:
            self._template_filter.blockSignals(False)

    # ------------------------------------------------------------------
    # Table
    # ------------------------------------------------------------------

    def _build_table(self) -> QWidget:
        """Construct the card history table.

        Returns:
            A widget containing the QTableWidget.
        """
        panel: QWidget = QWidget()
        panel.setObjectName("historyTablePanel")
        panel.setMinimumWidth(450)

        layout: QVBoxLayout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        heading: QLabel = QLabel("Generated Cards")
        heading.setObjectName("previewTitle")
        layout.addWidget(heading)

        self._table: QTableWidget = QTableWidget(
            0, self._COL_COUNT
        )
        self._table.setObjectName("historyTable")
        self._table.setHorizontalHeaderLabels([
            "", "Card ID", "Employee Name", "Template Name",
            "Generated Date", "Status",
        ])
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setSortingEnabled(True)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(
            self._show_context_menu
        )
        self._table.itemSelectionChanged.connect(
            self._on_selection_changed
        )

        header: QHeaderView = self._table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(
            self._COL_CHECKBOX, QHeaderView.ResizeMode.Fixed
        )
        header.resizeSection(self._COL_CHECKBOX, 40)
        header.setSectionResizeMode(
            self._COL_CARD_ID, QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            self._COL_NAME, QHeaderView.ResizeMode.Stretch
        )
        header.setSectionResizeMode(
            self._COL_TEMPLATE, QHeaderView.ResizeMode.Stretch
        )
        header.setSectionResizeMode(
            self._COL_DATE, QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            self._COL_STATUS, QHeaderView.ResizeMode.ResizeToContents
        )
        # Disable built-in sort (we do server-side or manual)
        self._table.setSortingEnabled(False)
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._on_header_clicked)

        layout.addWidget(self._table)

        return panel

    def _on_header_clicked(self, logical_index: int) -> None:
        """Handle table-header clicks for custom sorting.

        Args:
            logical_index: The column index that was clicked.
        """
        sort_map: dict[int, str] = {
            self._COL_CARD_ID: "created_at",
            self._COL_NAME: "employee_name",
            self._COL_TEMPLATE: "template_name",
            self._COL_DATE: "created_at",
            self._COL_STATUS: "created_at",
        }
        sort_col: str | None = sort_map.get(logical_index)
        if sort_col is None:
            return

        # Toggle direction if same column
        if sort_col == self._current_sort[0]:
            self._current_sort = (sort_col, not self._current_sort[1])
        else:
            self._current_sort = (sort_col, False)

        self._refresh()

    # ------------------------------------------------------------------
    # Bulk-actions toolbar
    # ------------------------------------------------------------------

    def _build_bulk_actions(self) -> QWidget:
        """Construct the bulk-action toolbar below the table.

        Returns:
            A widget with Delete Selected and Export Selected buttons.
        """
        bar: QWidget = QWidget()
        bar.setObjectName("bulkActionsBar")

        layout: QHBoxLayout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)

        select_all: QCheckBox = QCheckBox("Select All")
        select_all.setObjectName("selectAllCheck")
        select_all.setToolTip("Check or uncheck all cards in the list")
        select_all.stateChanged.connect(self._on_select_all)
        layout.addWidget(select_all)

        layout.addStretch()

        export_btn: QPushButton = QPushButton("Export Selected")
        export_btn.setObjectName("actionButton")
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.setToolTip("Copy all output files of selected cards to a folder")
        export_btn.clicked.connect(self._on_export_selected)
        layout.addWidget(export_btn)

        delete_btn: QPushButton = QPushButton("Delete Selected")
        delete_btn.setObjectName("actionButton")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setToolTip("Permanently delete all selected card records")
        delete_btn.clicked.connect(self._on_delete_selected)
        layout.addWidget(delete_btn)

        return bar

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        """Reload all data from the controller and repopulate the table."""
        try:
            self._populate_template_filter()

            date_from: str | None = None
            date_to: str | None = None
            preset: str = self._current_filter.get("date_preset", "all")
            if preset == "today":
                date_from, date_to = _today_range()
            elif preset == "week":
                date_from, date_to = _week_range()
            elif preset == "month":
                date_from, date_to = _month_range()

            template_id: int | None = self._current_filter.get("template_id")
            sort_col, sort_asc = self._current_sort

            self._all_cards = self._card_controller.search(
                search_text=self._current_search,
                template_id=template_id,
                date_from=date_from,
                date_to=date_to,
                sort_by=sort_col,
                sort_asc=sort_asc,
            )

            self._populate_table()
        except Exception:
            self._all_cards = []
            self._populate_table()

    def _populate_table(self) -> None:
        """Fill the table widget from the loaded card data."""
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)

        if not self._all_cards:
            self._table.setVisible(False)
            self._empty_state.setVisible(True)
            if self._current_search:
                self._empty_state.show_no_results(self._current_search)
            elif self._current_filter.get("date_preset") != "all" or \
                    self._current_filter.get("template_id") is not None:
                self._empty_state.show_filtered_empty()
            else:
                self._empty_state.show_no_cards()
            self._stats_label.setText("")
            self._preview_panel.clear()
            return

        self._table.setVisible(True)
        self._empty_state.setVisible(False)

        self._table.setRowCount(len(self._all_cards))

        for row_idx, (card, template_name) in enumerate(self._all_cards):
            # Checkbox
            chk: QTableWidgetItem = QTableWidgetItem("")
            chk.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
            chk.setCheckState(Qt.CheckState.Unchecked)
            chk.setData(Qt.ItemDataRole.UserRole, card.id)
            self._table.setItem(row_idx, self._COL_CHECKBOX, chk)

            # Card ID
            id_item: QTableWidgetItem = QTableWidgetItem(str(card.id))
            id_item.setData(Qt.ItemDataRole.UserRole, card.id)
            self._table.setItem(row_idx, self._COL_CARD_ID, id_item)

            # Name
            name_item: QTableWidgetItem = QTableWidgetItem(
                card.employee_name or "--"
            )
            name_item.setData(Qt.ItemDataRole.UserRole, card.id)
            self._table.setItem(row_idx, self._COL_NAME, name_item)

            # Template
            tpl_item: QTableWidgetItem = QTableWidgetItem(template_name)
            tpl_item.setData(Qt.ItemDataRole.UserRole, card.id)
            self._table.setItem(row_idx, self._COL_TEMPLATE, tpl_item)

            # Date
            date_str: str = _format_datetime(card.created_at)
            date_item: QTableWidgetItem = QTableWidgetItem(date_str)
            date_item.setData(Qt.ItemDataRole.UserRole, card.id)
            self._table.setItem(row_idx, self._COL_DATE, date_item)

            # Status
            status: str = self._card_controller.compute_status(card)
            status_item: QTableWidgetItem = QTableWidgetItem(status)
            status_item.setData(Qt.ItemDataRole.UserRole, card.id)
            self._table.setItem(row_idx, self._COL_STATUS, status_item)

        # Stats
        total: int = len(self._all_cards)
        self._stats_label.setText(
            f"Showing {total} card{'s' if total != 1 else ''}"
        )

        self._table.setSortingEnabled(False)
        self._preview_panel.clear()

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _on_selection_changed(self) -> None:
        """Update the preview panel when the selection changes."""
        selected_rows: set[int] = set()
        for item in self._table.selectedItems():
            selected_rows.add(item.row())

        if len(selected_rows) != 1:
            self._preview_panel.clear()
            return

        row: int = selected_rows.pop()
        if row < 0 or row >= len(self._all_cards):
            self._preview_panel.clear()
            return

        card, template_name = self._all_cards[row]
        status: str = self._card_controller.compute_status(card)

        # Load pixmaps
        front_pix: QPixmap | None = None
        back_pix: QPixmap | None = None

        if card.front_output:
            pix = QPixmap(card.front_output)
            if not pix.isNull():
                front_pix = pix

        if card.back_output:
            pix = QPixmap(card.back_output)
            if not pix.isNull():
                back_pix = pix

        self._preview_panel.show_card(
            card=card,
            template_name=template_name,
            status=status,
            front_pixmap=front_pix,
            back_pixmap=back_pix,
        )

    # ------------------------------------------------------------------
    # Checkbox (Select All)
    # ------------------------------------------------------------------

    def _on_select_all(self, state: int) -> None:
        """Check or uncheck all rows.

        Args:
            state: ``Qt.CheckState.Checked`` or ``Unchecked``.
        """
        checked: bool = state == Qt.CheckState.Checked.value
        for row in range(self._table.rowCount()):
            item: QTableWidgetItem | None = self._table.item(
                row, self._COL_CHECKBOX
            )
            if item is not None:
                item.setCheckState(
                    Qt.CheckState.Checked if checked
                    else Qt.CheckState.Unchecked
                )

    def _get_selected_card_ids(self) -> list[int]:
        """Return the card IDs of all checked rows.

        Returns:
            A list of card identifiers.
        """
        ids: list[int] = []
        for row in range(self._table.rowCount()):
            item: QTableWidgetItem | None = self._table.item(
                row, self._COL_CHECKBOX
            )
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                card_id: Any = item.data(Qt.ItemDataRole.UserRole)
                if card_id is not None:
                    ids.append(int(card_id))
        if not ids:
            # Fallback: use selected rows
            for item in self._table.selectedItems():
                if item.column() == self._COL_CHECKBOX:
                    card_id = item.data(Qt.ItemDataRole.UserRole)
                    if card_id is not None:
                        ids.append(int(card_id))
        return ids

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def _show_context_menu(self, pos) -> None:  # noqa: ANN001
        """Display the right-click context menu for a table row.

        Args:
            pos: The mouse position in table coordinates.
        """
        item: QTableWidgetItem | None = self._table.itemAt(pos)
        if item is None:
            return

        row: int = item.row()
        if row < 0 or row >= len(self._all_cards):
            return

        card, _ = self._all_cards[row]
        menu = self._table.createStandardContextMenu()

        actions: list[tuple[str, str]] = [
            ("Open Preview", "open"),
            ("Edit Information", "edit"),
            ("", ""),  # separator
            ("Regenerate Card", "regenerate"),
            ("Download Again", "download"),
            ("", ""),
            ("Duplicate", "duplicate"),
            ("Delete", "delete"),
        ]

        for label, action in actions:
            if not label:
                menu.addSeparator()
            else:
                qaction: QAction = QAction(label, self)
                qaction.setData(action)
                qaction.triggered.connect(
                    lambda checked=False, a=action, c=card: self._execute_action(
                        a, c
                    )
                )
                menu.addAction(qaction)

        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _execute_action(self, action: str, card: GeneratedCard) -> None:
        """Dispatch a context-menu action.

        Args:
            action: The action identifier string.
            card: The target card record.
        """
        action_map: dict[str, Any] = {
            "open": self._on_open,
            "edit": self._on_edit_info,
            "regenerate": self._on_regenerate,
            "download": self._on_download_again,
            "duplicate": self._on_duplicate,
            "delete": self._on_delete,
        }
        handler = action_map.get(action)
        if handler is not None:
            handler(card)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_open(self, card: GeneratedCard) -> None:
        """Open the preview panel for the given card (select its row).

        Args:
            card: The card record to show.
        """
        for row in range(self._table.rowCount()):
            id_item: QTableWidgetItem | None = self._table.item(
                row, self._COL_CARD_ID
            )
            if id_item is not None:
                cid: Any = id_item.data(Qt.ItemDataRole.UserRole)
                if cid is not None and int(cid) == card.id:
                    self._table.selectRow(row)
                    self._table.scrollToItem(id_item)
                    break

    def _on_edit_info(self, card: GeneratedCard) -> None:
        """Open the edit-information dialog for the given card.

        Args:
            card: The card record to edit.
        """
        dialog: _EditInfoDialog = _EditInfoDialog(card, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated: GeneratedCard = dialog.updated_card
            try:
                self._card_controller.update_card(updated)
                self._refresh()
            except Exception as exc:
                QMessageBox.warning(
                    self,
                    "Update Failed",
                    f"Could not update card information:\n{exc}",
                )

    def _on_regenerate(self, card: GeneratedCard) -> None:
        """Re-render a card using the same data and update its record.

        Args:
            card: The card record to regenerate.
        """
        if card.template_id is None:
            QMessageBox.warning(
                self, "Cannot Regenerate", "This card has no template assigned."
            )
            return

        progress: QProgressDialog = QProgressDialog(
            "Regenerating card...", None, 0, 0, self,
        )
        progress.setWindowTitle("Regenerating")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()

        try:
            template = self._template_controller.get_template_by_id(
                card.template_id
            )
            if template is None:
                QMessageBox.warning(
                    self,
                    "Cannot Regenerate",
                    f"Template id={card.template_id} not found.",
                )
                return

            fields = self._template_controller.load_all_layout(card.template_id)

            field_data: dict[str, str] = {}
            if card.employee_name is not None:
                field_data["employee_name"] = card.employee_name
            if card.designation is not None:
                field_data["designation"] = card.designation
            if card.employee_category is not None:
                field_data["employee_category"] = card.employee_category
            if card.blood_group is not None:
                field_data["blood_group"] = card.blood_group
            if card.location is not None:
                field_data["location"] = card.location
            if card.dependence is not None:
                field_data["dependence"] = card.dependence

            front_path: str = self._render_service.render_front(
                template=template,
                fields=fields,
                field_data=field_data,
                photo_path=card.photo_path,
            )
            back_path: str = self._render_service.render_back(
                template=template,
                fields=fields,
                field_data=field_data,
                photo_path=card.photo_path,
            )

            card.front_output = front_path
            card.back_output = back_path
            self._card_controller.update_card(card)

            self._refresh()
            QMessageBox.information(
                self,
                "Card Regenerated",
                f"Card #{card.id} has been regenerated successfully.",
            )

        except Exception as exc:
            logging.getLogger(__name__).exception(
                "Regeneration failed for card #%s", card.id
            )
            QMessageBox.warning(
                self,
                "Regeneration Failed",
                f"Could not regenerate card:\n{exc}",
            )
        finally:
            progress.close()

    def _on_download_again(self, card: GeneratedCard) -> None:
        """Copy the existing card output to a user-chosen location.

        Args:
            card: The card record whose outputs should be downloaded.
        """
        file_filter: str = "PNG (*.png);;JPEG (*.jpg *.jpeg);;All Files (*)"

        if card.combined_pdf and card.front_output and card.back_output:
            file_filter = "Combined PDF (*.pdf);;Front Image (*.png);;Back Image (*.png);;All Files (*)"
        elif card.combined_pdf:
            file_filter = "PDF (*.pdf);;All Files (*)"

        suggested: str = ""
        if card.employee_name:
            suggested = f"{card.employee_name}"
        suggested = suggested or f"card_{card.id}"

        dst_path: str
        dst_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            f"Download Card #{card.id}",
            suggested,
            file_filter,
        )
        if not dst_path:
            return

        try:
            if card.combined_pdf and ".pdf" in dst_path.lower():
                src: str = card.combined_pdf
            elif card.front_output:
                src = card.front_output
            elif card.back_output:
                src = card.back_output
            else:
                QMessageBox.warning(
                    self,
                    "No Output",
                    "This card has no output files to download.",
                )
                return

            if not src or not os.path.isfile(src):
                QMessageBox.warning(
                    self,
                    "Download Failed",
                    f"Source file not found:\n{src}",
                )
                return

            shutil.copy2(src, dst_path)
            QMessageBox.information(
                self,
                "Download Complete",
                f"File saved to:\n{dst_path}",
            )

        except Exception as exc:
            QMessageBox.warning(
                self,
                "Download Failed",
                f"Could not download file:\n{exc}",
            )

    def _on_duplicate(self, card: GeneratedCard) -> None:
        """Duplicate a card record (re-render with same data).

        Args:
            card: The card record to duplicate.
        """
        if card.template_id is None:
            QMessageBox.warning(
                self, "Cannot Duplicate", "This card has no template assigned."
            )
            return

        progress: QProgressDialog = QProgressDialog(
            "Duplicating card...", None, 0, 0, self,
        )
        progress.setWindowTitle("Duplicating")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()

        try:
            template = self._template_controller.get_template_by_id(
                card.template_id
            )
            if template is None:
                QMessageBox.warning(
                    self,
                    "Cannot Duplicate",
                    f"Template id={card.template_id} not found.",
                )
                return

            fields = self._template_controller.load_all_layout(card.template_id)

            field_data: dict[str, str] = {}
            if card.employee_name is not None:
                field_data["employee_name"] = card.employee_name
            if card.designation is not None:
                field_data["designation"] = card.designation
            if card.employee_category is not None:
                field_data["employee_category"] = card.employee_category
            if card.blood_group is not None:
                field_data["blood_group"] = card.blood_group
            if card.location is not None:
                field_data["location"] = card.location
            if card.dependence is not None:
                field_data["dependence"] = card.dependence

            front_path: str = self._render_service.render_front(
                template=template,
                fields=fields,
                field_data=field_data,
                photo_path=card.photo_path,
            )
            back_path: str = self._render_service.render_back(
                template=template,
                fields=fields,
                field_data=field_data,
                photo_path=card.photo_path,
            )

            duplicate: GeneratedCard = GeneratedCard(
                template_id=card.template_id,
                photo_path=card.photo_path,
                employee_name=card.employee_name,
                designation=card.designation,
                employee_category=card.employee_category,
                blood_group=card.blood_group,
                location=card.location,
                dependence=card.dependence,
                front_output=front_path,
                back_output=back_path,
            )
            self._card_controller.create_card(duplicate)
            self._refresh()

            QMessageBox.information(
                self,
                "Card Duplicated",
                f"Card #{duplicate.id} created from #{card.id}.",
            )

        except Exception as exc:
            logging.getLogger(__name__).exception(
                "Duplication failed for card #%s", card.id
            )
            QMessageBox.warning(
                self,
                "Duplication Failed",
                f"Could not duplicate card:\n{exc}",
            )
        finally:
            progress.close()

    def _on_delete(self, card: GeneratedCard) -> None:
        """Delete a single card record after confirmation.

        Args:
            card: The card record to delete.
        """
        if not self._confirm_delete(f"card #{card.id}"):
            return

        try:
            self._card_controller.delete_card(card.id)
            self._refresh()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Delete Failed",
                f"Could not delete card:\n{exc}",
            )

    # ------------------------------------------------------------------
    # Bulk actions
    # ------------------------------------------------------------------

    def _on_delete_selected(self) -> None:
        """Delete all checked card records after confirmation."""
        ids: list[int] = self._get_selected_card_ids()
        if not ids:
            QMessageBox.information(
                self,
                "No Selection",
                "Please select at least one card to delete.",
            )
            return

        if not self._confirm_delete(f"{len(ids)} card{'s' if len(ids) != 1 else ''}"):
            return

        try:
            self._card_controller.delete_cards(ids)
            self._refresh()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Bulk Delete Failed",
                f"Could not delete cards:\n{exc}",
            )

    def _on_export_selected(self) -> None:
        """Export checked card records to a chosen directory."""
        ids: list[int] = self._get_selected_card_ids()
        if not ids:
            QMessageBox.information(
                self,
                "No Selection",
                "Please select at least one card to export.",
            )
            return

        dst_dir: str = QFileDialog.getExistingDirectory(
            self,
            "Export Cards To",
        )
        if not dst_dir:
            return

        exported: int = 0
        errors: list[str] = []

        try:
            cards: list[GeneratedCard] = self._card_controller.get_cards_by_ids(ids)
            for card in cards:
                try:
                    if card.front_output:
                        dst: str = f"{dst_dir}/card_{card.id}_front.png"
                        shutil.copy2(card.front_output, dst)
                        exported += 1
                    if card.back_output:
                        dst = f"{dst_dir}/card_{card.id}_back.png"
                        shutil.copy2(card.back_output, dst)
                        exported += 1
                    if card.combined_pdf:
                        dst = f"{dst_dir}/card_{card.id}.pdf"
                        shutil.copy2(card.combined_pdf, dst)
                        exported += 1
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"Card #{card.id}: {exc}")

        except Exception as exc:
            QMessageBox.warning(
                self,
                "Export Failed",
                f"Could not retrieve cards:\n{exc}",
            )
            return

        msg: str = f"Exported {exported} file(s) to:\n{dst_dir}"
        if errors:
            msg += f"\n\nErrors:\n" + "\n".join(errors[:5])
        QMessageBox.information(self, "Export Complete", msg)

    # ------------------------------------------------------------------
    # Confirmation dialog
    # ------------------------------------------------------------------

    @staticmethod
    def _confirm_delete(target_description: str) -> bool:
        """Show a confirmation dialog before deleting cards.

        Args:
            target_description: Description of what will be deleted
                (e.g. ``"card #5"`` or ``"3 cards"``).

        Returns:
            ``True`` if the user confirms deletion.
        """
        result: QMessageBox.StandardButton = QMessageBox.warning(
            None,
            "Confirm Deletion",
            f"Are you sure you want to delete {target_description}?\n\n"
            "This action is irreversible and cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return result == QMessageBox.StandardButton.Yes
