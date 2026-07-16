"""Dependent model.

Represents a single dependent record associated with a cardholder.
"""

from dataclasses import dataclass


@dataclass
class Dependent:
    """A dependent person associated with an employee cardholder.

    Attributes:
        id: Unique identifier (``None`` until persisted).
        card_id: Foreign key to the parent ``GeneratedCard``.
        name: Full name of the dependent.
        relation: Relationship to the cardholder (e.g. Son, Wife).
        date_of_birth: Date of birth string (DD-MM-YYYY or YYYY-MM-DD).
        cnic: National ID number of the dependent.
        created_at: ISO-8601 timestamp of creation.
    """

    id: int | None = None
    card_id: int | None = None
    name: str = ""
    relation: str = ""
    date_of_birth: str = ""
    cnic: str = ""
    created_at: str | None = None
