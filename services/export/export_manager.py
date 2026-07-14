"""Export manager — orchestrates the full export workflow.

Coordinates validation, high-resolution image rendering, PDF
assembly, and temporary-file cleanup.  The single entry point
for all export operations from the UI layer.
"""

from __future__ import annotations

from pathlib import Path

from config.settings import GENERATED_CARDS_DIR
from controllers.binding_manager import BindingManager
from controllers.template_controller import TemplateController
from models.field import TemplateField
from models.template import CardTemplate
from services.export.exceptions import ExportError
from services.export.export_validator import ExportValidator
from services.export.file_name_generator import FileNameGenerator
from services.export.image_exporter import ImageExporter
from services.export.pdf_exporter import PDFExporter
from utils.helpers import generate_filename
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ExportManager:
    """Orchestrates card export to image or PDF formats.

    Owns the exporters, validator, and filename generator.
    Accepts a ``BindingManager`` (for field values and photo
    path) and a ``TemplateController`` (for loading template
    metadata from the database).

    Usage::

        mgr = ExportManager(binding_manager, template_controller)
        path = mgr.export_front("/out/John_Front.png")
    """

    def __init__(
        self,
        binding_manager: BindingManager,
        template_controller: TemplateController,
    ) -> None:
        """Initialise the export manager.

        Args:
            binding_manager: Provides the current field values
                and photo path via ``.model``.
            template_controller: Template repository for loading
                ``CardTemplate`` and ``TemplateField`` objects.
        """
        self._binding_manager: BindingManager = binding_manager
        self._template_ctrl: TemplateController = template_controller
        self._image_exporter: ImageExporter = ImageExporter()
        self._pdf_exporter: PDFExporter = PDFExporter()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def export_front(self, output_path: str) -> str:
        """Export the front card side as an image.

        Args:
            output_path: Full path where the image should be saved.
                File extension (``.png``, ``.jpg``, ``.jpeg``)
                determines the output format.

        Returns:
            The ``output_path`` the file was saved to.

        Raises:
            ExportError: If validation fails or rendering fails.
        """
        errors: list[str] = ExportValidator.validate(
            self._binding_manager, self._template_ctrl
        )
        if errors:
            raise ExportError("\n".join(errors))

        model = self._binding_manager.model
        template: CardTemplate
        fields: list[TemplateField]
        template, fields = self._load_template_data()

        logger.info(
            "Exporting front card to %s", output_path
        )
        return self._image_exporter.export_front(
            template=template,
            fields=fields,
            field_data=model.all_values,
            photo_path=model.photo_path or None,
            output_path=output_path,
        )

    def export_back(self, output_path: str) -> str:
        """Export the back card side as an image.

        Args:
            output_path: Full path where the image should be saved.
                File extension (``.png``, ``.jpg``, ``.jpeg``)
                determines the output format.

        Returns:
            The ``output_path`` the file was saved to.

        Raises:
            ExportError: If validation fails or rendering fails.
        """
        errors: list[str] = ExportValidator.validate(
            self._binding_manager, self._template_ctrl
        )
        if errors:
            raise ExportError("\n".join(errors))

        model = self._binding_manager.model
        template: CardTemplate
        fields: list[TemplateField]
        template, fields = self._load_template_data()

        logger.info("Exporting back card to %s", output_path)
        return self._image_exporter.export_back(
            template=template,
            fields=fields,
            field_data=model.all_values,
            photo_path=model.photo_path or None,
            output_path=output_path,
        )

    def export_combined_pdf(self, output_path: str) -> str:
        """Export both card sides as a single two-page PDF.

        Front side is rendered to a temporary image, back side is
        rendered to a temporary image, then both are assembled
        into the PDF.  Temporary files are cleaned up afterwards.

        Args:
            output_path: Full path where the PDF should be saved.

        Returns:
            The ``output_path`` the PDF was saved to.

        Raises:
            ExportError: If validation fails or rendering fails.
        """
        errors: list[str] = ExportValidator.validate(
            self._binding_manager, self._template_ctrl
        )
        if errors:
            raise ExportError("\n".join(errors))

        model = self._binding_manager.model
        template: CardTemplate
        fields: list[TemplateField]
        template, fields = self._load_template_data()

        # Render both sides to temporary PNG files
        temp_dir = GENERATED_CARDS_DIR
        temp_dir.mkdir(parents=True, exist_ok=True)

        front_png: str = str(
            temp_dir / generate_filename("_export_front_temp", ".png")
        )
        back_png: str = str(
            temp_dir / generate_filename("_export_back_temp", ".png")
        )

        try:
            self._image_exporter.export_front(
                template=template,
                fields=fields,
                field_data=model.all_values,
                photo_path=model.photo_path or None,
                output_path=front_png,
            )
            self._image_exporter.export_back(
                template=template,
                fields=fields,
                field_data=model.all_values,
                photo_path=model.photo_path or None,
                output_path=back_png,
            )

            logger.info("Assembling combined PDF at %s", output_path)
            return self._pdf_exporter.create_combined_pdf(
                front_path=front_png,
                back_path=back_png,
                output_path=output_path,
            )
        finally:
            # Clean up temporary images
            for p in (front_png, back_png):
                try:
                    Path(p).unlink(missing_ok=True)
                except OSError:
                    logger.warning("Could not remove temp file: %s", p)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_template_data(
        self,
    ) -> tuple[CardTemplate, list[TemplateField]]:
        """Load the current template and its fields from the database.

        Returns:
            ``(template, fields)``.

        Raises:
            ExportError: If the template is not found.
        """
        tid: int = self._binding_manager.model.template_id
        template: CardTemplate | None = self._template_ctrl.get_template_by_id(
            tid
        )
        if template is None:
            raise ExportError(
                f"Template id={tid} not found in the database."
            )
        fields: list[TemplateField] = self._template_ctrl.load_all_layout(tid)
        return template, fields
