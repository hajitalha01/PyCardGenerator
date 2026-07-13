"""Template layout repository.

Data-access layer for template and field persistence.
Encapsulates all SQL operations and schema migration so that
controllers and views remain decoupled from the database.
"""

import sqlite3

from database.db_manager import DatabaseManager
from models.field import TemplateField
from models.template import CardTemplate
from utils.helpers import timestamp_now
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Columns that may need to be added to existing tables.
_TEMPLATE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("canvas_width", "REAL NOT NULL DEFAULT 85.6"),
    ("canvas_height", "REAL NOT NULL DEFAULT 54.0"),
    ("grid_size", "INTEGER NOT NULL DEFAULT 10"),
    ("snap_to_grid", "INTEGER NOT NULL DEFAULT 1"),
    ("zoom_level", "REAL NOT NULL DEFAULT 100.0"),
)

_FIELD_COLUMNS: tuple[tuple[str, str], ...] = (
    ("object_type", "TEXT NOT NULL DEFAULT 'text_field'"),
    ("display_name", "TEXT NOT NULL DEFAULT ''"),
    ("background_color", "TEXT NOT NULL DEFAULT '#FFFFFF'"),
    ("underline", "INTEGER NOT NULL DEFAULT 0"),
    ("opacity", "REAL NOT NULL DEFAULT 1.0"),
    ("visible", "INTEGER NOT NULL DEFAULT 1"),
    ("locked", "INTEGER NOT NULL DEFAULT 0"),
    ("required", "INTEGER NOT NULL DEFAULT 0"),
    ("default_value", "TEXT NOT NULL DEFAULT ''"),
    ("z_order", "INTEGER NOT NULL DEFAULT 0"),
)

# ------------------------------------------------------------------
# Row-to-model converters
# ------------------------------------------------------------------


