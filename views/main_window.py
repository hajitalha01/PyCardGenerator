"""Main application window.

Provides the primary window frame: a top header bar, a collapsible
left sidebar for navigation, a QStackedWidget for page content,
and a status bar.  The sidebar uses a QButtonGroup so that only
one nav item is active at a time.

Keyboard shortcuts
------------------
Ctrl+N   Navigate to Card Generator
Ctrl+O   Navigate to Template Manager
Ctrl+F   Navigate to Card History
Ctrl+E   Focus the export / download area (Card Generator)
Ctrl+S   Save (Card Generator)

Window state
------------
Geometry and position are persisted via QSettings so that the
window reopens at the same size and location.
"""

from PySide6.QtCore import Qt, QDate, QEasingCurve, QEvent, QSettings, QVariantAnimation, Signal
from PySide6.QtGui import QIcon, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from config.constants import (
    APP_NAME,
    APP_VERSION,
    SIDEBAR_COLLAPSED_WIDTH,
    SIDEBAR_WIDTH,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from controllers.template_controller import TemplateController
from views.card_generator_view import CardGeneratorView
from views.card_history_view import CardHistoryView
from views.dashboard_view import DashboardView
from views.settings_view import SettingsView
from views.template_editor_view import TemplateEditorView
from views.template_manager_view import TemplateManagerView


class _CollapsibleSidebar(QWidget):
    """Sidebar widget that collapses to icons-only on mouse leave."""

    def __init__(self, main_window: QMainWindow, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mw = main_window
        self.setObjectName("sidebar")

    def enterEvent(self, event: QEvent) -> None:
        self._mw._expand_sidebar()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._mw._collapse_sidebar()
        super().leaveEvent(event)


class MainWindow(QMainWindow):
    """Main application window with header, sidebar and stacked content.

    Navigation is handled by a QButtonGroup that ensures exactly
    one sidebar button is checked at any time.  Each button click
    switches the central QStackedWidget to the corresponding page.
    """

    # (text, standard-pixmap-name, stack-index)
    _NAV_ITEMS: list[tuple[str, str, int]] = [
        ("Dashboard",         "SP_ComputerIcon",           0),
        ("Card Generator",    "SP_FileIcon",               1),
        ("Template Manager",  "SP_DirIcon",                2),
        ("Template Editor",   "SP_FileDialogDetailedView", 3),
        ("Card History",      "SP_FileDialogListView",     4),
        ("Settings",          "SP_DialogApplyButton",      5),
    ]

    navigation_changed = Signal(int)

    def __init__(self) -> None:
        """Initialise the window, header, sidebar, views and status bar."""
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        self._nav_group: QButtonGroup = QButtonGroup(self)
        self._stack: QStackedWidget = self._build_views()

        self.navigation_changed.connect(self._on_navigation_changed)

        self._setup_ui()
        self._setup_status_bar()
        self._setup_shortcuts()
        self._restore_window_state()
        self._navigate_to(0)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Build the complete window layout."""
        central: QWidget = QWidget()
        self.setCentralWidget(central)

        root_layout: QVBoxLayout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_header())

        body: QWidget = QWidget()
        body_layout: QHBoxLayout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self._sidebar = self._build_sidebar()
        body_layout.addWidget(self._sidebar)
        body_layout.addWidget(self._stack, stretch=1)

        root_layout.addWidget(body, stretch=1)

    def _build_header(self) -> QWidget:
        """Construct the top header bar.

        Returns:
            A widget containing the application name, version and
            current date aligned horizontally.
        """
        header: QWidget = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(52)

        layout: QHBoxLayout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)

        title: QLabel = QLabel(APP_NAME)
        title.setObjectName("headerTitle")
        layout.addWidget(title)

        version: QLabel = QLabel(f"v{APP_VERSION}")
        version.setObjectName("headerVersion")
        layout.addWidget(version)

        layout.addStretch()

        today: QLabel = QLabel(
            QDate.currentDate().toString("dddd, d MMMM yyyy")
        )
        today.setObjectName("headerDate")
        layout.addWidget(today)

        return header

    def _build_sidebar(self) -> QWidget:
        """Construct the collapsible navigation sidebar.

        Returns:
            A sidebar widget that collapses to icons-only and
            expands smoothly on mouse hover.
        """
        sidebar: _CollapsibleSidebar = _CollapsibleSidebar(self)
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(SIDEBAR_COLLAPSED_WIDTH)

        layout: QVBoxLayout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 16, 8, 12)
        layout.setSpacing(2)

        self._nav_buttons: list[QPushButton] = []
        self._nav_button_texts: list[str] = []

        for text, pixmap_name, index in self._NAV_ITEMS:
            icon: QIcon = QApplication.style().standardIcon(
                getattr(QStyle.StandardPixmap, pixmap_name)
            )
            button: QPushButton = QPushButton(icon, "")
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setMinimumHeight(40)
            button.setToolTip(text)

            self._nav_group.addButton(button, index)
            layout.addWidget(button)
            self._nav_buttons.append(button)
            self._nav_button_texts.append(text)

        layout.addStretch()

        self._nav_group.idClicked.connect(self._navigate_to)

        self._sidebar_collapsed: bool = True
        self._sidebar_anim = QVariantAnimation(self)
        self._sidebar_anim.setDuration(200)
        self._sidebar_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._sidebar_anim.valueChanged.connect(self._on_sidebar_anim)

        return sidebar

    def _expand_sidebar(self) -> None:
        """Animate the sidebar to its full width and show button text."""
        if not self._sidebar_collapsed:
            return
        self._sidebar_anim.stop()
        self._sidebar_collapsed = False
        self._restore_nav_text()
        self._start_sidebar_anim(
            self._sidebar.width(), SIDEBAR_WIDTH
        )

    def _collapse_sidebar(self) -> None:
        """Hide button text and animate the sidebar to collapsed width."""
        if self._sidebar_collapsed:
            return
        self._sidebar_anim.stop()
        self._hide_nav_text()
        self._sidebar_collapsed = True
        self._start_sidebar_anim(
            self._sidebar.width(), SIDEBAR_COLLAPSED_WIDTH
        )

    def _start_sidebar_anim(self, start: int, end: int) -> None:
        """Start sidebar width animation.

        Args:
            start: Starting width in pixels.
            end: Target width in pixels.
        """
        self._sidebar_anim.setStartValue(start)
        self._sidebar_anim.setEndValue(end)
        self._sidebar_anim.start()

    def _on_sidebar_anim(self, value: int) -> None:
        """Update sidebar fixed width during animation.

        Args:
            value: Current animation value (width in pixels).
        """
        self._sidebar.setFixedWidth(value)

    def _hide_nav_text(self) -> None:
        """Clear button text so only icons remain visible."""
        for btn in self._nav_buttons:
            btn.setText("")

    def _restore_nav_text(self) -> None:
        """Restore original button text."""
        for btn, text in zip(self._nav_buttons, self._nav_button_texts, strict=False):
            btn.setText(text)

    def _build_views(self) -> QStackedWidget:
        """Create all child views and embed them in a QStackedWidget.

        Returns:
            A QStackedWidget containing every application view.
        """
        stack: QStackedWidget = QStackedWidget()

        self._dashboard_view: DashboardView = DashboardView()
        self._card_generator_view: CardGeneratorView = CardGeneratorView()
        self._template_manager_view: TemplateManagerView = TemplateManagerView()
        self._template_editor_view: TemplateEditorView = TemplateEditorView()
        self._card_history_view: CardHistoryView = CardHistoryView()
        self._settings_view: SettingsView = SettingsView()

        stack.addWidget(self._dashboard_view)
        stack.addWidget(self._card_generator_view)
        stack.addWidget(self._template_manager_view)
        stack.addWidget(self._template_editor_view)
        stack.addWidget(self._card_history_view)
        stack.addWidget(self._settings_view)

        # Wire template manager open_in_editor → load template + navigate
        self._template_manager_view.open_in_editor.connect(
            self._on_open_template_in_editor
        )

        # Wire template editor save_requested → save template
        self._template_editor_view.save_requested.connect(
            self._template_editor_view._on_save
        )

        # Wire template editor open_requested → show template picker
        self._template_editor_view.open_requested.connect(
            self._on_open_template_from_editor
        )

        return stack

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    def _setup_shortcuts(self) -> None:
        """Register global keyboard shortcuts for the main window.

        Shortcuts are connected to navigation or status bar hints.
        """
        shortcuts: list[tuple[str, str, int | None]] = [
            ("Ctrl+N", "Navigate to Card Generator", 1),
            ("Ctrl+O", "Navigate to Template Manager", 2),
            ("Ctrl+F", "Navigate to Card History", 4),
            ("Ctrl+E", "Switch to Card Generator for export", 1),
            ("Ctrl+S", "Save (focused view handles it)", None),
        ]

        for key_seq, hint, nav_index in shortcuts:
            shortcut: QShortcut = QShortcut(QKeySequence(key_seq), self)
            if nav_index is not None:
                shortcut.activated.connect(
                    lambda checked=False, idx=nav_index: self._navigate_to(idx)
                )
            else:
                shortcut.activated.connect(
                    lambda: self.statusBar().showMessage("Save", 3000)
                )

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _setup_status_bar(self) -> None:
        """Configure the status bar with a default 'Ready' message."""
        bar: QStatusBar = self.statusBar()
        bar.setObjectName("statusBar")
        bar.showMessage("Ready")

    # ------------------------------------------------------------------
    # Window state persistence
    # ------------------------------------------------------------------

    def _restore_window_state(self) -> None:
        """Restore the window geometry and position from QSettings."""
        settings: QSettings = QSettings(APP_NAME, APP_NAME)
        geom: bytes | None = settings.value("main_window/geometry")
        state: bytes | None = settings.value("main_window/state")
        if geom is not None:
            self.restoreGeometry(geom)
        if state is not None:
            self.restoreState(state)

    def closeEvent(self, event) -> None:  # noqa: N802
        """Save the window geometry and position before closing.

        Args:
            event: The close event.
        """
        settings: QSettings = QSettings(APP_NAME, APP_NAME)
        settings.setValue("main_window/geometry", self.saveGeometry())
        settings.setValue("main_window/state", self.saveState())
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _navigate_to(self, index: int) -> None:
        """Emit ``navigation_changed`` to switch the active view.

        This method is connected to the button-group ``idClicked``
        signal and to ``navigation_changed`` which performs the
        actual switch.

        Args:
            index: The QStackedWidget index of the target page.
        """
        self.navigation_changed.emit(index)

    def _on_open_template_in_editor(self, template_id: int) -> None:
        """Load a template into the editor and navigate to it.

        Args:
            template_id: The primary key of the template to load.
        """
        self._template_editor_view.load_template(template_id)
        self._navigate_to(3)  # Template Editor is at index 3

    def _on_open_template_from_editor(self) -> None:
        """Show a template selection dialog and load the chosen template."""
        ctrl: TemplateController = TemplateController()
        templates = ctrl.get_all_templates()
        if not templates:
            QMessageBox.information(self, "No Templates", "No templates found in the database.")
            return

        names: list[str] = [t.template_name for t in templates]
        name, ok = QInputDialog.getItem(
            self, "Open Template", "Select a template:", names, 0, False
        )
        if ok and name:
            matching = [t for t in templates if t.template_name == name]
            if matching and matching[0].id is not None:
                self._on_open_template_in_editor(matching[0].id)

    def _on_navigation_changed(self, index: int) -> None:
        """Perform the view switch and update the sidebar highlight.

        Args:
            index: The QStackedWidget index of the target page.
        """
        self._stack.setCurrentIndex(index)
        button: QPushButton | None = self._nav_group.button(index)
        if button is not None:
            button.setChecked(True)
