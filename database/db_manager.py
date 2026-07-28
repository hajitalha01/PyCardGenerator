"""Database connection and schema management.

Provides a singleton DatabaseManager for SQLite connections,
automatic schema initialisation, and helper methods for common
query patterns.

The database file and schema are created automatically on first
connection if they do not already exist.

On first launch (when the writable database does not exist) a
bundled seed database containing default templates is copied to
the writable location, along with the required template background
images.
"""

import shutil
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from config.settings import (
    DATABASE_DIR,
    DATABASE_PATH,
    SCHEMA_PATH,
    TEMPLATE_UPLOADS_DIR,
    ensure_directories,
)
from utils.logger import setup_logger
from utils.resource_path import PathManager

logger = setup_logger(__name__)


class DatabaseManager:
    """Singleton manager for the SQLite database.

    Usage::

        db = DatabaseManager()
        row = db.fetch_one("SELECT * FROM templates WHERE id = ?", (1,))
        rows = db.fetch_all("SELECT * FROM templates")
    """

    _instance: "DatabaseManager | None" = None

    def __new__(cls) -> "DatabaseManager":
        """Return the single existing instance or create one."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            object.__setattr__(cls._instance, "_initialised", False)
        return cls._instance

    def __init__(self) -> None:
        """Initialise paths and connection state (once only)."""
        if self._initialised:
            return
        self._db_path: Path = DATABASE_PATH
        self._schema_path: Path = SCHEMA_PATH
        self._connection: sqlite3.Connection | None = None
        self._schema_initialised: bool = False
        self._initialised: bool = True

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> sqlite3.Connection:
        """Return an active SQLite connection.

        Creates the database directory, database file, and schema
        tables automatically when called for the first time.

        On first launch (writable database does not exist) a bundled
        seed database with default templates is copied to the writable
        location, along with the required template background images.

        Returns:
            An open ``sqlite3.Connection`` with ``row_factory`` set to
            ``sqlite3.Row`` and WAL mode enabled.
        """
        if self._connection is not None:
            return self._connection

        ensure_directories()

        if not self._db_path.exists():
            self._initialise_from_seed()

        logger.info("Opening database at %s", self._db_path)

        self._connection = sqlite3.connect(str(self._db_path), isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")

        if not self._schema_initialised:
            self._initialise_schema()

        return self._connection

    def _initialise_from_seed(self) -> None:
        """Copy the bundled seed database and template images on first launch.

        Only runs when the writable database does not yet exist, so
        existing user databases are never overwritten.
        """
        _pm = PathManager()
        seed: Path = _pm.seed_db_path

        if not seed.exists():
            logger.info("No seed database found at %s; using schema-only init", seed)
            return

        logger.info("First launch detected — copying seed database to %s", self._db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(seed), str(self._db_path))

        bundled_templates: Path = _pm.templates_dir
        if bundled_templates.is_dir():
            TEMPLATE_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
            for img in bundled_templates.iterdir():
                if img.is_file() and img.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp"):
                    dst = TEMPLATE_UPLOADS_DIR / img.name
                    if not dst.exists():
                        shutil.copy2(str(img), str(dst))
                        logger.info("Copied bundled template image: %s", img.name)

        self._schema_initialised = True
        logger.info("Database initialised from seed: %s", self._db_path)
        """Close the database connection if it is open.

        The singleton instance remains valid and will create a fresh
        connection on the next ``connect()`` call.
        """
        if self._connection is not None:
            logger.info("Closing database connection")
            self._connection.close()
            self._connection = None
            self._schema_initialised = False

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _initialise_schema(self) -> None:
        """Execute *schema.sql* against the database.

        This is idempotent — every ``CREATE TABLE`` uses ``IF NOT EXISTS``.
        """
        if not self._schema_path.exists():
            logger.warning("Schema file not found: %s", self._schema_path)
            return

        logger.info("Initialising database schema from %s", self._schema_path)
        schema: str = self._schema_path.read_text(encoding="utf-8")
        self._connection.executescript(schema)
        self._connection.commit()
        self._schema_initialised = True
        logger.info("Schema initialisation complete")

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def execute(
        self, query: str, params: tuple[Any, ...] = ()
    ) -> sqlite3.Cursor:
        """Execute a query and return the cursor.

        Args:
            query: SQL statement to execute.
            params: Positional parameters for the query.

        Returns:
            A ``sqlite3.Cursor`` with any results available.
        """
        conn: sqlite3.Connection = self.connect()
        return conn.execute(query, params)

    def fetch_one(
        self, query: str, params: tuple[Any, ...] = ()
    ) -> sqlite3.Row | None:
        """Execute a query and return the first row.

        Args:
            query: SQL SELECT statement.
            params: Positional parameters for the query.

        Returns:
            A single ``sqlite3.Row``, or ``None`` if no rows matched.
        """
        cursor: sqlite3.Cursor = self.execute(query, params)
        return cursor.fetchone()

    def fetch_all(
        self, query: str, params: tuple[Any, ...] = ()
    ) -> list[sqlite3.Row]:
        """Execute a query and return every matching row.

        Args:
            query: SQL SELECT statement.
            params: Positional parameters for the query.

        Returns:
            A list of ``sqlite3.Row`` objects (possibly empty).
        """
        cursor: sqlite3.Cursor = self.execute(query, params)
        return cursor.fetchall()

    def execute_many(
        self, query: str, params_list: list[tuple[Any, ...]]
    ) -> sqlite3.Cursor:
        """Execute the same query for every parameter set.

        Args:
            query: SQL statement (typically INSERT or UPDATE).
            params_list: Sequence of parameter tuples.

        Returns:
            A ``sqlite3.Cursor``.
        """
        conn: sqlite3.Connection = self.connect()
        return conn.executemany(query, params_list)

    # ------------------------------------------------------------------
    # Transaction helper
    # ------------------------------------------------------------------

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager that commits on success and rolls back on error.

        With ``isolation_level=None`` the connection is in autocommit
        mode, so an explicit ``BEGIN`` is required to group statements.

        Usage::

            with db.transaction() as conn:
                conn.execute("INSERT INTO templates (name) VALUES (?)", ("My Card",))
        """
        conn: sqlite3.Connection = self.connect()
        conn.execute("BEGIN")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("Transaction rolled back")
            raise
