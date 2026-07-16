"""Generated card model.

Stores metadata about a completed card generation operation,
including the user-provided data and all output file paths.
"""

from dataclasses import dataclass


@dataclass
class GeneratedCard:
    """Metadata for a card that has been generated and saved.

    Attributes:
        id: Unique identifier (``None`` until persisted).
        template_id: Foreign key to the ``CardTemplate`` used.
        photo_path: Path to the user-uploaded photo.
        employee_name: Cardholder employee name.
        designation: Designation / job title.
        employee_category: Employee category.
        blood_group: Blood group.
        location: Location.
        dependence: Dependence.
        dependents: List of dependent dicts associated with this card.
        front_output: Path to the generated front card image.
        back_output: Path to the generated back card image.
        combined_pdf: Path to the combined front + back PDF.
        created_at: ISO-8601 timestamp of generation.
        updated_at: ISO-8601 timestamp of last update.
    """

    id: int | None = None
    template_id: int | None = None
    photo_path: str | None = None
    employee_name: str | None = None
    designation: str | None = None
    employee_category: str | None = None
    blood_group: str | None = None
    location: str | None = None
    dependence: str | None = None
    dependents: list[dict] | None = None
    front_output: str | None = None
    back_output: str | None = None
    combined_pdf: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
