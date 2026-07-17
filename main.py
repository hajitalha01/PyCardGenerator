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
from utils.settings_manager import SettingsManager
from utils.theme_manager import ThemeManager
from views.main_window import MainWindow


def _apply_stylesheet(app: QApplication) -> None:
    """Load and apply the user's preferred theme.

    Reads from ``SettingsManager`` and delegates to ``ThemeManager``
    so that dark / light / system themes are all supported.

    Args:
        app: The ``QApplication`` instance to style.
    """
    settings: SettingsManager = SettingsManager()
    theme_mgr: ThemeManager = ThemeManager(app)
    theme_mgr.apply(settings.theme)


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
