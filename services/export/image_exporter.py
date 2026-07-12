"""High-resolution image export.

Wraps ``RenderService`` at 300 DPI to produce PNG or JPEG card
images.  The output format is determined by the file extension
of the requested output path — ``.jpg`` / ``.jpeg`` produces
JPEG, everything else produces PNG.
"""

from __future__ import annotations

from config.constants import CARD_DPI
from models.field import TemplateField
from models.template import CardTemplate
from services.render_service import RenderService


class ImageExporter:
    """Exports card sides as high-resolution PNG or JPEG images.

    Typical usage::

        exporter = ImageExporter()
        path = exporter.export_front(
            template, fields, field_data, photo_path, "output.png"
        )
    """

    def __init__(self) -> None:
        """Initialise the exporter with a 300 DPI render service."""
        self._render_service: RenderService = RenderService(dpi=CARD_DPI)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def export_front(
        self,
        template: CardTemplate,
        fields: list[TemplateField],
        field_data: dict[str, str],
        photo_path: str | None,
        output_path: str,
    ) -> str:
        """Render and save the front card side.

        Args:
            template: The card template defining layout and images.
            fields: All fields belonging to this template.
            field_data: ``{field_name: value}`` dictionary.
            photo_path: Path to the user's photo, or ``None``.
            output_path: Desired output file path (extension
                determines format).

        Returns:
            The ``output_path`` the image was saved to.
        """
        return self._render_service.render_front(
            template=template,
            fields=fields,
            field_data=field_data,
            photo_path=photo_path,
            output_path=output_path,
        )

    def export_back(
        self,
        template: CardTemplate,
        fields: list[TemplateField],
        field_data: dict[str, str],
        photo_path: str | None,
        output_path: str,
    ) -> str:
        """Render and save the back card side.

        Args:
            template: The card template defining layout and images.
            fields: All fields belonging to this template.
            field_data: ``{field_name: value}`` dictionary.
            photo_path: Path to the user's photo, or ``None``.
            output_path: Desired output file path (extension
                determines format).

        Returns:
            The ``output_path`` the image was saved to.
        """
        return self._render_service.render_back(
            template=template,
            fields=fields,
            field_data=field_data,
            photo_path=photo_path,
            output_path=output_path,
        )
