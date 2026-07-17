"""High-resolution image export.

Wraps ``RenderService`` at the configured DPI (default 600) to
produce PNG or JPEG card images.  The output format is determined
by the file extension of the requested output path — ``.jpg`` /
``.jpeg`` produces JPEG, everything else produces PNG.
"""

from __future__ import annotations

from config.constants import EXPORT_DPI
from models.field import TemplateField
from models.template import CardTemplate
from services.render_service import RenderService


class ImageExporter:
    """Exports card sides as high-resolution PNG or JPEG images.

    Typical usage::

        exporter = ImageExporter(dpi=600)
        path = exporter.export_front(
            template, fields, field_data, photo_path, "output.png"
        )
    """

    def __init__(self, dpi: int = EXPORT_DPI) -> None:
        """Initialise the exporter with the requested render DPI.

        Args:
            dpi: Output resolution in dots per inch (default 600).
        """
        self._dpi: int = dpi
        self._render_service: RenderService = RenderService(dpi=dpi)

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
        dependents: list[dict] | None = None,
    ) -> str:
        """Render and save the front card side.

        Args:
            template: The card template defining layout and images.
            fields: All fields belonging to this template.
            field_data: ``{field_name: value}`` dictionary.
            photo_path: Path to the user's photo, or ``None``.
            output_path: Desired output file path (extension
                determines format).
            dependents: Optional list of dependent records.

        Returns:
            The ``output_path`` the image was saved to.
        """
        return self._render_service.render_front(
            template=template,
            fields=fields,
            field_data=field_data,
            photo_path=photo_path,
            output_path=output_path,
            dependents=dependents,
        )

    def export_back(
        self,
        template: CardTemplate,
        fields: list[TemplateField],
        field_data: dict[str, str],
        photo_path: str | None,
        output_path: str,
        dependents: list[dict] | None = None,
    ) -> str:
        """Render and save the back card side.

        Args:
            template: The card template defining layout and images.
            fields: All fields belonging to this template.
            field_data: ``{field_name: value}`` dictionary.
            photo_path: Path to the user's photo, or ``None``.
            output_path: Desired output file path (extension
                determines format).
            dependents: Optional list of dependent records.

        Returns:
            The ``output_path`` the image was saved to.
        """
        return self._render_service.render_back(
            template=template,
            fields=fields,
            field_data=field_data,
            photo_path=photo_path,
            output_path=output_path,
            dependents=dependents,
        )
