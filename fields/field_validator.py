"""Field definition validation.

Validates a ``FieldDefinition`` instance against structural
and business rules.  Each check is a small, focused function
so they can be composed, extended, or skipped individually.
"""

from fields.field_definition import FieldDefinition
from fields.field_type import FieldType

# Valid alignment values
_VALID_ALIGNMENTS: frozenset[str] = frozenset(
    {"left", "center", "right", "justify"}
)


class FieldValidationError(Exception):
    """Raised when field validation fails irrecoverably."""


def _check_name(field: FieldDefinition, errors: list[str]) -> None:
    """Append an error if ``field_name`` is empty or whitespace-only."""
    if not field.field_name or not field.field_name.strip():
        errors.append("Field name must not be empty")


def _check_display_name(field: FieldDefinition, errors: list[str]) -> None:
    """Append an error if ``display_name`` is empty or whitespace-only."""
    if not field.display_name or not field.display_name.strip():
        errors.append("Display name must not be empty")


def _check_size(field: FieldDefinition, errors: list[str]) -> None:
    """Append errors if width or height are non-positive."""
    if field.width <= 0:
        errors.append(f"Width must be positive, got {field.width}")
    if field.height <= 0:
        errors.append(f"Height must be positive, got {field.height}")


def _check_coordinates(field: FieldDefinition, errors: list[str]) -> None:
    """Append errors if x or y are negative."""
    if field.x < 0:
        errors.append(f"X coordinate must be non-negative, got {field.x}")
    if field.y < 0:
        errors.append(f"Y coordinate must be non-negative, got {field.y}")


def _check_font_size(field: FieldDefinition, errors: list[str]) -> None:
    """Append an error if ``font_size`` is not positive."""
    if field.font_size <= 0:
        errors.append(
            f"Font size must be positive, got {field.font_size}"
        )


def _check_opacity(field: FieldDefinition, errors: list[str]) -> None:
    """Append an error if ``opacity`` is outside the 0.0-1.0 range."""
    if not 0.0 <= field.opacity <= 1.0:
        errors.append(
            f"Opacity must be between 0.0 and 1.0, got {field.opacity}"
        )


def _check_alignment(field: FieldDefinition, errors: list[str]) -> None:
    """Append an error if ``alignment`` is not a recognised value."""
    if field.alignment not in _VALID_ALIGNMENTS:
        valid = ", ".join(sorted(_VALID_ALIGNMENTS))
        errors.append(
            f"Alignment must be one of {valid}, got '{field.alignment}'"
        )


def _check_field_type(field: FieldDefinition, errors: list[str]) -> None:
    """Append an error if ``field_type`` is not a recognised type."""
    if isinstance(field.field_type, str):
        try:
            FieldType(field.field_type)
        except ValueError:
            errors.append(
                f"Invalid field type: '{field.field_type}'"
            )
    elif not isinstance(field.field_type, FieldType):
        errors.append(
            f"Field type must be a FieldType enum or valid string, "
            f"got {type(field.field_type).__name__}"
        )


def validate_field(field: FieldDefinition) -> list[str]:
    """Run all validation checks against a field definition.

    Args:
        field: The ``FieldDefinition`` instance to validate.

    Returns:
        A list of human-readable validation error messages.
        An empty list means the field is valid.
    """
    errors: list[str] = []

    _check_name(field, errors)
    _check_display_name(field, errors)
    _check_size(field, errors)
    _check_coordinates(field, errors)
    _check_font_size(field, errors)
    _check_opacity(field, errors)
    _check_alignment(field, errors)
    _check_field_type(field, errors)

    return errors


def is_valid_field(field: FieldDefinition) -> bool:
    """Return ``True`` when the field passes all validation checks.

    Args:
        field: The ``FieldDefinition`` instance to validate.

    Returns:
        ``True`` if the field has no validation errors.
    """
    return len(validate_field(field)) == 0
