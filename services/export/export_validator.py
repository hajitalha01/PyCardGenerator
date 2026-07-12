"""Pre-export validation.

Checks that all prerequisites for a successful export are met:
template selected, template exists in the database, required
field values filled, and photo provided when the template
requires one.
"""

from __future__ import annotations

from controllers.binding_manager import BindingManager
from controllers.template_controller import TemplateController
from models.field import TemplateField
from models.template import CardTemplate


class ExportValidator:
    """Validates that the current form state can be exported.

    Usage::

        errors = ExportValidator.validate(binding_manager, template_controller)
        if errors:
            raise ExportError("; ".join(errors))
    """

    @staticmethod
    def validate(
        binding_manager: BindingManager,
        template_controller: TemplateController,
    ) -> list[str]:
        """Check all export prerequisites and return a list of errors.

        Args:
            binding_manager: The active binding manager holding
                the current form state.
            template_controller: Used to load template metadata
                from the database.

        Returns:
            A (possibly empty) list of human-readable error
            messages.  An empty list means the export can proceed.
        """
        errors: list[str] = []
        model = binding_manager.model

        # --- Template must be selected ---
        tid: int = model.template_id
        if tid == 0:
            errors.append("No template selected. Please select a template first.")
            return errors  # no point checking further

        # --- Template must exist in the database ---
        template: CardTemplate | None = template_controller.get_template_by_id(tid)
        if template is None:
            errors.append(
                f"Template id={tid} not found in the database."
            )
            return errors

        # --- Required field values ---
        for field_name, err_msg in model.validate():
            errors.append(err_msg)

        # --- Photo required when template has a PHOTO field ---
        fields: list[TemplateField] = template_controller.load_layout(tid)
        has_photo_field: bool = any(
            f.field_type == "photo" and f.visible
            for f in fields
        )
        if has_photo_field and not model.photo_path:
            errors.append(
                "A photo is required but none has been selected."
            )

        return errors