def _row_to_template(row: sqlite3.Row) -> CardTemplate:
    """Convert a database row to a ``CardTemplate`` instance."""
    return CardTemplate(
        id=row["id"],
        template_name=row["template_name"],
        front_image=row["front_image"],
        back_image=row["back_image"],
        canvas_width=row["canvas_width"],
        canvas_height=row["canvas_height"],
        grid_size=row["grid_size"],
        snap_to_grid=bool(row["snap_to_grid"]),
        zoom_level=row["zoom_level"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_field(row: sqlite3.Row) -> TemplateField:
    """Convert a database row to a ``TemplateField`` instance."""
    return TemplateField(
        id=row["id"],
        template_id=row["template_id"],
        object_type=row["object_type"],
        field_name=row["field_name"],
        display_name=row["display_name"],
        field_type=row["field_type"],
        x=row["x"],
        y=row["y"],
        width=row["width"],
        height=row["height"],
        font_family=row["font_family"],
        font_size=row["font_size"],
        font_color=row["font_color"],
        background_color=row["background_color"],
        bold=bool(row["bold"]),
        italic=bool(row["italic"]),
        underline=bool(row["underline"]),
        alignment=row["alignment"],
        rotation=row["rotation"],
        opacity=row["opacity"],
        visible=bool(row["visible"]),
        locked=bool(row["locked"]),
        required=bool(row["required"]),
        default_value=row["default_value"],
        z_order=row["z_order"],
        page_side=row["page_side"],
        created_at=row["created_at"],
    )


class TemplateRepository:
    """Data-access layer for templates and their fields.

    Every SQL operation related to template layout persistence is
    encapsulated here.  Instantiate once — schema migration runs
    automatically on first use.

    Usage::

        repo = TemplateRepository()

        tpl = repo.create_template(CardTemplate(template_name="My Card"))
        fields = repo.get_fields(tpl.id)
    """

    def __init__(self) -> None:
        """Initialise and run schema migration for existing databases."""
        self._db: DatabaseManager = DatabaseManager()
        self._migrate()

    # ------------------------------------------------------------------
    # Schema migration
    # ------------------------------------------------------------------

    def _migrate(self) -> None:
        """Add missing columns to existing *templates* and *template_fields*.

        Each ``ALTER TABLE`` is wrapped in a try/except so that
        columns which already exist are silently ignored.
        """
        for col_name, col_def in _TEMPLATE_COLUMNS:
            try:
                self._db.execute(
                    f"ALTER TABLE templates ADD COLUMN {col_name} {col_def}"  # noqa: S608
                )
                logger.info("Added column templates.%s", col_name)
            except Exception:  # noqa: BLE001
                pass

        for col_name, col_def in _FIELD_COLUMNS:
            try:
                self._db.execute(
                    f"ALTER TABLE template_fields ADD COLUMN {col_name} {col_def}"  # noqa: S608
                )
                logger.info("Added column template_fields.%s", col_name)
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------
    # Template CRUD
    # ------------------------------------------------------------------

    def create_template(self, template: CardTemplate) -> CardTemplate:
        """Persist a new template and return it with ``id`` populated.

        Args:
            template: A ``CardTemplate`` instance (``id`` may be ``None``).

        Returns:
            The same instance with ``id``, ``created_at`` and
            ``updated_at`` filled in.
        """
        now: str = timestamp_now()
        cursor = self._db.execute(
            """INSERT INTO templates
               (template_name, front_image, back_image,
                canvas_width, canvas_height, grid_size,
                snap_to_grid, zoom_level, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                template.template_name,
                template.front_image,
                template.back_image,
                template.canvas_width,
                template.canvas_height,
                template.grid_size,
                int(template.snap_to_grid),
                template.zoom_level,
                now,
                now,
            ),
        )
        template.id = cursor.lastrowid
        template.created_at = now
        template.updated_at = now
        return template

    def get_template(self, template_id: int) -> CardTemplate | None:
        """Retrieve a single template by primary key.

        Args:
            template_id: The template's unique identifier.

        Returns:
            The matching ``CardTemplate`` or ``None``.
        """
        row = self._db.fetch_one(
            "SELECT * FROM templates WHERE id = ?",
            (template_id,),
        )
        return _row_to_template(row) if row else None

    def get_all_templates(self) -> list[CardTemplate]:
        """Return every template ordered by most-recently updated.

        Returns:
            A list of ``CardTemplate`` instances (possibly empty).
        """
        rows = self._db.fetch_all(
            "SELECT * FROM templates ORDER BY updated_at DESC",
        )
        return [_row_to_template(r) for r in rows]

    def update_template(self, template: CardTemplate) -> None:
        """Persist changes to an existing template's columns.

        Args:
            template: The ``CardTemplate`` with updated field values.
                Must have a valid ``id``.
        """
        now: str = timestamp_now()
        self._db.execute(
            """UPDATE templates SET
               template_name = ?, front_image = ?, back_image = ?,
               canvas_width = ?, canvas_height = ?, grid_size = ?,
               snap_to_grid = ?, zoom_level = ?, updated_at = ?
               WHERE id = ?""",
            (
                template.template_name,
                template.front_image,
                template.back_image,
                template.canvas_width,
                template.canvas_height,
                template.grid_size,
                int(template.snap_to_grid),
                template.zoom_level,
                now,
                template.id,
            ),
        )
        template.updated_at = now

    def delete_template(self, template_id: int) -> None:
        """Remove a template (fields are cascade-deleted).

        Args:
            template_id: The unique identifier of the template to remove.
        """
        self._db.execute(
            "DELETE FROM templates WHERE id = ?",
            (template_id,),
        )

    def count_templates_by_image(self, image_path: str) -> int:
        """Count how many templates reference a specific image path.

        Args:
            image_path: The front_image or back_image path to check.

        Returns:
            Number of templates that reference this path.
        """
        row = self._db.fetch_one(
            "SELECT COUNT(*) AS cnt FROM templates "
            "WHERE front_image = ? OR back_image = ?",
            (image_path, image_path),
        )
        return row["cnt"] if row else 0

    def template_name_exists(
        self, name: str, exclude_id: int | None = None
    ) -> bool:
        """Check whether a template with the given name already exists.

        Args:
            name: The template name to check.
            exclude_id: Optional id to exclude from the check
                (used when renaming).

        Returns:
            ``True`` if another template already uses *name*.
        """
        if exclude_id is not None:
            row = self._db.fetch_one(
                "SELECT id FROM templates WHERE template_name = ? AND id != ?",
                (name, exclude_id),
            )
        else:
            row = self._db.fetch_one(
                "SELECT id FROM templates WHERE template_name = ?",
                (name,),
            )
        return row is not None

    # ------------------------------------------------------------------
    # Field CRUD
    # ------------------------------------------------------------------

    def save_fields(
        self, template_id: int, fields: list[TemplateField]
    ) -> None:
        """Replace all fields for a template with the provided list.

        Performs a full delete-and-insert inside a single transaction.

        Args:
            template_id: The owning template's id.
            fields: The complete list of ``TemplateField`` objects.
                Every field will be assigned *template_id*.
        """
        with self._db.transaction() as conn:
            conn.execute(
                "DELETE FROM template_fields WHERE template_id = ?",
                (template_id,),
            )
            now: str = timestamp_now()
            for field in fields:
                field.template_id = template_id
                field.created_at = now
                conn.execute(
                    """INSERT INTO template_fields
                       (template_id, object_type, field_name, display_name,
                        field_type, x, y, width, height, font_family,
                        font_size, font_color, background_color, bold,
                        italic, underline, alignment, rotation, opacity,
                        visible, locked, required, default_value, z_order,
                        page_side, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                               ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                               ?, ?, ?, ?, ?, ?)""",
                    (
                        template_id,
                        field.object_type,
                        field.field_name,
                        field.display_name,
                        field.field_type,
                        field.x,
                        field.y,
                        field.width,
                        field.height,
                        field.font_family,
                        field.font_size,
                        field.font_color,
                        field.background_color,
                        int(field.bold),
                        int(field.italic),
                        int(field.underline),
                        field.alignment,
                        field.rotation,
                        field.opacity,
                        int(field.visible),
                        int(field.locked),
                        int(field.required),
                        field.default_value,
                        field.z_order,
                        field.page_side,
                        now,
                    ),
                )

    def get_fields(self, template_id: int) -> list[TemplateField]:
        """Retrieve all fields for a template ordered by *z_order*.

        Args:
            template_id: The owning template's id.

        Returns:
            A list of ``TemplateField`` instances (possibly empty).
        """
        rows = self._db.fetch_all(
            "SELECT * FROM template_fields WHERE template_id = ? "
            "ORDER BY z_order ASC",
            (template_id,),
        )
        return [_row_to_field(r) for r in rows]

    def delete_fields(self, template_id: int) -> None:
        """Remove all fields belonging to a template.

        Args:
            template_id: The owning template's id.
        """
        self._db.execute(
            "DELETE FROM template_fields WHERE template_id = ?",
            (template_id,),
        )
