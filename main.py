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
        background-color: #f5f6fa;
        font-family: "Segoe UI", "Arial", sans-serif;
        font-size: 13px;
        color: #2d3436;
    }

    /* ---- Header ---- */
    #header {
        background-color: #ffffff;
        border-bottom: 1px solid #e0e4e8;
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
        color: #636e72;
    }

    /* ---- Sidebar ---- */
    #sidebar {
        background-color: #ffffff;
        border-right: 1px solid #e0e4e8;
    }

    #navButton {
        background-color: transparent;
        color: #555555;
        border: none;
        border-radius: 8px;
        padding: 8px 10px;
        font-size: 13px;
        text-align: left;
        min-width: 36px;
    }
    #navButton:hover {
        background-color: #eef2ff;
        color: #4a6cf7;
    }
    #navButton:checked {
        background-color: #eef2ff;
        color: #4a6cf7;
        font-weight: 600;
    }

    /* ---- Content pages ---- */
    #viewTitle {
        font-size: 22px;
        font-weight: 700;
        color: #1a1a2e;
        padding: 0px;
    }
    #viewDescription {
        font-size: 13px;
        color: #888888;
        line-height: 1.4;
        padding: 0px;
    }
    #viewContent {
        background-color: #ffffff;
        border: 1px solid #e9ecef;
        border-radius: 10px;
    }

    /* ---- Card Generator Toolbar ---- */
    #cardToolbar {
        background-color: #ffffff;
        border-bottom: 1px solid #e9ecef;
    }
    #cardToolbar #toolbarButton {
        background-color: #f0f2f5;
        color: #2d3436;
        border: 1px solid #d5d9e2;
        border-radius: 8px;
        padding: 7px 18px;
        font-size: 12px;
        font-weight: 500;
        min-height: 28px;
    }
    #cardToolbar #toolbarButton:hover {
        background-color: #e4e6f0;
        border-color: #4a6cf7;
        color: #4a6cf7;
    }
    #cardToolbar #toolbarButton:pressed {
        background-color: #d0d4e0;
    }
    #tbSep {
        background-color: #e0e0e0;
        max-width: 1px;
        min-width: 1px;
        min-height: 24px;
    }

    /* ---- Form controls ---- */
    #formScroll {
        background-color: transparent;
        border: none;
    }
    #formContainer {
        background-color: transparent;
    }
    #formPanel {
        background-color: #ffffff;
    }
    #formSectionTitle {
        font-size: 12px;
        font-weight: 700;
        color: #2d3436;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 0px;
    }
    #photoPlaceholder {
        background-color: #f8f9fa;
        border: 2px dashed #d0d0d0;
        border-radius: 10px;
        color: #aaaaaa;
        font-size: 12px;
    }
    #photoButton {
        background-color: #f0f0f0;
        color: #333333;
        border: 1px solid #d0d0d0;
        border-radius: 8px;
        padding: 7px 18px;
        font-size: 12px;
        font-weight: 500;
    }
    #photoButton:hover {
        background-color: #e4e6f0;
        border-color: #4a6cf7;
        color: #4a6cf7;
    }
    #fieldInput {
        background-color: #ffffff;
        border: 1px solid #d5d9e2;
        border-radius: 8px;
        padding: 7px 12px;
        font-size: 13px;
        color: #2d3436;
        min-height: 18px;
    }
    #fieldInput:focus {
        border-color: #4a6cf7;
        background-color: #fcfcff;
    }
    #fieldInput:hover {
        border-color: #b0b8c8;
    }
    #fieldInput[invalid="true"] {
        border: 1px solid #e74c3c;
        background-color: #fef5f5;
    }
    #fieldInput QComboBox::drop-down {
        border: none;
        padding-right: 8px;
    }
    #actionButton {
        background-color: #f0f2f5;
        color: #2d3436;
        border: 1px solid #d5d9e2;
        border-radius: 8px;
        padding: 7px 16px;
        font-size: 12px;
        font-weight: 500;
    }
    #actionButton:hover {
        background-color: #e4e6f0;
        border-color: #4a6cf7;
        color: #4a6cf7;
    }
    #actionButton:disabled {
        background-color: #f8f8f8;
        color: #bbbbbb;
        border-color: #e8e8e8;
    }
    #actionButton:pressed {
        background-color: #d0d4e0;
    }
    #sideTabBtn {
        background-color: #f0f2f5;
        color: #636e72;
        border: 1px solid #d5d9e2;
        border-radius: 8px;
        padding: 6px 18px;
        font-size: 12px;
        font-weight: 500;
    }
    #sideTabBtn:hover {
        background-color: #e4e6f0;
        border-color: #b0b8c8;
    }
    #sideTabBtn:checked {
        background-color: #4a6cf7;
        color: #ffffff;
        border-color: #4a6cf7;
        font-weight: 600;
    }

    /* ---- Preview controls ---- */
    #previewTitle {
        font-size: 14px;
        font-weight: 700;
        color: #2d3436;
        padding: 0px;
    }
    #previewPanel {
        background-color: #ffffff;
        border-left: 1px solid #e9ecef;
    }
    #previewCardTitle {
        font-size: 12px;
        font-weight: 600;
        color: #636e72;
        padding: 0px;
    }
    #cardFrame {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
    }
    #cardPlaceholder {
        color: #aaaaaa;
        font-size: 13px;
    }

    /* ---- Zoom controls ---- */
    #zoomToolbar {
        background-color: transparent;
        padding: 0px;
    }
    #zoomBtn {
        background-color: #f0f2f5;
        color: #2d3436;
        border: 1px solid #d5d9e2;
        border-radius: 8px;
        padding: 5px 14px;
        font-size: 12px;
        font-weight: 500;
        min-height: 24px;
    }
    #zoomBtn:hover {
        background-color: #e4e6f0;
        border-color: #4a6cf7;
        color: #4a6cf7;
    }
    #previewToolBtn {
        background-color: #f0f2f5;
        color: #2d3436;
        border: 1px solid #d5d9e2;
        border-radius: 8px;
        padding: 5px 14px;
        font-size: 12px;
        font-weight: 500;
        min-height: 24px;
    }
    #previewToolBtn:hover {
        background-color: #e4e6f0;
        border-color: #4a6cf7;
        color: #4a6cf7;
    }

    /* ---- Info bar ---- */
    #infoBar {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 6px 12px;
    }
    #infoLabel {
        font-size: 11px;
        color: #888888;
    }

    /* ---- Dependents Panel ---- */
    #dependentsPanel {
        background-color: #ffffff;
        border-top: 1px solid #e9ecef;
        margin: 0px 24px 0px 24px;
    }
    #dependentsTable {
        background-color: #ffffff;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        alternate-background-color: #f8f9fa;
        selection-background-color: #eef2ff;
        selection-color: #2d3436;
        gridline-color: #eceef2;
    }
    #dependentsTable QHeaderView::section {
        background-color: #f8f9fa;
        color: #555555;
        font-weight: 600;
        font-size: 12px;
        padding: 8px 12px;
        border: none;
        border-bottom: 1px solid #dee2e6;
    }
    #dependentsTable::item {
        padding: 6px 12px;
        border: none;
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
    #templateToolbar #toolbarButton {
        background-color: #f0f2f5;
        color: #2d3436;
        border: 1px solid #d5d9e2;
        border-radius: 8px;
        padding: 7px 16px;
        font-size: 12px;
        font-weight: 500;
    }
    #templateToolbar #toolbarButton:hover {
        background-color: #e4e6f0;
        border-color: #4a6cf7;
        color: #4a6cf7;
    }
    #templateListPanel {
        background-color: #ffffff;
    }
    #templateTable {
        background-color: #ffffff;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        alternate-background-color: #f8f9fa;
        selection-background-color: #eef2ff;
        selection-color: #2d3436;
    }
    #templateTable QHeaderView::section {
        background-color: #f8f9fa;
        color: #555555;
        font-weight: 600;
        font-size: 12px;
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
        border-radius: 8px;
    }
    #templateInfoLabel {
        font-size: 12px;
        font-weight: 600;
        color: #636e72;
    }
    #templateInfoValue {
        font-size: 12px;
        color: #2d3436;
    }
    #detailButtons {
        background-color: transparent;
    }

    /* ---- Template Editor ---- */
    #editorToolbar {
        background-color: #ffffff;
        border-bottom: 1px solid #e0e4e8;
    }
    #editorToolbarBtn {
        background-color: transparent;
        color: #555555;
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 5px 12px;
        font-size: 12px;
    }
    #editorToolbarBtn:hover {
        background-color: #eef2ff;
        color: #4a6cf7;
        border-color: #d0d8f0;
    }
    #editorToolbarBtn:checked {
        background-color: #eef2ff;
        color: #4a6cf7;
        font-weight: 600;
    }
    #editorToolbarSep {
        color: #e0e0e0;
        padding: 0px;
        max-width: 2px;
    }
    #propertiesPanel {
        background-color: #ffffff;
        border-right: 1px solid #e0e4e8;
    }
    #propertiesSectionTitle {
        font-size: 11px;
        font-weight: 700;
        color: #888888;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 0px;
    }
    #fieldLabel {
        font-size: 12px;
        color: #636e72;
        min-width: 70px;
    }
    #fieldToolbox {
        background-color: #ffffff;
        border-left: 1px solid #e0e4e8;
    }
    #fieldToolboxBtn {
        background-color: #f8f9fa;
        color: #444444;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 8px 14px;
        font-size: 12px;
        text-align: left;
    }
    #fieldToolboxBtn:hover {
        background-color: #eef2ff;
        color: #4a6cf7;
        border-color: #d0d8f0;
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
        border-top: 1px solid #e0e4e8;
    }
    #inspectorLabel {
        font-size: 13px;
        color: #999999;
        font-style: italic;
    }
    #editorStatusBar {
        background-color: #f8f9fa;
        border-top: 1px solid #e0e4e8;
    }
    #editorStatusLabel {
        font-size: 11px;
        color: #888888;
    }

    /* ---- Status bar ---- */
    #statusBar {
        background-color: #ffffff;
        border-top: 1px solid #e0e4e8;
        font-size: 12px;
        color: #888888;
        padding: 2px 12px;
    }
    #statusBar QLabel {
        padding: 0px 12px;
    }

    /* ---- Scrollbar ---- */
    QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #d0d4e0;
        border-radius: 4px;
        min-height: 30px;
    }
    QScrollBar::handle:vertical:hover {
        background: #b0b8c8;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar:horizontal {
        background: transparent;
        height: 8px;
        margin: 0px;
    }
    QScrollBar::handle:horizontal {
        background: #d0d4e0;
        border-radius: 4px;
        min-width: 30px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #b0b8c8;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }

    /* ---- Tooltips ---- */
    QToolTip {
        background-color: #2d3436;
        color: #ffffff;
        border: none;
        border-radius: 6px;
        padding: 6px 10px;
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
