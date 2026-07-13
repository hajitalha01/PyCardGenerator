"""Human-readable, unique filename generation for exported cards.

Builds descriptive filenames from field data (e.g. name + roll
number) and appends a uniqueness counter when a file already
exists at the target path.
"""

from __future__ import annotations

from pathlib import Path

from utils.helpers import sanitise_filename


class FileNameGenerator:
    """Generates descriptive, collision-free filenames for card exports.

    Typical usage::

        # Suggested name for a front-card PNG
        name = FileNameGenerator.generate_front_name(
            {"employee_name": "John Doe"}, ".png"
        )
        # -> "JohnDoe_Front.png"

        # Avoid overwrites
        unique = FileNameGenerator.ensure_unique(
            "/out/JohnDoe_Front.png"
        )
        # -> "/out/JohnDoe_Front_1.png" (if original exists)
    """

    _DEFAULT_IDENTIFIER: str = "Card"

    # ------------------------------------------------------------------
    # Identifier helpers
    # ------------------------------------------------------------------

    @classmethod
    def _get_identifier(cls, field_data: dict[str, str]) -> str:
        """Build a short identifier from the field data.

        Uses ``employee_name`` when available; falls back to
        ``"Card"``.

        Args:
            field_data: ``{field_name: value}`` dict from the model.

        Returns:
            A human-readable identifier string.
        """
        name: str = field_data.get("employee_name", "").strip()
        if name:
            return name
        return cls._DEFAULT_IDENTIFIER

    @classmethod
    def _sanitise(cls, text: str) -> str:
        """Remove characters unsafe for filenames.

        Args:
            text: Raw text.

        Returns:
            Filename-safe string.
        """
        return sanitise_filename(text)

    # ------------------------------------------------------------------
    # Public generators
    # ------------------------------------------------------------------

    @classmethod
    def generate_front_name(
        cls,
        field_data: dict[str, str],
        extension: str = ".png",
    ) -> str:
        """Generate a filename for a front-card export.

        Format: ``{Identifier}_Front{extension}``

        Args:
            field_data: Current field values from the data model.
            extension: File extension including the dot.

        Returns:
            A filename string (no directory component).
        """
        ident: str = cls._sanitise(cls._get_identifier(field_data))
        return f"{ident}_Front{extension}"

    @classmethod
    def generate_back_name(
        cls,
        field_data: dict[str, str],
        extension: str = ".png",
    ) -> str:
        """Generate a filename for a back-card export.

        Format: ``{Identifier}_Back{extension}``

        Args:
            field_data: Current field values from the data model.
            extension: File extension including the dot.

        Returns:
            A filename string (no directory component).
        """
        ident: str = cls._sanitise(cls._get_identifier(field_data))
        return f"{ident}_Back{extension}"

    @classmethod
    def generate_combined_name(
        cls,
        field_data: dict[str, str],
    ) -> str:
        """Generate a filename for a combined (front + back) PDF export.

        Format: ``{Identifier}.pdf``

        Args:
            field_data: Current field values from the data model.

        Returns:
            A filename string (no directory component).
        """
        ident: str = cls._sanitise(cls._get_identifier(field_data))
        return f"{ident}.pdf"

    # ------------------------------------------------------------------
    # Collision avoidance
    # ------------------------------------------------------------------

    @classmethod
    def ensure_unique(cls, path: str) -> str:
        """Return a path that does not already exist on disk.

        If a file already exists at *path*, appends ``_1``, ``_2``,
        etc. before the extension until a free name is found.

        Args:
            path: The desired output path.

        Returns:
            A unique path string.
        """
        p: Path = Path(path)
        if not p.exists():
            return str(p)

        stem: str = p.stem
        suffix: str = p.suffix
        parent: Path = p.parent
        counter: int = 1

        while True:
            candidate: Path = parent / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return str(candidate)
            counter += 1
