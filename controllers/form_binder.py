"""Form binder — connects Qt input widgets to the ``BindingManager``.

Provides a clean declarative API for wiring common widget types
(QLineEdit, QDateEdit, QComboBox, etc.) to the central data model
without cluttering the view with lambda-based signal connections.
"""

from __future__ import annotations

from PySide6.QtCore import QDate, QObject
from PySide6.QtWidgets import QComboBox, QDateEdit, QLineEdit, QPushButton

from controllers.binding_manager import BindingManager


class FormBinder:
    """Declarative form-to-model binding helper.

    Each ``bind_*`` method connects a widget's change signal to the
    appropriate ``BindingManager`` method.  All connections are
    tracked so they can be disconnected via ``unbind_all()``.

    Usage::

        binder = FormBinder(binding_manager)

        binder.bind_text_field(name_input, "name")
        binder.bind_text_field(program_input, "program")
        binder.bind_date_field(issue_date, "issue_date")
        binder.bind_template_combo(template_combo)
    """

    def __init__(self, manager: BindingManager) -> None:
        """Initialise the binder.

        Args:
            manager: The ``BindingManager`` that owns the data model.
        """
        self._manager: BindingManager = manager
        self._connections: list[QObject] = []

    # ------------------------------------------------------------------
    # Field bindings
    # ------------------------------------------------------------------

    def bind_text_field(
        self, widget: QLineEdit, field_name: str
    ) -> None:
        """Bind a ``QLineEdit.textChanged`` to a model field.

        Args:
            widget: The line-edit to observe.
            field_name: The target field name in the data model.
        """
        widget.textChanged.connect(
            lambda value: self._manager.set_field(field_name, value)
        )

    def bind_date_field(
        self, widget: QDateEdit, field_name: str
    ) -> None:
        """Bind a ``QDateEdit.dateChanged`` to a model field.

        The date is converted to ``"yyyy-MM-dd"`` string format
        before being passed to the model.

        Args:
            widget: The date picker to observe.
            field_name: The target field name in the data model.
        """
        widget.dateChanged.connect(
            lambda date: self._manager.set_field(
                field_name, date.toString("yyyy-MM-dd")
            )
        )

    def bind_boolean_field(
        self, widget, field_name: str
    ) -> None:
        """Bind a checkable widget (QCheckBox / QRadioButton) to a model field.

        The checked state is converted to ``"true"`` / ``"false"``.

        Args:
            widget: A widget with a ``toggled(bool)`` signal.
            field_name: The target field name in the data model.
        """
        widget.toggled.connect(
            lambda checked: self._manager.set_field(
                field_name, "true" if checked else "false"
            )
        )

    def bind_numeric_field(
        self, widget, field_name: str
    ) -> None:
        """Bind a numeric widget (QSpinBox / QDoubleSpinBox) to a model field.

        The numeric value is converted to its string representation.

        Args:
            widget: A widget with a ``valueChanged(str)`` or
                ``valueChanged(int/float)`` signal.
            field_name: The target field name in the data model.
        """
        # QSpinBox/QDoubleSpinBox emit valueChanged(int|float)
        widget.valueChanged.connect(
            lambda value: self._manager.set_field(
                field_name, str(value)
            )
        )

    # ------------------------------------------------------------------
    # Template / photo bindings
    # ------------------------------------------------------------------

    def bind_template_combo(self, combo: QComboBox) -> None:
        """Bind a ``QComboBox.currentIndexChanged`` to template selection.

        The combo's ``currentData()`` value is passed to
        ``BindingManager.set_template()``.  The combo should have
        item data set to the template id (``0`` = none).

        Args:
            combo: The template selector combo-box.
        """
        combo.currentIndexChanged.connect(
            lambda _: self._manager.set_template(combo.currentData())
        )

    def bind_photo_button(
        self, button: QPushButton, on_choose: callable
    ) -> None:
        """Bind a photo ``Choose Photo`` button.

        Because photo selection involves a native file dialog,
        the binder delegates the dialog logic to a callback.
        The callback should call ``manager.set_photo(path)``
        with the chosen path.

        Args:
            button: The ``Choose Photo`` button.
            on_choose: A zero-argument callable that opens the
                file dialog and calls ``manager.set_photo()``.
        """
        button.clicked.connect(on_choose)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def unbind_all(self) -> None:
        """Disconnect every binding created by this binder.

        Call this when the view is destroyed or when the form
        is completely rebuilt.
        """
        for obj in self._connections:
            try:
                obj.disconnect()
            except RuntimeError:
                pass  # already disconnected or destroyed
        self._connections.clear()
