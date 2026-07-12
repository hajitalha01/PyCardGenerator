"""Preview manager — live preview orchestrator.

Listens to state-change signals from ``BindingManager`` and
re-renders the card images in real time via ``PreviewRenderer``.
Manages the update debounce timer and a ``PreviewCache`` so that
backgrounds are only re-rendered when the template changes.
Field values are no longer stored here — they are read from the
central ``CardDataModel`` on every update.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer

from controllers.template_controller import TemplateController
from models.field import TemplateField
from models.template import CardTemplate
from services.preview import PreviewCache, PreviewRenderer
from utils.logger import setup_logger

logger = setup_logger(__name__)

_DEBOUNCE_MS: int = 50


class PreviewManager(QObject):
    """Orchestrates live preview updates in response to model changes.

    Usage::

        manager = PreviewManager(front_canvas, back_canvas)
        manager.connect_binding_manager(binding_manager)

    The manager automatically debounces rapid input changes,
    caches template backgrounds, and updates both preview canvases.
    All user-supplied values are read from ``BindingManager.model``.
    """

    def __init__(
        self,
        front_canvas,
        back_canvas,
        parent: QObject | None = None,
    ) -> None:
        """Initialise the preview manager.

        Args:
            front_canvas: ``PreviewCanvas`` for the front card side.
            back_canvas:  ``PreviewCanvas`` for the back card side.
            parent: Optional Qt parent.
        """
        super().__init__(parent)

        self._front_canvas = front_canvas
        self._back_canvas = back_canvas
        self._template_ctrl: TemplateController = TemplateController()
        self._renderer: PreviewRenderer = PreviewRenderer(dpi=150)
        self._cache: PreviewCache = PreviewCache()

        # Debounce timer — prevents re-rendering on every keystroke.
        self._debounce: QTimer = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._do_update)

        # Reference to the binding manager (set via connect_binding_manager)
        self._binding_manager = None

        # Current rendering state (template metadata only)
        self._template: CardTemplate | None = None
        self._fields: list[TemplateField] = []

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect_binding_manager(self, manager) -> None:
        """Connect to a ``BindingManager`` for data signals.

        Replaces the old ``connect_view()`` — the manager no
        longer needs to know about the ``CardGeneratorView``.

        Args:
            manager: The ``BindingManager`` whose signals should
                drive preview updates.
        """
        self._binding_manager = manager
        manager.field_changed.connect(self._on_field_changed)
        manager.photo_changed.connect(self._on_photo_changed)
        manager.template_changed.connect(self._on_template_changed)
        manager.form_reset.connect(self._on_form_reset)

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def _on_field_changed(self, name: str, value: str) -> None:
        """Handle a single field value change — schedule a re-render.

        The value is stored in the central ``CardDataModel``;
        we only need to trigger the update.

        Args:
            name: The field name (e.g. ``'name'``, ``'roll_no'``).
            value: The new text value.
        """
        self._schedule_update()

    def _on_photo_changed(self, path: str) -> None:
        """Handle a photo selection change.

        Args:
            path: Path to the newly selected photo file.
        """
        self._schedule_update()

    def _on_template_changed(self, template_id: int) -> None:
        """Handle a template selection change.

        Loads the template and its fields from the database,
        invalidates the background cache, and triggers a full
        re-render.

        Args:
            template_id: The newly selected template's id (0 = none).
        """
        self._cache.invalidate()

        if template_id > 0:
            template: CardTemplate | None = (
                self._template_ctrl.get_template_by_id(template_id)
            )
            if template is not None:
                self._template = template
                self._fields = self._template_ctrl.load_layout(template_id)
                self._schedule_update()
                return

        # No valid template selected — show placeholders.
        self._template = None
        self._fields = []
        self._front_canvas.set_placeholder("No Front Template Selected")
        self._back_canvas.set_placeholder("No Back Template Selected")

    def _on_form_reset(self) -> None:
        """Handle a form reset / clear event."""
        self._template = None
        self._fields = []
        self._cache.invalidate()
        self._debounce.stop()
        self._front_canvas.set_placeholder("No Front Template Selected")
        self._back_canvas.set_placeholder("No Back Template Selected")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _schedule_update(self) -> None:
        """Schedule a preview update after the debounce period.

        If no template is loaded the call is a no-op.
        """
        if self._template is None:
            return
        self._debounce.start(_DEBOUNCE_MS)

    def _do_update(self) -> None:
        """Render both card sides and update the preview canvases.

        Reads the current field values and photo path from the
        ``CardDataModel`` (owned by ``BindingManager``) on every
        invocation, so the preview always reflects the latest
        state.
        """
        if self._template is None or self._binding_manager is None:
            return

        model = self._binding_manager.model
        field_data: dict[str, str] = model.all_values
        photo_path: str | None = model.photo_path or None

        try:
            # --- Front side ---
            front_img = self._renderer.render_front(
                template=self._template,
                fields=self._fields,
                field_data=field_data,
                photo_path=photo_path,
                cache=self._cache,
            )
            self._front_canvas.set_pixmap(
                PreviewRenderer.image_to_qpixmap(front_img)
            )

            # --- Back side ---
            back_img = self._renderer.render_back(
                template=self._template,
                fields=self._fields,
                field_data=field_data,
                photo_path=photo_path,
                cache=self._cache,
            )
            self._back_canvas.set_pixmap(
                PreviewRenderer.image_to_qpixmap(back_img)
            )

        except Exception:  # noqa: BLE001
            logger.exception("Preview update failed")
