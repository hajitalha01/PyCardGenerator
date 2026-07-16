"""Card Generator - Desktop ID Card Application.

Entry point for the application. Initialises logging, ensures
required application directories exist, creates the database
and schema, then displays the main window.
"""

import sys

from PySide6.QtWidgets import QApplication

from config.constants import APP_NAME
from config.settings import ensure_directories
from database.db_manager import DatabaseManager
from utils.logger import setup_logger
from views.main_window import MainWindow


def _apply_stylesheet(app: QApplication) -> None:
    """Load and apply a professional light QSS stylesheet.

    Args:
        app: The ``QApplication`` instance to style.
    """
    stylesheet: str = """
    /* ---- Root ---- */
    QMainWindow, QWidget {
        background-color: #f8f9fa;
        font-family: "Segoe UI", "Arial", sans-serif;
        font-size: 13px;
        color: #333333;
    }

    /* ---- Header ---- */
    #header {
        background-color: #ffffff;
        border-bottom: 1px solid #dee2e6;
    }
    #headerTitle {
        font-size: 15px;
        font-weight: 700;
        color: #1a1a2e;
    }
    #headerVersion {
        font-size: 11px;
        color: #888888;
        margin-left: 6px;
    }
    #headerDate {
        font-size: 12px;
        color: #666666;
    }

    /* ---- Sidebar ---- */
    #sidebar {
        background-color: #ffffff;
        border-right: 1px solid #dee2e6;
    }
    #sidebarTitle {
        font-size: 16px;
        font-weight: 700;
        color: #1a1a2e;
        padding: 0px 16px;
    }
    #sidebarVersion {
        font-size: 11px;
        color: #aaaaaa;
        padding: 8px 0px;
    }

    #navButton {
        background-color: transparent;
        color: #555555;
        border: none;
        border-radius: 8px;
        padding: 8px 14px;
        font-size: 13px;
        text-align: left;
    }
    #navButton:hover {
        background-color: #e8f0fe;
        color: #1a73e8;
    }
    #navButton:checked {
        background-color: #e8f0fe;
        color: #1a73e8;
        font-weight: 600;
    }

    /* ---- Content pages ---- */
    #viewTitle {
        font-size: 26px;
        font-weight: 700;
        color: #1a1a2e;
    }
    #viewDescription {
        font-size: 14px;
        color: #888888;
        line-height: 1.5;
    }
    #viewContent {
        background-color: #ffffff;
        border: 1px solid #e9ecef;
        border-radius: 10px;
    }

    /* ---- Form controls ---- */
    #formScroll {
        background-color: transparent;
    }
    #formContainer {
        background-color: transparent;
    }
    #formSectionTitle {
        font-size: 13px;
        font-weight: 600;
        color: #333333;
    }
    #photoPlaceholder {
        background-color: #f8f9fa;
        border: 2px dashed #cccccc;
        border-radius: 8px;
        color: #aaaaaa;
        font-size: 12px;
    }
    #photoButton {
        background-color: #f0f0f0;
        color: #333333;
        border: 1px solid #cccccc;
        border-radius: 6px;
        padding: 6px 16px;
        font-size: 12px;
    }
    #photoButton:hover {
        background-color: #e4e4e4;
        border-color: #aaaaaa;
    }
    #fieldInput {
        background-color: #ffffff;
        border: 1px solid #d0d0d0;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
        color: #333333;
    }
    #fieldInput:focus {
        border-color: #1a73e8;
    }
    #fieldInput[invalid="true"] {
        border: 1px solid #dc3545;
        background-color: #fff5f5;
    }
    #fieldInput QComboBox::drop-down {
        border: none;
        padding-right: 8px;
    }
    #actionButton {
        background-color: #f0f0f0;
        color: #333333;
        border: 1px solid #cccccc;
        border-radius: 6px;
        padding: 7px 14px;
        font-size: 12px;
    }
    #actionButton:hover {
        background-color: #e4e4e4;
        border-color: #aaaaaa;
    }
    #actionButton:disabled {
        background-color: #f8f8f8;
        color: #bbbbbb;
        border-color: #e0e0e0;
    }
    #sideTabBtn {
        background-color: #f0f0f0;
        color: #666666;
        border: 1px solid #cccccc;
        border-radius: 6px;
        padding: 6px 18px;
        font-size: 12px;
        font-weight: 500;
    }
    #sideTabBtn:hover {
        background-color: #e4e4e4;
        border-color: #aaaaaa;
    }
    #sideTabBtn:checked {
        background-color: #1a73e8;
        color: #ffffff;
        border-color: #1a73e8;
        font-weight: 600;
    }

    /* ---- Preview controls ---- */
    #previewTitle {
        font-size: 13px;
        font-weight: 600;
        color: #555555;
    }
    #previewPanel {
        background-color: #ffffff;
    }
    #previewCardTitle {
        font-size: 12px;
        font-weight: 600;
        color: #666666;
        padding: 0px;
    }
    #cardFrame {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 6px;
    }
    #cardPlaceholder {
        color: #aaaaaa;
        font-size: 13px;
    }

    /* ---- Info bar ---- */
    #infoBar {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 6px;
        padding: 8px 12px;
    }
    #infoLabel {
        font-size: 12px;
        color: #888888;
    }

    /* ---- Divider ---- */
    #divider {
        background-color: #e0e0e0;
    }

    /* ---- Template Manager ---- */
    #templateToolbar {
        background-color: #f8f9fa;
        border-bottom: 1px solid #e9ecef;
    }
    #toolbarButton {
        background-color: #f0f0f0;
        color: #333333;
        border: 1px solid #cccccc;
        border-radius: 6px;
        padding: 6px 14px;
        font-size: 12px;
    }
    #toolbarButton:hover {
        background-color: #e4e4e4;
        border-color: #aaaaaa;
    }
    #templateListPanel {
        background-color: #ffffff;
    }
    #templateTable {
        background-color: #ffffff;
        border: 1px solid #e9ecef;
        border-radius: 6px;
        alternate-background-color: #f8f9fa;
        selection-background-color: #e8f0fe;
        selection-color: #1a1a2e;
    }
    #templateTable QHeaderView::section {
        background-color: #f8f9fa;
        color: #555555;
        font-weight: 600;
        padding: 8px 12px;
        border: none;
        border-bottom: 1px solid #dee2e6;
    }
    #templateTable::item {
        padding: 6px 12px;
        border: none;
    }
    #detailsContainer {
        background-color: transparent;
    }
    #templateInfoSection {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 6px;
    }
    #templateInfoLabel {
        font-size: 12px;
        font-weight: 600;
        color: #666666;
    }
    #templateInfoValue {
        font-size: 12px;
        color: #333333;
    }
    #detailButtons {
        background-color: transparent;
    }

    /* ---- Template Editor ---- */
    #editorToolbar {
        background-color: #ffffff;
        border-bottom: 1px solid #dee2e6;
    }
    #editorToolbarBtn {
        background-color: transparent;
        color: #555555;
        border: 1px solid transparent;
        border-radius: 4px;
        padding: 4px 10px;
        font-size: 12px;
    }
    #editorToolbarBtn:hover {
        background-color: #e8f0fe;
        color: #1a73e8;
        border-color: #c6dafc;
    }
    #editorToolbarBtn:checked {
        background-color: #e8f0fe;
        color: #1a73e8;
        font-weight: 600;
    }
    #editorToolbarSep {
        color: #e0e0e0;
        padding: 0px;
        max-width: 2px;
    }
    #propertiesPanel {
        background-color: #ffffff;
        border-right: 1px solid #dee2e6;
    }
    #propertiesSectionTitle {
        font-size: 11px;
        font-weight: 700;
        color: #888888;
        text-transform: uppercase;
        padding: 0px;
    }
    #fieldLabel {
        font-size: 12px;
        color: #666666;
        min-width: 70px;
    }
    #fieldToolbox {
        background-color: #ffffff;
        border-left: 1px solid #dee2e6;
    }
    #fieldToolboxBtn {
        background-color: #f8f9fa;
        color: #444444;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        padding: 7px 12px;
        font-size: 12px;
        text-align: left;
    }
    #fieldToolboxBtn:hover {
        background-color: #e8f0fe;
        color: #1a73e8;
        border-color: #c6dafc;
    }
    #canvasPanel {
        background-color: #f0f0f0;
    }
    #editorCanvas {
        background-color: transparent;
        border: none;
    }
    #inspectorPanel {
        background-color: #ffffff;
        border-top: 1px solid #dee2e6;
    }
    #inspectorLabel {
        font-size: 13px;
        color: #999999;
        font-style: italic;
    }
    #editorStatusBar {
        background-color: #f8f9fa;
        border-top: 1px solid #dee2e6;
    }
    #editorStatusLabel {
        font-size: 11px;
        color: #888888;
    }

    /* ---- Status bar ---- */
    #statusBar {
        background-color: #ffffff;
        border-top: 1px solid #dee2e6;
        font-size: 12px;
        color: #888888;
        padding: 2px 12px;
    }
    #statusBar QLabel {
        padding: 0px 12px;
    }

    /* ---- Tooltips ---- */
    QToolTip {
        background-color: #333333;
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 12px;
    }
    """
    app.setStyleSheet(stylesheet)


def _initialise_application() -> None:
    """Prepare the runtime environment.

    Creates every required directory, initialises the database
    connection, and applies the schema.
    """
    logger = setup_logger(__name__)

    logger.info("Ensuring application directories exist")
    ensure_directories()

    logger.info("Initialising database")
    db = DatabaseManager()
    db.connect()
    logger.info("Database ready at %s", db)


def main() -> None:
    """Application entry point.

    Sets up logging, directories and the database, then creates
    the Qt application and shows the main window.
    """
    _initialise_application()
    logger = setup_logger(__name__)
    logger.info("Starting %s", APP_NAME)

    app: QApplication = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    _apply_stylesheet(app)

    window: MainWindow = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
