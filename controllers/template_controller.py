"""Controller for template CRUD operations.

Coordinates between the UI layer and the database for all
template- and field-related actions.  Uses ``TemplateRepository``
for persistence and provides validation before every write.
"""

from typing import Any

from database.template_repository import TemplateRepository
from fields.field_type import FieldType
from models.field import TemplateField
from models.template import CardTemplate
from utils.helpers import timestamp_now
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Valid alignment values for field validation
_VALID_ALIGNMENTS: frozenset[str] = frozenset(
    {"left", "center", "right", "justify"}
)


class TemplateController:
    """Orchestrates template creation, retrieval, update, and deletion.

    Every mutating operation validates input before delegating to
    the persistence layer.

    Usage::

        ctrl = TemplateController()
        tpl = ctrl.create_template("Student Card")
        ctrl.save_layout(tpl.id, fields)
        loaded = ctrl.load_layout(tpl.id)
    """

    def __init__(self) -> None:
        """Initialise the controller with a repository and no active template."""
        self._repo: TemplateRepository = TemplateRepository()
        self._current_template: CardTemplate | None = None

    # ------------------------------------------------------------------
    # Current template
    # ------------------------------------------------------------------

    @property
    def current_template(self) -> CardTemplate | None:
        """The template currently being edited, or ``None``."""
        return self._current_template

    @current_template.setter
    def current_template(self, value: CardTemplate | None) -> None:
        """Set the active template."""
        self._current_template = value

    # ------------------------------------------------------------------
    # Name validation
    # ------------------------------------------------------------------

    def validate_template_name(
        self, name: str, exclude_id: int | None = None
    ) -> str | None:
        """Validate a template name.

        Args:
            name: The name to validate.
            exclude_id: Optional id to exclude from the duplicate check
                (used during rename).

        Returns:
            An error message string, or ``None`` if the name is valid.
        """
        if not name or not name.strip():
            return "Template name must not be empty."
        if self._repo.template_name_exists(name.strip(), exclude_id):
            return f"A template named '{name.strip()}' already exists."
        return None

    def _raise_on_invalid_name(
        self, name: str, exclude_id: int | None = None
    ) -> str:
        """Return the stripped name or raise ``ValueError``."""
        error: str | None = self.validate_template_name(name, exclude_id)
        if error:
            raise ValueError(error)
        return name.strip()

    # ------------------------------------------------------------------
    # Field validation
    # ------------------------------------------------------------------

    def validate_field_properties(self, field: TemplateField) -> list[str]:
        """Validate a single field's property values.

        Args:
            field: The ``TemplateField`` to validate.

        Returns:
            A list of error messages (empty = valid).
        """
        errors: list[str] = []

        if not field.field_name or not field.field_name.strip():
            errors.append("Field name must not be empty.")

        if field.width <= 0:
            errors.append(f"Field width must be positive, got {field.width}.")

        if field.height <= 0:
            errors.append(
                f"Field height must be positive, got {field.height}."
            )

        if field.x < 0:
            errors.append(f"Field X must be non-negative, got {field.x}.")

        if field.y < 0:
            errors.append(f"Field Y must be non-negative, got {field.y}.")

        if field.font_size <= 0:
            errors.append(
                f"Font size must be positive, got {field.font_size}."
            )

        if not (0.0 <= field.opacity <= 1.0):
            errors.append(
                f"Opacity must be between 0.0 and 1.0, got "
                f"{field.opacity}."
            )

        if field.alignment not in _VALID_ALIGNMENTS:
            valid: str = ", ".join(sorted(_VALID_ALIGNMENTS))
            errors.append(
                f"Alignment must be one of {valid}, "
                f"got '{field.alignment}'."
            )

        if isinstance(field.field_type, str):
            try:
                FieldType(field.field_type)
            except ValueError:
                errors.append(
                    f"Invalid field type: '{field.field_type}'."
                )

        return errors

    def validate_fields(
        self, fields: list[TemplateField]
    ) -> list[tuple[int, str]]:
        """Validate a list of fields.

        Args:
            fields: The fields to validate.

        Returns:
            A list of ``(index, error_message)`` tuples for invalid
            fields.  An empty list means all fields are valid.
        """
        results: list[tuple[int, str]] = []
        for i, field in enumerate(fields):
            for err in self.validate_field_properties(field):
                results.append((i, err))
        return results

    # ------------------------------------------------------------------
    # Template CRUD
    # ------------------------------------------------------------------

    def create_template(self, name: str) -> CardTemplate:
        """Create and persist a new card template.

        Args:
            name: Display name for the new template.

        Returns:
            The newly created ``CardTemplate`` with ``id`` populated.

        Raises:
            ValueError: If *name* is empty or a duplicate.
        """
        valid_name: str = self._raise_on_invalid_name(name)
        template: CardTemplate = CardTemplate(template_name=valid_name)
        self._repo.create_template(template)
        self._current_template = template
        logger.info("Created template id=%d name='%s'", template.id, template.template_name)
        return template

    def get_all_templates(self) -> list[CardTemplate]:
        """Retrieve every template stored in the database.

        Returns:
            A list of ``CardTemplate`` objects (possibly empty).
        """
        return self._repo.get_all_templates()

    def get_template_by_id(self, template_id: int) -> CardTemplate | None:
        """Retrieve a single template by its primary key.

        Args:
            template_id: The template's unique identifier.

        Returns:
            The matching ``CardTemplate`` or ``None`` if not found.
        """
        template: CardTemplate | None = self._repo.get_template(template_id)
        if template is not None:
            self._current_template = template
        return template

    def update_template(self, template: CardTemplate) -> None:
        """Persist changes made to an existing template.

        Args:
            template: The ``CardTemplate`` instance with updated values.

        Raises:
            ValueError: If the template name is empty or a duplicate.
        """
        self._raise_on_invalid_name(
            template.template_name, exclude_id=template.id
        )
        self._repo.update_template(template)
        if (
            self._current_template is not None
            and self._current_template.id == template.id
        ):
            self._current_template = template
        logger.info(
            "Updated template id=%d name='%s'",
            template.id,
            template.template_name,
        )

    def delete_template(self, template_id: int) -> None:
        """Remove a template and its associated fields from the database.

        Args:
            template_id: The unique identifier of the template to delete.
        """
        self._repo.delete_template(template_id)
        if (
            self._current_template is not None
            and self._current_template.id == template_id
        ):
            self._current_template = None
        logger.info("Deleted template id=%d", template_id)

    def rename_template(self, template_id: int, new_name: str) -> CardTemplate:
        """Rename an existing template.

        Args:
            template_id: The template to rename.
            new_name: The new display name.

        Returns:
            The updated ``CardTemplate``.

        Raises:
            ValueError: If *new_name* is empty or a duplicate.
        """
        valid_name: str = self._raise_on_invalid_name(
            new_name, exclude_id=template_id
        )
        template: CardTemplate | None = self._repo.get_template(template_id)
        if template is None:
            raise ValueError(f"Template id={template_id} not found.")
        template.template_name = valid_name
        self._repo.update_template(template)
        self._current_template = template
        logger.info(
            "Renamed template id=%d to '%s'", template_id, valid_name
        )
        return template

    def duplicate_template(
        self, template_id: int, new_name: str
    ) -> CardTemplate:
        """Duplicate a template and all its fields under a new name.

        Args:
            template_id: The source template to duplicate.
            new_name: Name for the duplicated template.

        Returns:
            The newly created ``CardTemplate`` with its fields saved.

        Raises:
            ValueError: If *new_name* is empty or a duplicate, or if
                the source template is not found.
        """
        valid_name: str = self._raise_on_invalid_name(new_name)

        source: CardTemplate | None = self._repo.get_template(template_id)
        if source is None:
            raise ValueError(
                f"Source template id={template_id} not found."
            )

        # Create the duplicate template shell
        dup: CardTemplate = CardTemplate(
            template_name=valid_name,
            front_image=source.front_image,
            back_image=source.back_image,
            canvas_width=source.canvas_width,
            canvas_height=source.canvas_height,
            grid_size=source.grid_size,
            snap_to_grid=source.snap_to_grid,
            zoom_level=source.zoom_level,
        )
        self._repo.create_template(dup)

        # Duplicate all fields
        fields: list[TemplateField] = self._repo.get_fields(template_id)
        for field in fields:
            field.id = None  # force new PK
            field.created_at = None
        self._repo.save_fields(dup.id, fields)

        self._current_template = dup
        logger.info(
            "Duplicated template id=%d -> id=%d name='%s'",
            template_id,
            dup.id,
            valid_name,
        )
        return dup

    # ------------------------------------------------------------------
    # Layout persistence (fields)
    # ------------------------------------------------------------------

    def save_layout(
        self, template_id: int, fields: list[TemplateField]
    ) -> None:
        """Save all fields for a template, replacing any existing fields.

        Validates every field before persisting.

        Args:
            template_id: The owning template's id.
            fields: The complete list of fields to save.

        Raises:
            ValueError: If any field fails validation.
        """
        field_errors: list[tuple[int, str]] = self.validate_fields(fields)
        if field_errors:
            msg: str = "; ".join(
                f"Field [{idx}] {err}" for idx, err in field_errors
            )
            raise ValueError(f"Field validation failed: {msg}")

        self._repo.save_fields(template_id, fields)
        logger.info(
            "Saved %d fields for template id=%d",
            len(fields),
            template_id,
        )

    def load_layout(self, template_id: int) -> list[TemplateField]:
        """Load all fields for a template.

        Args:
            template_id: The template whose fields should be loaded.

        Returns:
            A list of ``TemplateField`` instances ordered by z_order.
        """
        fields: list[TemplateField] = self._repo.get_fields(template_id)
        logger.info(
            "Loaded %d fields for template id=%d",
            len(fields),
            template_id,
        )
        return fields

    # ------------------------------------------------------------------
    # Full save (template + layout)
    # ------------------------------------------------------------------

    def save_full_template(
        self, template: CardTemplate, fields: list[TemplateField]
    ) -> CardTemplate:
        """Persist the template metadata and all its fields in one call.

        Convenience method that calls ``update_template`` then
        ``save_layout``.

        Args:
            template: The template with any updated metadata.
            fields: The complete list of fields.

        Returns:
            The same template instance after persistence.

        Raises:
            ValueError: If validation fails for either name or fields.
        """
        self.update_template(template)
        if template.id is not None:
            self.save_layout(template.id, fields)
        return template

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def template_count(self) -> int:
        """Return the total number of templates in the database."""
        return len(self._repo.get_all_templates())
