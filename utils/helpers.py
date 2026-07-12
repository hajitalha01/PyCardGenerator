"""General-purpose helper utilities.

Provides small, reusable functions for file operations,
unique identifiers, and timestamps.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path


def generate_unique_id() -> str:
    """Return a short unique identifier string.

    Uses UUID4 without hyphens for concise, collision-resistant IDs.

    Returns:
        A 32-character hexadecimal string.
    """
    return uuid.uuid4().hex


def timestamp_now() -> str:
    """Return the current UTC time as an ISO-8601 string.

    Returns:
        ISO-8601 formatted timestamp (e.g. ``'2026-07-12T08:15:30'``).
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def sanitise_filename(name: str) -> str:
    """Remove or replace characters unsuitable for filenames.

    Args:
        name: The raw string to sanitise.

    Returns:
        A filename-safe string.
    """
    unsafe: str = r'<>:"/\|?*'
    sanitised: str = "".join("_" if c in unsafe else c for c in name)
    return sanitised.strip().strip(".")


# ------------------------------------------------------------------
# File helpers
# ------------------------------------------------------------------


def generate_filename(prefix: str = "card", extension: str = ".png") -> str:
    """Generate a unique filename with the given prefix and extension.

    The resulting name has the form::

        prefix_<32-char-hex><extension>

    Args:
        prefix:   File name prefix (default ``'card'``).
        extension: File extension including the dot (default ``'.png'``).

    Returns:
        A unique filename string.
    """
    return f"{sanitise_filename(prefix)}_{generate_unique_id()}{extension}"


def ensure_dir(path: Path) -> Path:
    """Create a directory if it does not exist and return the path.

    Args:
        path: Filesystem path to a directory.

    Returns:
        The same ``path`` after ensuring it exists.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_extension(path: str) -> str:
    """Extract the lowercased file extension from a path.

    Args:
        path: File path or name.

    Returns:
        The extension including the dot (e.g. ``'.png'``),
        or an empty string if there is no extension.
    """
    return Path(path).suffix.lower()
