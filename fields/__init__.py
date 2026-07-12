"""Dynamic Field System.

A reusable, template-type-agnostic field model that supports
every kind of card template (student, employee, hospital,
library, visitor, membership, …).

Typical usage::

    from fields import FieldDefinition, FieldType, validate_field

    field = FieldDefinition(
        field_name="full_name",
        display_name="Full Name",
        field_type=FieldType.TEXT,
        x=10.0,
        y=15.0,
        width=60.0,
        height=8.0,
        required=True,
    )

    errors = validate_field(field)
    if not errors:
        ...  # use the field
"""

from fields.field_type import FieldType
from fields.field_definition import FieldDefinition
from fields.field_validator import (
    FieldValidationError,
    validate_field,
    is_valid_field,
)

__all__ = [
    "FieldType",
    "FieldDefinition",
    "FieldValidationError",
    "validate_field",
    "is_valid_field",
]
