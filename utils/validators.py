"""Input and data validation utilities.

Contains validation functions for user-supplied values
entered through the UI forms.  Each ``validate_*`` function
returns a ``(is_valid, error_message)`` tuple.
"""

import re
from datetime import datetime
from pathlib import Path

# ------------------------------------------------------------------
# General-purpose validators (kept from initial scaffold)
# ------------------------------------------------------------------


def is_valid_hex_color(value: str) -> bool:
    """Check whether a string is a valid six-digit hex colour.

    Args:
        value: The colour string to validate (e.g. ``'#FF00AA'``).

    Returns:
        ``True`` if the value matches the hex colour pattern.
    """
    if not value.startswith("#") or len(value) != 7:
        return False
    try:
        int(value[1:], 16)
        return True
    except ValueError:
        return False


def is_valid_image_path(path: str) -> bool:
    """Check whether the given path points to an existing image file.

    Args:
        path: Filesystem path to validate.

    Returns:
        ``True`` if the path exists and has a recognised image extension.
    """
    supported: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".bmp")
    p: Path = Path(path)
    return p.is_file() and p.suffix.lower() in supported


def is_positive_number(value: float) -> bool:
    """Check whether a numeric value is positive.

    Args:
        value: The number to check.

    Returns:
        ``True`` if the value is greater than zero.
    """
    return value > 0


# ------------------------------------------------------------------
# Domain-specific validators
# ------------------------------------------------------------------


def validate_name(value: str) -> tuple[bool, str]:
    """Validate a person's name.

    Rules:
        - Must not be empty.
        - Must contain only letters, spaces, hyphens, apostrophes
          and periods.
        - Length must be between 2 and 100 characters.

    Args:
        value: The name string to validate.

    Returns:
        ``(True, "")`` on success, ``(False, error_message)`` on failure.
    """
    if not value or not value.strip():
        return False, "Name is required."
    if len(value) > 100:
        return False, "Name must not exceed 100 characters."
    if not re.match(r"^[A-Za-zÀ-ÿ\s'.\-]{2,}$", value.strip()):
        return False, "Name contains invalid characters."
    return True, ""


def validate_roll_number(value: str) -> tuple[bool, str]:
    """Validate a student / employee roll number.

    Rules:
        - Must not be empty.
        - Alphanumeric, hyphens, and forward slashes only.
        - Length between 2 and 30 characters.

    Args:
        value: The roll number string to validate.

    Returns:
        ``(True, "")`` on success, ``(False, error_message)`` on failure.
    """
    if not value or not value.strip():
        return False, "Roll number is required."
    if len(value) > 30:
        return False, "Roll number must not exceed 30 characters."
    if not re.match(r"^[A-Za-z0-9\-/]+$", value.strip()):
        return False, "Roll number contains invalid characters."
    return True, ""


def validate_cnic(value: str) -> tuple[bool, str]:
    """Validate a CNIC (Computerised National Identity Card) number.

    Expected format: ``12345-1234567-1`` (5 digits, 7 digits, 1 digit).

    Args:
        value: The CNIC string to validate.

    Returns:
        ``(True, "")`` on success, ``(False, error_message)`` on failure.
    """
    if not value or not value.strip():
        return False, "CNIC is required."
    pattern: str = r"^\d{5}-\d{7}-\d{1}$"
    if not re.match(pattern, value.strip()):
        return False, "CNIC must follow the format 12345-1234567-1."
    return True, ""


def validate_date(value: str) -> tuple[bool, str]:
    """Validate a date string in ``YYYY-MM-DD`` format.

    Args:
        value: The date string to validate.

    Returns:
        ``(True, "")`` on success, ``(False, error_message)`` on failure.
    """
    if not value or not value.strip():
        return False, "Date is required."
    try:
        datetime.strptime(value.strip(), "%Y-%m-%d")
        return True, ""
    except ValueError:
        return False, "Date must be in YYYY-MM-DD format."
