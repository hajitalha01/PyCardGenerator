"""Controller for card history and generation operations.

Coordinates data access for the ``cards`` table, search,
filtering, sorting, and bulk actions.  Reuses the existing
``CardRepository`` data-access layer.
"""

import logging
from datetime import datetime, timezone

from database.card_repository import CardRepository
from models.card import GeneratedCard

logger = logging.getLogger(__name__)


class CardController:
    """Business-logic controller for card history management.

    Provides search, filter, sort, CRUD, and bulk operations.
    Delegates all SQL to ``CardRepository``.

    Usage::

        ctrl = CardController()
        cards = ctrl.search("John", template_id=1)
        ctrl.delete_card(card_id=5)
    """

    def __init__(self) -> None:
        """Initialise the controller and its data-access layer."""
        self._repo: CardRepository = CardRepository()

    # ------------------------------------------------------------------
    # Single-record operations
    # ------------------------------------------------------------------

    def get_card(self, card_id: int) -> GeneratedCard | None:
        """Retrieve a single card record.

        Args:
            card_id: The card's unique identifier.

        Returns:
            The matching ``GeneratedCard`` or ``None``.
        """
        return self._repo.get_card(card_id)

    def create_card(self, card: GeneratedCard) -> GeneratedCard:
        """Persist a new card record.

        Args:
            card: A ``GeneratedCard`` instance (``id`` may be ``None``).

        Returns:
            The same instance with ``id`` and timestamps populated.
        """
        return self._repo.create_card(card)

    def update_card(self, card: GeneratedCard) -> None:
        """Persist changes to an existing card record.

        Args:
            card: The ``GeneratedCard`` with updated fields.
                Must have a valid ``id``.
        """
        self._repo.update_card(card)

    def delete_card(self, card_id: int) -> None:
        """Remove a single card record.

        Args:
            card_id: The unique identifier of the card to remove.
        """
        self._repo.delete_card(card_id)

    def delete_cards(self, card_ids: list[int]) -> None:
        """Remove multiple card records in bulk.

        Args:
            card_ids: List of card identifiers to remove.
        """
        self._repo.delete_cards(card_ids)

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_all_cards(self) -> list[GeneratedCard]:
        """Retrieve all card records.

        Returns:
            A list of ``GeneratedCard`` instances.
        """
        return self._repo.get_all_cards()

    def get_generation_history(
        self,
    ) -> list[tuple[GeneratedCard, str]]:
        """Return all cards with their template names, newest first.

        Returns:
            A list of ``(GeneratedCard, template_name)`` tuples.
        """
        return self._repo.search_cards()

    def get_cards_by_ids(
        self, card_ids: list[int]
    ) -> list[GeneratedCard]:
        """Retrieve specific card records by their identifiers.

        Args:
            card_ids: List of card identifiers.

        Returns:
            A list of matching ``GeneratedCard`` instances.
        """
        return self._repo.get_cards_by_ids(card_ids)

    # ------------------------------------------------------------------
    # Search, filter & sort
    # ------------------------------------------------------------------

    def search(
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
        """Search, filter and sort card records.

        Args:
            search_text: Free-text search (name, roll no, CNIC,
                template name, card ID).
            template_id: Filter by template.
            date_from: ISO-8601 start date (inclusive).
            date_to: ISO-8601 end date (inclusive).
            status: ``'Has Output'``, ``'No Output'``, or ``None``.
            sort_by: Column to sort (``'created_at'``, ``'name'``,
                ``'template_name'``).
            sort_asc: ``True`` for ascending order.

        Returns:
            A list of ``(GeneratedCard, template_name)`` tuples.
        """
        return self._repo.search_cards(
            search_text=search_text,
            template_id=template_id,
            date_from=date_from,
            date_to=date_to,
            status=status,
            sort_by=sort_by,
            sort_asc=sort_asc,
        )

    # ------------------------------------------------------------------
    # Filter options (populate dropdowns)
    # ------------------------------------------------------------------

    def get_filter_options(self) -> dict:
        """Return metadata needed for filter controls.

        Returns:
            A dict with key ``templates`` containing a list of
            ``(id, name)`` tuples.
        """
        return self._repo.get_filter_options()

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    @staticmethod
    def compute_status(card: GeneratedCard) -> str:
        """Derive a human-readable status from the card record.

        Args:
            card: A ``GeneratedCard`` instance.

        Returns:
            ``'Completed'`` if both outputs exist,
            ``'Partial'`` if at least one output exists,
            ``'No Output'`` otherwise.
        """
        has_front: bool = bool(card.front_output)
        has_back: bool = bool(card.back_output)
        if has_front and has_back:
            return "Completed"
        if has_front or has_back:
            return "Partial"
        return "No Output"
