"""Card history repository.

Data-access layer for the ``cards`` table.
Encapsulates all SQL operations so that controllers and views
remain decoupled from the database schema.
"""

import sqlite3

from database.db_manager import DatabaseManager
from models.card import GeneratedCard
from utils.helpers import timestamp_now
from utils.logger import setup_logger

logger = setup_logger(__name__)

# ------------------------------------------------------------------
# Row-to-model converter
# ------------------------------------------------------------------


def _row_to_card(row: sqlite3.Row) -> GeneratedCard:
    """Convert a database row to a ``GeneratedCard`` instance."""
    card = GeneratedCard(
        id=row["id"],
        template_id=row["template_id"],
        photo_path=row["photo_path"],
        name=row["name"],
        program=row["program"],
        roll_no=row["roll_no"],
        cnic=row["cnic"],
        expiry_date=row["expiry_date"],
        front_output=row["front_output"],
        back_output=row["back_output"],
        combined_pdf=row["combined_pdf"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
    return card


# ------------------------------------------------------------------
# Repository
# ------------------------------------------------------------------


class CardRepository:
    """Data-access layer for generated card records.

    Every SQL operation related to card-history persistence is
    encapsulated here.

    Usage::

        repo = CardRepository()
        card = repo.create_card(GeneratedCard(name="John Doe", template_id=1))
        cards = repo.search_cards("John", {})
        repo.delete_card(card.id)
    """

    def __init__(self) -> None:
        """Initialise with a reference to the database singleton."""
        self._db: DatabaseManager = DatabaseManager()

    # ------------------------------------------------------------------
    # Single-record CRUD
    # ------------------------------------------------------------------

    def create_card(self, card: GeneratedCard) -> GeneratedCard:
        """Persist a new card record and return it with ``id`` populated.

        Args:
            card: A ``GeneratedCard`` instance (``id`` may be ``None``).

        Returns:
            The same instance with ``id``, ``created_at`` and
            ``updated_at`` filled in.
        """
        now: str = timestamp_now()
        try:
            cursor = self._db.execute(
                """INSERT INTO cards
                   (template_id, photo_path, name, program, roll_no,
                    cnic, expiry_date, front_output, back_output,
                    combined_pdf, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    card.template_id,
                    card.photo_path,
                    card.name,
                    card.program,
                    card.roll_no,
                    card.cnic,
                    card.expiry_date,
                    card.front_output,
                    card.back_output,
                    card.combined_pdf,
                    now,
                    now,
                ),
            )
            card.id = cursor.lastrowid
            card.created_at = now
            card.updated_at = now
            logger.info("Created card id=%d", card.id)
            return card
        except Exception:
            logger.exception("Failed to create card record")
            raise

    def get_card(self, card_id: int) -> GeneratedCard | None:
        """Retrieve a single card record by primary key.

        Args:
            card_id: The card's unique identifier.

        Returns:
            The matching ``GeneratedCard`` or ``None``.
        """
        row = self._db.fetch_one(
            "SELECT * FROM cards WHERE id = ?",
            (card_id,),
        )
        return _row_to_card(row) if row else None

    def update_card(self, card: GeneratedCard) -> None:
        """Persist changes to an existing card record.

        Args:
            card: The ``GeneratedCard`` with updated field values.
                Must have a valid ``id``.
        """
        now: str = timestamp_now()
        try:
            self._db.execute(
                """UPDATE cards SET
                   template_id = ?, photo_path = ?, name = ?, program = ?,
                   roll_no = ?, cnic = ?, expiry_date = ?, front_output = ?,
                   back_output = ?, combined_pdf = ?, updated_at = ?
                   WHERE id = ?""",
                (
                    card.template_id,
                    card.photo_path,
                    card.name,
                    card.program,
                    card.roll_no,
                    card.cnic,
                    card.expiry_date,
                    card.front_output,
                    card.back_output,
                    card.combined_pdf,
                    now,
                    card.id,
                ),
            )
            card.updated_at = now
            logger.info("Updated card id=%d", card.id)
        except Exception:
            logger.exception("Failed to update card id=%d", card.id)
            raise

    def delete_card(self, card_id: int) -> None:
        """Remove a single card record.

        Args:
            card_id: The unique identifier of the card to remove.
        """
        self._db.execute(
            "DELETE FROM cards WHERE id = ?",
            (card_id,),
        )

    def delete_cards(self, card_ids: list[int]) -> None:
        """Remove multiple card records in a single transaction.

        Args:
            card_ids: List of card identifiers to remove.
        """
        if not card_ids:
            return
        placeholders: str = ",".join("?" for _ in card_ids)
        self._db.execute(
            f"DELETE FROM cards WHERE id IN ({placeholders})",  # noqa: S608
            tuple(card_ids),
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_all_cards(self) -> list[GeneratedCard]:
        """Return every card record ordered by most-recently created.

        Returns:
            A list of ``GeneratedCard`` instances (possibly empty).
        """
        rows = self._db.fetch_all(
            "SELECT * FROM cards ORDER BY created_at DESC",
        )
        return [_row_to_card(r) for r in rows]

    def get_cards_by_ids(self, card_ids: list[int]) -> list[GeneratedCard]:
        """Return card records matching the given ids.

        Args:
            card_ids: List of card identifiers.

        Returns:
            A list of ``GeneratedCard`` instances in id order.
        """
        if not card_ids:
            return []
        placeholders: str = ",".join("?" for _ in card_ids)
        rows = self._db.fetch_all(
            f"SELECT * FROM cards WHERE id IN ({placeholders}) "  # noqa: S608
            "ORDER BY created_at DESC",
            tuple(card_ids),
        )
        return [_row_to_card(r) for r in rows]

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_cards(
        self,
        search_text: str = "",
        *,
        template_id: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        status: str | None = None,
        sort_by: str = "created_at",
        sort_asc: bool = False,
    ) -> list[tuple[GeneratedCard, str]]:
        """Search and filter card records, returning each card with its template name.

        Args:
            search_text: Text to match against card name, roll number,
                CNIC, or template name.
            template_id: If provided, only cards using this template.
            date_from: ISO-8601 start date (inclusive).
            date_to: ISO-8601 end date (inclusive).
            status: ``'Has Output'`` or ``'No Output'``.
            sort_by: Column name to sort by (``'created_at'``,
                ``'name'``, ``'template_name'``).
            sort_asc: ``True`` for ascending, ``False`` for descending.

        Returns:
            A list of ``(GeneratedCard, template_name)`` tuples.
        """
        conditions: list[str] = []
        params: list[str | int] = []

        if search_text:
            like_val: str = f"%{search_text}%"
            conditions.append(
                "(c.name LIKE ? OR c.roll_no LIKE ? OR c.cnic LIKE ? "
                "OR t.template_name LIKE ? OR CAST(c.id AS TEXT) LIKE ?)"
            )
            params.extend([like_val] * 5)

        if template_id is not None:
            conditions.append("c.template_id = ?")
            params.append(template_id)

        if date_from:
            conditions.append("c.created_at >= ?")
            params.append(date_from)

        if date_to:
            conditions.append("c.created_at <= ?")
            params.append(date_to)

        if status == "Has Output":
            conditions.append(
                "(c.front_output IS NOT NULL OR c.back_output IS NOT NULL)"
            )
        elif status == "No Output":
            conditions.append(
                "(c.front_output IS NULL AND c.back_output IS NULL)"
            )

        where_clause: str = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # Map sort field to SQL column
        sort_column_map: dict[str, str] = {
            "created_at": "c.created_at",
            "name": "c.name",
            "template_name": "t.template_name",
        }
        sort_col: str = sort_column_map.get(sort_by, "c.created_at")
        sort_dir: str = "ASC" if sort_asc else "DESC"

        query: str = (
            "SELECT c.*, t.template_name "
            "FROM cards c "
            "LEFT JOIN templates t ON c.template_id = t.id "
            f"{where_clause} "
            f"ORDER BY {sort_col} {sort_dir}"
        )

        rows = self._db.fetch_all(query, tuple(params))
        results: list[tuple[GeneratedCard, str]] = []
        for row in rows:
            card = _row_to_card(row)
            tpl_name: str = row["template_name"] if row["template_name"] else "Unknown"
            results.append((card, tpl_name))
        return results

    def get_filter_options(self) -> dict:
        """Return metadata for filter dropdowns.

        Returns:
            A dict with ``templates`` — a list of ``(id, name)`` tuples.
        """
        rows = self._db.fetch_all(
            "SELECT id, template_name FROM templates ORDER BY template_name ASC",
        )
        templates: list[tuple[int, str]] = []
        for row in rows:
            templates.append((row["id"], row["template_name"]))
        return {"templates": templates}
