"""Preview panel for the Card History view.

Displays front/back card previews along with card metadata
(template name, generation date) when a row is selected.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from models.card import GeneratedCard
from views.widgets.card_preview_widget import CardPreviewWidget


class PreviewPanel(QScrollArea):
    """Right-hand preview panel for the card history view.

    Shows front and back card previews (if available), together
    with selected card metadata.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise the panel with placeholder state."""
        super().__init__(parent)
        self.setObjectName("historyPreviewPanel")
        self.setWidgetResizable(True)
        self.setMinimumWidth(360)

        container: QWidget = QWidget()
        self._layout: QVBoxLayout = QVBoxLayout(container)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(16)

        # --- Preview heading ---
        self._no_selection_label: QLabel = QLabel(
            "Select a card to preview"
        )
        self._no_selection_label.setObjectName("previewPlaceholder")
        self._no_selection_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        self._no_selection_label.setWordWrap(True)
        self._layout.addWidget(self._no_selection_label)

        # --- Front preview ---
        preview_heading: QLabel = QLabel("Card Preview")
        preview_heading.setObjectName("previewTitle")
        preview_heading.setVisible(False)
        self._layout.addWidget(preview_heading)
        self._preview_heading = preview_heading

        self._front_preview: CardPreviewWidget = CardPreviewWidget("Front")
        self._front_preview.set_placeholder("No front image")
        self._front_preview.setMinimumHeight(120)
        self._front_preview.setVisible(False)
        self._layout.addWidget(self._front_preview)

        self._back_preview: CardPreviewWidget = CardPreviewWidget("Back")
        self._back_preview.set_placeholder("No back image")
        self._back_preview.setMinimumHeight(120)
        self._back_preview.setVisible(False)
        self._layout.addWidget(self._back_preview)

        # --- Info section ---
        info_heading: QLabel = QLabel("Card Information")
        info_heading.setObjectName("formSectionTitle")
        info_heading.setVisible(False)
        self._layout.addWidget(info_heading)
        self._info_heading = info_heading

        self._info_template: QLabel = QLabel("--")
        self._info_date: QLabel = QLabel("--")
        self._info_status: QLabel = QLabel("--")

        info_section: QWidget = QWidget()
        info_section.setObjectName("templateInfoSection")
        info_layout: QVBoxLayout = QVBoxLayout(info_section)
        info_layout.setContentsMargins(16, 16, 16, 16)
        info_layout.setSpacing(6)

        info_layout.addWidget(self._build_info_row("Template:", self._info_template))
        info_layout.addWidget(self._build_info_row("Generated:", self._info_date))
        info_layout.addWidget(self._build_info_row("Status:", self._info_status))

        info_section.setVisible(False)
        self._layout.addWidget(info_section)
        self._info_section = info_section

        self._layout.addStretch()
        self.setWidget(container)

        self.clear()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_card(
        self,
        card: GeneratedCard,
        template_name: str,
        status: str,
        front_pixmap: QPixmap | None,
        back_pixmap: QPixmap | None,
    ) -> None:
        """Display previews and metadata for a selected card.

        Args:
            card: The card record to display.
            template_name: Human-readable template name.
            status: Human-readable status string.
            front_pixmap: Front card image or ``None``.
            back_pixmap: Back card image or ``None``.
        """
        self._no_selection_label.setVisible(False)

        self._preview_heading.setVisible(True)
        self._front_preview.setVisible(True)
        self._back_preview.setVisible(True)
        self._info_heading.setVisible(True)
        self._info_section.setVisible(True)

        # Previews
        if front_pixmap is not None and not front_pixmap.isNull():
            self._front_preview.set_pixmap(front_pixmap)
        else:
            self._front_preview.set_pixmap(None)
            self._front_preview.set_placeholder("No front image available")

        if back_pixmap is not None and not back_pixmap.isNull():
            self._back_preview.set_pixmap(back_pixmap)
        else:
            self._back_preview.set_pixmap(None)
            self._back_preview.set_placeholder("No back image available")

        # Metadata
        self._info_template.setText(template_name)
        created: str = card.created_at or "--"
        self._info_date.setText(created)
        self._info_status.setText(status)

    def clear(self) -> None:
        """Reset the panel to its empty (no-selection) state."""
        self._no_selection_label.setVisible(True)
        self._preview_heading.setVisible(False)
        self._front_preview.setVisible(False)
        self._back_preview.setVisible(False)
        self._info_heading.setVisible(False)
        self._info_section.setVisible(False)

        self._front_preview.set_pixmap(None)
        self._back_preview.set_pixmap(None)
        self._info_template.setText("--")
        self._info_date.setText("--")
        self._info_status.setText("--")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _build_info_row(label_text: str, value_label: QLabel) -> QWidget:
        """Build a single labelled information row.

        Args:
            label_text: The field name displayed on the left.
            value_label: The ``QLabel`` that shows the value.

        Returns:
            A horizontally laid-out row widget.
        """
        row: QWidget = QWidget()
        row_layout: QHBoxLayout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        label: QLabel = QLabel(label_text)
        label.setObjectName("templateInfoLabel")
        row_layout.addWidget(label)

        value_label.setObjectName("templateInfoValue")
        row_layout.addWidget(value_label, stretch=1)

        return row
