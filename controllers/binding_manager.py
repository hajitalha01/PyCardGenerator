"""Binding manager — the single point of contact for card form data.

Owns the ``CardDataModel``, coordinates all state mutations,
and emits standardised signals so that the preview engine,
future save engine, and future export engine all react to the
same events without coupling to the UI layer.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal

from controllers.template_controller import TemplateController
from models.card_data_model import CardDataModel
from models.field import TemplateField
from models.template import CardTemplate
from utils.logger import setup_logger

logger = setup_logger(__name__)


class BindingManager(QObject):
    """Central orchestrator for all card form data.

    Owns a ``CardDataModel`` and exposes methods that the
    ``FormBinder`` (or any other input source) calls when
    the user changes a value.  After updating the model the
    manager emits signals to notify downstream consumers.

    Signals
    -------
    field_changed:
        A single field value was updated.
        Carries ``(field_name, new_value)``.
    photo_changed:
        The user's photo selection changed.
        Carries the file path (empty string when cleared).
    template_changed:
        The template selection changed.
        Carries the template id (``0`` when none selected).
    form_reset:
        The entire form was reset or cleared.
    model_updated:
        Fired after **every** state change so that generic
        consumers (e.g. the info-bar) can refresh without
        connecting to every specific signal.
    validation_error:
        A field failed validation.
        Carries ``(field_name, error_message)``.
    """

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    field_changed = Signal(str, str)
    photo_changed = Signal(str)
    template_changed = Signal(int)
    form_reset = Signal()
    model_updated = Signal()
    validation_error = Signal(str, str)

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def __init__(self, parent: QObject | None = None) -> None:
        """Initialise the binding manager with an empty model.

        Args:
            parent: Optional Qt parent.
        """
        super().__init__(parent)
        self._model: CardDataModel = CardDataModel()
        self._template_ctrl: TemplateController = TemplateController()

    # ------------------------------------------------------------------
    # Public API — read
    # ------------------------------------------------------------------

    @property
    def model(self) -> CardDataModel:
        """The underlying ``CardDataModel`` (read / write through methods)."""
        return self._model

    @property
    def is_dirty(self) -> bool:
        """``True`` when any field has been modified since the last clean point."""
        return self._model.is_dirty

    @property
    def dirty_fields(self) -> list[str]:
        """Names of all fields that differ from their clean snapshot."""
        return self._model.get_dirty_fields()

    def validate(self) -> list[tuple[str, str]]:
        """Validate every field and return errors.

        Returns:
            A (possibly empty) list of ``(field_name, error_message)``.
        """
        return self._model.validate()

    def get_field_value(self, field_name: str) -> str:
        """Convenience accessor for a single field value.

        Args:
            field_name: The field to query.

        Returns:
            The current string value.
        """
        return self._model.get_value(field_name)

    # ------------------------------------------------------------------
    # Public API — write
    # ------------------------------------------------------------------

    def set_field(self, field_name: str, value: str) -> None:
        """Update a single field in the model and emit signals.

        Args:
            field_name: The field to update (e.g. ``"name"``).
            value: The new string value.
        """
        self._model.set_value(field_name, value)
        self.field_changed.emit(field_name, value)
        self.model_updated.emit()

        # Run lightweight inline validation for the changed field.
        for name, err in self._model.validate():
            if name == field_name:
                self.validation_error.emit(name, err)

    def set_photo(self, path: str) -> None:
        """Update the photo path and emit signals.

        Args:
            path: Filesystem path to the photo (empty string to clear).
        """
        self._model.photo_path = path
        self.photo_changed.emit(path)
        self.model_updated.emit()

    def set_template(self, template_id: int) -> None:
        """Select a template and load its field definitions.

        Fetches the ``CardTemplate`` and its ``TemplateField`` list
        from the database, populates the model, and emits the
        ``template_changed`` signal.

        Passing ``0`` clears the template selection.

        Args:
            template_id: The template's primary key (``0`` = none).
        """
        if template_id > 0:
            template: CardTemplate | None = (
                self._template_ctrl.get_template_by_id(template_id)
            )
            if template is not None:
                self._model.template_id = template_id
                self._model.template_name = template.template_name

                fields: list[TemplateField] = (
                    self._template_ctrl.load_all_layout(template_id)
                )
                self._model.load_template_fields(fields)

                logger.info(
                    "Template set: id=%d name='%s' with %d fields",
                    template_id, template.template_name, len(fields),
                )
                self.template_changed.emit(template_id)
                self.model_updated.emit()
                return

        # No template or lookup failed.
        self._model.clear()
        self.template_changed.emit(0)
        self.model_updated.emit()

    def reset(self) -> None:
        """Revert every field to its clean snapshot value.

        The dirty flag is cleared.  The ``form_reset`` signal is
        emitted so that consumers (e.g. ``PreviewManager``) can
        re-sync.
        """
        self._model.reset()
        self.form_reset.emit()
        self.model_updated.emit()
        logger.debug("Form reset to snapshot.")

    def clear(self) -> None:
        """Clear all values, photo, and template selection.

        The ``form_reset`` signal is emitted.
        """
        self._model.clear()
        self.form_reset.emit()
        self.model_updated.emit()
        logger.debug("Form cleared.")

    def mark_clean(self) -> None:
        """Accept the current values as the clean baseline.

        Useful after a successful save to reset the dirty flag.
        """
        self._model.mark_clean()
