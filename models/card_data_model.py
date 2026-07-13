"""Central data model for card form state.

Holds all user-supplied field values, photo path, and template
selection in one place so that views, preview, save, and export
engines all read from the same source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from models.field import TemplateField


# ------------------------------------------------------------------
# FieldValue — one per form field
# ------------------------------------------------------------------


@dataclass
class FieldValue:
    """Current value and metadata for a single form field.

    Attributes:
        field_name: Programmatic snake_case identifier.
        value: The current user-supplied string value.
        field_type: One of ``FieldType`` values (e.g. ``"text"``,
            ``"date"``, ``"photo"``).
        default_value: Fallback used when the user hasn't entered anything.
        required: Whether a non-empty value must be supplied.
        is_dirty: ``True`` when the value differs from the last
            clean snapshot.
        has_error: ``True`` when the field failed validation.
        error_message: Human-readable description of the validation
            failure.
    """

    field_name: str = ""
    value: str = ""
    field_type: str = "text"
    default_value: str = ""
    required: bool = False
    is_dirty: bool = False
    has_error: bool = False
    error_message: str = ""


# ------------------------------------------------------------------
# CardDataModel — central state container
# ------------------------------------------------------------------


class CardDataModel:
    """Thread-safe-ish central store for all card-generation form data.

    The model owns **user-provided** values only.  Template metadata
    (``CardTemplate``, ``TemplateField`` layout definitions) are
    managed separately by the rendering layer.

    Typical usage::

        model = CardDataModel()
        model.load_template_fields(template_fields)
        model.set_value("employee_name", "John Doe")
        model.set_photo(r"C:\\photos\\john.jpg")
        model.set_template(1, "Employee Card")

        for name, err in model.validate():
            print(f"{name}: {err}")

        state = model.all_values  # {"employee_name": "John Doe", ...}
    """

    def __init__(self) -> None:
        """Initialise an empty data model."""
        self._template_id: int = 0
        self._template_name: str = ""
        self._photo_path: str = ""
        self._fields: dict[str, FieldValue] = {}
        self._clean_snapshot: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def template_id(self) -> int:
        """The currently selected template's database id (0 = none)."""
        return self._template_id

    @template_id.setter
    def template_id(self, value: int) -> None:
        self._template_id = value

    @property
    def template_name(self) -> str:
        """Human-readable name of the selected template."""
        return self._template_name

    @template_name.setter
    def template_name(self, value: str) -> None:
        self._template_name = value

    @property
    def photo_path(self) -> str:
        """Filesystem path to the user's chosen photo."""
        return self._photo_path

    @photo_path.setter
    def photo_path(self, value: str) -> None:
        self._photo_path = value

    # ------------------------------------------------------------------
    # Field management
    # ------------------------------------------------------------------

    def load_template_fields(self, fields: list[TemplateField]) -> None:
        """Populate field metadata from a template's field definitions.

        Each ``TemplateField`` becomes a ``FieldValue`` with its
        ``default_value`` pre-filled as the starting value.

        Args:
            fields: Every field belonging to the current template.
        """
        self._fields.clear()
        for f in fields:
            self._fields[f.field_name] = FieldValue(
                field_name=f.field_name,
                field_type=f.field_type,
                default_value=f.default_value,
                required=f.required,
                value=f.default_value,
            )
        self._take_snapshot()

    def set_value(self, field_name: str, value: str) -> None:
        """Update a single field's value and its dirty flag.

        Args:
            field_name: The field to update.
            value: The new string value.
        """
        field: FieldValue | None = self._fields.get(field_name)
        if field is None:
            # Accept values for unknown fields (dynamic / ad-hoc fields)
            self._fields[field_name] = FieldValue(field_name=field_name, value=value)
            self._clean_snapshot[field_name] = ""
            field = self._fields[field_name]

        field.value = value
        field.is_dirty = (value != self._clean_snapshot.get(field_name, ""))

    def get_value(self, field_name: str) -> str:
        """Return the current value of a field.

        Args:
            field_name: The field to query.

        Returns:
            The current string value, or ``""`` if the field does
            not exist.
        """
        field: FieldValue | None = self._fields.get(field_name)
        return field.value if field is not None else ""

    def get_field_meta(self, field_name: str) -> FieldValue | None:
        """Return the full ``FieldValue`` metadata object.

        Args:
            field_name: The field to look up.

        Returns:
            The ``FieldValue`` instance, or ``None`` if not found.
        """
        return self._fields.get(field_name)

    # ------------------------------------------------------------------
    # Dirty tracking
    # ------------------------------------------------------------------

    @property
    def is_dirty(self) -> bool:
        """``True`` when any field differs from its clean snapshot."""
        return any(f.is_dirty for f in self._fields.values())

    def get_dirty_fields(self) -> list[str]:
        """Return the names of all fields that have been modified.

        Returns:
            A list of ``field_name`` strings (may be empty).
        """
        return [name for name, f in self._fields.items() if f.is_dirty]

    def mark_clean(self) -> None:
        """Accept the current values as the new clean baseline."""
        self._take_snapshot()
        for field in self._fields.values():
            field.is_dirty = False

    def _take_snapshot(self) -> None:
        """Copy every field's current value into the clean snapshot."""
        self._clean_snapshot = {
            name: f.value for name, f in self._fields.items()
        }

    # ------------------------------------------------------------------
    # Reset / Clear
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Revert every field to its clean snapshot value."""
        for name, field in self._fields.items():
            field.value = self._clean_snapshot.get(name, "")
            field.is_dirty = False
            field.has_error = False
            field.error_message = ""

    def clear(self) -> None:
        """Clear all values, photo, and template selection."""
        for field in self._fields.values():
            field.value = ""
            field.is_dirty = False
            field.has_error = False
            field.error_message = ""
        self._photo_path = ""
        self._template_id = 0
        self._template_name = ""

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> list[tuple[str, str]]:
        """Validate every field and return a list of errors.

        Checks:
        - Required fields are non-empty.
        - Date fields contain a valid ``YYYY-MM-DD`` string.

        Each field's ``has_error`` and ``error_message`` attributes
        are updated in place.

        Returns:
            A (possibly empty) list of ``(field_name, error_message)``
            tuples.
        """
        from utils.validators import validate_date  # noqa: PLC0415

        errors: list[tuple[str, str]] = []
        for name, field in self._fields.items():
            field.has_error = False
            field.error_message = ""

            if field.required and not field.value.strip():
                msg: str = f"'{name}' is required."
                field.has_error = True
                field.error_message = msg
                errors.append((name, msg))

            if field.field_type == "date" and field.value:
                valid: bool
                msg: str
                valid, msg = validate_date(field.value)
                if not valid:
                    field.has_error = True
                    field.error_message = msg
                    errors.append((name, msg))

        return errors

    # ------------------------------------------------------------------
    # Bulk access
    # ------------------------------------------------------------------

    @property
    def all_values(self) -> dict[str, str]:
        """Return a ``{field_name: value}`` dict of every current value.

        The returned dict is the primary data source for the rendering
        and export pipelines.
        """
        return {name: f.value for name, f in self._fields.items()}
