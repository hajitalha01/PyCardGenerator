"""Theme switching (Light / Dark / System).

Provides a singleton ``ThemeManager`` that holds both a light and
dark QSS stylesheet and applies the active one to the
``QApplication`` instantly.
"""

from __future__ import annotations

import contextlib
import winreg
from typing import ClassVar

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication

from utils.logger import setup_logger

logger = setup_logger(__name__)


class ThemeManager(QObject):
    """Switches the application theme in real time.

    Usage::

        mgr = ThemeManager(app)
        mgr.apply("dark")   # instant switch
        mgr.apply("system") # follows Windows dark/light mode
    """

    _instance: ThemeManager | None = None

    # Shared selectors — light overrides, dark overrides, then shared rules.
    _LIGHT_QSS: ClassVar[str] = ""
    _DARK_QSS: ClassVar[str] = ""

    def __new__(cls, *args, **kwargs) -> ThemeManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, app: QApplication | None = None) -> None:
        if hasattr(self, "_initialised"):
            return
        super().__init__()
        self._initialised = True
        self._app: QApplication | None = app

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply(self, theme: str) -> None:
        """Apply the named theme to the application.

        Args:
            theme: ``'light'``, ``'dark'``, or ``'system'``.
        """
        qss: str = self._resolve_qss(theme)
        if self._app is not None:
            self._app.setStyleSheet(qss)
            logger.info("Applied theme: %s", theme)

    def reload(self) -> None:
        """Re-apply the current theme (useful after stylesheet edits)."""
        if self._app is not None:
            self._app.setStyleSheet(self._app.styleSheet())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_qss(self, theme: str) -> str:
        """Return the full QSS string for the requested theme."""
        if theme == "dark":
            return self._dark_qss()
        if theme == "system":
            return self._dark_qss() if self._is_windows_dark() else self._light_qss()
        return self._light_qss()

    @staticmethod
    def _is_windows_dark() -> bool:
        """Detect Windows dark mode via the registry."""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return value == 0
        except OSError:
            return False

    # ------------------------------------------------------------------
    # Stylesheets
    # ------------------------------------------------------------------

    @staticmethod
    def _light_qss() -> str:
        """Return the full light-theme stylesheet.

        This matches the original ``_apply_stylesheet`` in ``main.py``
        so existing pages are unaffected.
        """
        return LIGHT_QSS

    @staticmethod
    def _dark_qss() -> str:
        """Return the full dark-theme stylesheet."""
        return DARK_QSS


# ======================================================================
# Light stylesheet  (unchanged from original)
# ======================================================================

LIGHT_QSS: str = """
QMainWindow, QWidget {
    background-color: #f5f6fa;
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
    color: #2d3436;
}

#header {
    background-color: #ffffff;
    border-bottom: 1px solid #e0e4e8;
}
#headerTitle {
    font-size: 15px;
    font-weight: 700;
    color: #1a1a2e;
}
#headerVersion {
    font-size: 11px;
    color: #888888;
    margin-left: 6px;
}
#headerDate {
    font-size: 12px;
    color: #636e72;
}

#sidebar {
    background-color: #ffffff;
    border-right: 1px solid #e0e4e8;
}
#navButton {
    background-color: transparent;
    color: #555555;
    border: none;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 13px;
    text-align: left;
    min-width: 36px;
}
#navButton:hover {
    background-color: #eef2ff;
    color: #4a6cf7;
}
#navButton:checked {
    background-color: #eef2ff;
    color: #4a6cf7;
    font-weight: 600;
}

#viewTitle {
    font-size: 22px;
    font-weight: 700;
    color: #1a1a2e;
    padding: 0px;
}
#viewDescription {
    font-size: 13px;
    color: #888888;
    line-height: 1.4;
    padding: 0px;
}
#viewContent {
    background-color: #ffffff;
    border: 1px solid #e9ecef;
    border-radius: 10px;
}

#cardToolbar {
    background-color: #ffffff;
    border-bottom: 1px solid #e9ecef;
}
#cardToolbar #toolbarButton {
    background-color: #f0f2f5;
    color: #2d3436;
    border: 1px solid #d5d9e2;
    border-radius: 8px;
    padding: 7px 18px;
    font-size: 12px;
    font-weight: 500;
    min-height: 28px;
}
#cardToolbar #toolbarButton:hover {
    background-color: #e4e6f0;
    border-color: #4a6cf7;
    color: #4a6cf7;
}
#cardToolbar #toolbarButton:pressed {
    background-color: #d0d4e0;
}
#tbSep {
    background-color: #e0e0e0;
    max-width: 1px;
    min-width: 1px;
    min-height: 24px;
}

#formScroll {
    background-color: transparent;
    border: none;
}
#formContainer {
    background-color: transparent;
}
#formPanel {
    background-color: #ffffff;
}
#formSectionTitle {
    font-size: 12px;
    font-weight: 700;
    color: #2d3436;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 0px;
}
#photoPlaceholder {
    background-color: #f8f9fa;
    border: 2px dashed #d0d0d0;
    border-radius: 10px;
    color: #aaaaaa;
    font-size: 12px;
}
#photoButton {
    background-color: #f0f0f0;
    color: #333333;
    border: 1px solid #d0d0d0;
    border-radius: 8px;
    padding: 7px 18px;
    font-size: 12px;
    font-weight: 500;
}
#photoButton:hover {
    background-color: #e4e6f0;
    border-color: #4a6cf7;
    color: #4a6cf7;
}
#fieldInput {
    background-color: #ffffff;
    border: 1px solid #d5d9e2;
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 13px;
    color: #2d3436;
    min-height: 18px;
}
#fieldInput:focus {
    border-color: #4a6cf7;
    background-color: #fcfcff;
}
#fieldInput:hover {
    border-color: #b0b8c8;
}
#fieldInput[invalid="true"] {
    border: 1px solid #e74c3c;
    background-color: #fef5f5;
}
#fieldInput QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
#actionButton {
    background-color: #f0f2f5;
    color: #2d3436;
    border: 1px solid #d5d9e2;
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 12px;
    font-weight: 500;
}
#actionButton:hover {
    background-color: #e4e6f0;
    border-color: #4a6cf7;
    color: #4a6cf7;
}
#actionButton:disabled {
    background-color: #f8f8f8;
    color: #bbbbbb;
    border-color: #e8e8e8;
}
#actionButton:pressed {
    background-color: #d0d4e0;
}
#sideTabBtn {
    background-color: #f0f2f5;
    color: #636e72;
    border: 1px solid #d5d9e2;
    border-radius: 8px;
    padding: 6px 18px;
    font-size: 12px;
    font-weight: 500;
}
#sideTabBtn:hover {
    background-color: #e4e6f0;
    border-color: #b0b8c8;
}
#sideTabBtn:checked {
    background-color: #4a6cf7;
    color: #ffffff;
    border-color: #4a6cf7;
    font-weight: 600;
}

#previewTitle {
    font-size: 14px;
    font-weight: 700;
    color: #2d3436;
    padding: 0px;
}
#previewPanel {
    background-color: #ffffff;
    border-left: 1px solid #e9ecef;
}
#previewCardTitle {
    font-size: 12px;
    font-weight: 600;
    color: #636e72;
    padding: 0px;
}
#cardFrame {
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 8px;
}
#cardPlaceholder {
    color: #aaaaaa;
    font-size: 13px;
}

#zoomToolbar {
    background-color: transparent;
    padding: 0px;
}
#zoomBtn {
    background-color: #f0f2f5;
    color: #2d3436;
    border: 1px solid #d5d9e2;
    border-radius: 8px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 500;
    min-height: 24px;
}
#zoomBtn:hover {
    background-color: #e4e6f0;
    border-color: #4a6cf7;
    color: #4a6cf7;
}
#previewToolBtn {
    background-color: #f0f2f5;
    color: #2d3436;
    border: 1px solid #d5d9e2;
    border-radius: 8px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 500;
    min-height: 24px;
}
#previewToolBtn:hover {
    background-color: #e4e6f0;
    border-color: #4a6cf7;
    color: #4a6cf7;
}

#infoBar {
    background-color: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 6px 12px;
}
#infoLabel {
    font-size: 11px;
    color: #888888;
}

#dependentsPanel {
    background-color: #ffffff;
    border-top: 1px solid #e9ecef;
    margin: 0px 24px 0px 24px;
}
#dependentsTable {
    background-color: #ffffff;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    alternate-background-color: #f8f9fa;
    selection-background-color: #eef2ff;
    selection-color: #2d3436;
    gridline-color: #eceef2;
}
#dependentsTable QHeaderView::section {
    background-color: #f8f9fa;
    color: #555555;
    font-weight: 600;
    font-size: 12px;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #dee2e6;
}
#dependentsTable::item {
    padding: 6px 12px;
    border: none;
}

#divider {
    background-color: #e0e0e0;
}

#templateToolbar {
    background-color: #f8f9fa;
    border-bottom: 1px solid #e9ecef;
}
#templateToolbar #toolbarButton {
    background-color: #f0f2f5;
    color: #2d3436;
    border: 1px solid #d5d9e2;
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 12px;
    font-weight: 500;
}
#templateToolbar #toolbarButton:hover {
    background-color: #e4e6f0;
    border-color: #4a6cf7;
    color: #4a6cf7;
}
#templateListPanel {
    background-color: #ffffff;
}
#templateTable {
    background-color: #ffffff;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    alternate-background-color: #f8f9fa;
    selection-background-color: #eef2ff;
    selection-color: #2d3436;
}
#templateTable QHeaderView::section {
    background-color: #f8f9fa;
    color: #555555;
    font-weight: 600;
    font-size: 12px;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #dee2e6;
}
#templateTable::item {
    padding: 6px 12px;
    border: none;
}
#detailsContainer {
    background-color: transparent;
}
#templateInfoSection {
    background-color: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 8px;
}
#templateInfoLabel {
    font-size: 12px;
    font-weight: 600;
    color: #636e72;
}
#templateInfoValue {
    font-size: 12px;
    color: #2d3436;
}
#detailButtons {
    background-color: transparent;
}

#editorToolbar {
    background-color: #ffffff;
    border-bottom: 1px solid #e0e4e8;
}
#editorToolbarBtn {
    background-color: transparent;
    color: #555555;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 12px;
}
#editorToolbarBtn:hover {
    background-color: #eef2ff;
    color: #4a6cf7;
    border-color: #d0d8f0;
}
#editorToolbarBtn:checked {
    background-color: #eef2ff;
    color: #4a6cf7;
    font-weight: 600;
}
#editorToolbarSep {
    color: #e0e0e0;
    padding: 0px;
    max-width: 2px;
}
#propertiesPanel {
    background-color: #ffffff;
    border-right: 1px solid #e0e4e8;
}
#propertiesSectionTitle {
    font-size: 11px;
    font-weight: 700;
    color: #888888;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 0px;
}
#fieldLabel {
    font-size: 12px;
    color: #636e72;
    min-width: 70px;
}
#fieldToolbox {
    background-color: #ffffff;
    border-left: 1px solid #e0e4e8;
}
#fieldToolboxBtn {
    background-color: #f8f9fa;
    color: #444444;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 12px;
    text-align: left;
}
#fieldToolboxBtn:hover {
    background-color: #eef2ff;
    color: #4a6cf7;
    border-color: #d0d8f0;
}
#canvasPanel {
    background-color: #f0f0f0;
}
#editorCanvas {
    background-color: transparent;
    border: none;
}
#inspectorPanel {
    background-color: #ffffff;
    border-top: 1px solid #e0e4e8;
}
#inspectorLabel {
    font-size: 13px;
    color: #999999;
    font-style: italic;
}
#editorStatusBar {
    background-color: #f8f9fa;
    border-top: 1px solid #e0e4e8;
}
#editorStatusLabel {
    font-size: 11px;
    color: #888888;
}

#statusBar {
    background-color: #ffffff;
    border-top: 1px solid #e0e4e8;
    font-size: 12px;
    color: #888888;
    padding: 2px 12px;
}
#statusBar QLabel {
    padding: 0px 12px;
}

QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #d0d4e0;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #b0b8c8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #d0d4e0;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #b0b8c8;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QToolTip {
    background-color: #2d3436;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}
"""


# ======================================================================
# Dark stylesheet
# ======================================================================

DARK_QSS: str = """
QMainWindow, QWidget {
    background-color: #16162a;
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
    color: #e4e4f0;
}

#header {
    background-color: #1e1e36;
    border-bottom: 1px solid #3a3a55;
}
#headerTitle {
    font-size: 15px;
    font-weight: 700;
    color: #f0f0fa;
}
#headerVersion {
    font-size: 11px;
    color: #9898b8;
    margin-left: 6px;
}
#headerDate {
    font-size: 12px;
    color: #b8b8d0;
}

#sidebar {
    background-color: #1e1e36;
    border-right: 1px solid #3a3a55;
}
#navButton {
    background-color: transparent;
    color: #b8b8d0;
    border: none;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 13px;
    text-align: left;
    min-width: 36px;
}
#navButton:hover {
    background-color: #2e2e50;
    color: #7b9cff;
}
#navButton:checked {
    background-color: #2e2e50;
    color: #7b9cff;
    font-weight: 600;
}

#viewTitle {
    font-size: 22px;
    font-weight: 700;
    color: #f0f0fa;
    padding: 0px;
}
#viewDescription {
    font-size: 13px;
    color: #9898b8;
    line-height: 1.4;
    padding: 0px;
}
#viewContent {
    background-color: #1e1e36;
    border: 1px solid #3a3a55;
    border-radius: 10px;
}

#cardToolbar {
    background-color: #1e1e36;
    border-bottom: 1px solid #3a3a55;
}
#cardToolbar #toolbarButton {
    background-color: #2a2a48;
    color: #e4e4f0;
    border: 1px solid #4a4a68;
    border-radius: 8px;
    padding: 7px 18px;
    font-size: 12px;
    font-weight: 500;
    min-height: 28px;
}
#cardToolbar #toolbarButton:hover {
    background-color: #3a3a58;
    border-color: #7b9cff;
    color: #7b9cff;
}
#cardToolbar #toolbarButton:pressed {
    background-color: #4a4a68;
}
#tbSep {
    background-color: #4a4a68;
    max-width: 1px;
    min-width: 1px;
    min-height: 24px;
}

#formScroll {
    background-color: transparent;
    border: none;
}
#formContainer {
    background-color: transparent;
}
#formPanel {
    background-color: #1e1e36;
}
#formSectionTitle {
    font-size: 12px;
    font-weight: 700;
    color: #d0d0e8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 0px;
}
#photoPlaceholder {
    background-color: #2a2a48;
    border: 2px dashed #5a5a78;
    border-radius: 10px;
    color: #8888aa;
    font-size: 12px;
}
#photoButton {
    background-color: #2a2a48;
    color: #e4e4f0;
    border: 1px solid #4a4a68;
    border-radius: 8px;
    padding: 7px 18px;
    font-size: 12px;
    font-weight: 500;
}
#photoButton:hover {
    background-color: #3a3a58;
    border-color: #7b9cff;
    color: #7b9cff;
}
#fieldInput {
    background-color: #1e1e36;
    border: 1px solid #4a4a68;
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 13px;
    color: #e4e4f0;
    min-height: 18px;
}
#fieldInput:focus {
    border-color: #7b9cff;
    background-color: #22223c;
}
#fieldInput:hover {
    border-color: #6a6a88;
}
#fieldInput[invalid="true"] {
    border: 1px solid #e74c3c;
    background-color: #2e1e28;
}
#fieldInput QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
#actionButton {
    background-color: #2a2a48;
    color: #e4e4f0;
    border: 1px solid #4a4a68;
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 12px;
    font-weight: 500;
}
#actionButton:hover {
    background-color: #3a3a58;
    border-color: #7b9cff;
    color: #7b9cff;
}
#actionButton:disabled {
    background-color: #22223a;
    color: #6a6a88;
    border-color: #3a3a55;
}
#actionButton:pressed {
    background-color: #4a4a68;
}
#sideTabBtn {
    background-color: #2a2a48;
    color: #b8b8d0;
    border: 1px solid #4a4a68;
    border-radius: 8px;
    padding: 6px 18px;
    font-size: 12px;
    font-weight: 500;
}
#sideTabBtn:hover {
    background-color: #3a3a58;
    border-color: #6a6a88;
}
#sideTabBtn:checked {
    background-color: #7b9cff;
    color: #16162a;
    border-color: #7b9cff;
    font-weight: 600;
}

#previewTitle {
    font-size: 14px;
    font-weight: 700;
    color: #e4e4f0;
    padding: 0px;
}
#previewPanel {
    background-color: #1e1e36;
    border-left: 1px solid #3a3a55;
}
#previewCardTitle {
    font-size: 12px;
    font-weight: 600;
    color: #b8b8d0;
    padding: 0px;
}
#cardFrame {
    background-color: #2a2a48;
    border: 1px solid #4a4a68;
    border-radius: 8px;
}
#cardPlaceholder {
    color: #8888aa;
    font-size: 13px;
}

#zoomToolbar {
    background-color: transparent;
    padding: 0px;
}
#zoomBtn {
    background-color: #2a2a48;
    color: #e4e4f0;
    border: 1px solid #4a4a68;
    border-radius: 8px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 500;
    min-height: 24px;
}
#zoomBtn:hover {
    background-color: #3a3a58;
    border-color: #7b9cff;
    color: #7b9cff;
}
#previewToolBtn {
    background-color: #2a2a48;
    color: #e4e4f0;
    border: 1px solid #4a4a68;
    border-radius: 8px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 500;
    min-height: 24px;
}
#previewToolBtn:hover {
    background-color: #3a3a58;
    border-color: #7b9cff;
    color: #7b9cff;
}

#infoBar {
    background-color: #2a2a48;
    border: 1px solid #4a4a68;
    border-radius: 8px;
    padding: 6px 12px;
}
#infoLabel {
    font-size: 11px;
    color: #9898b8;
}

#dependentsPanel {
    background-color: #1e1e36;
    border-top: 1px solid #3a3a55;
    margin: 0px 24px 0px 24px;
}
#dependentsTable {
    background-color: #1e1e36;
    border: 1px solid #4a4a68;
    border-radius: 8px;
    alternate-background-color: #22223c;
    selection-background-color: #2e2e50;
    selection-color: #e4e4f0;
    gridline-color: #3a3a55;
}
#dependentsTable QHeaderView::section {
    background-color: #2a2a48;
    color: #b8b8d0;
    font-weight: 600;
    font-size: 12px;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #4a4a68;
}
#dependentsTable::item {
    padding: 6px 12px;
    border: none;
}

#divider {
    background-color: #4a4a68;
}

#templateToolbar {
    background-color: #2a2a48;
    border-bottom: 1px solid #4a4a68;
}
#templateToolbar #toolbarButton {
    background-color: #2a2a48;
    color: #e4e4f0;
    border: 1px solid #4a4a68;
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 12px;
    font-weight: 500;
}
#templateToolbar #toolbarButton:hover {
    background-color: #3a3a58;
    border-color: #7b9cff;
    color: #7b9cff;
}
#templateListPanel {
    background-color: #1e1e36;
}
#templateTable {
    background-color: #1e1e36;
    border: 1px solid #4a4a68;
    border-radius: 8px;
    alternate-background-color: #22223c;
    selection-background-color: #2e2e50;
    selection-color: #e4e4f0;
}
#templateTable QHeaderView::section {
    background-color: #2a2a48;
    color: #b8b8d0;
    font-weight: 600;
    font-size: 12px;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #4a4a68;
}
#templateTable::item {
    padding: 6px 12px;
    border: none;
}
#detailsContainer {
    background-color: transparent;
}
#templateInfoSection {
    background-color: #2a2a48;
    border: 1px solid #4a4a68;
    border-radius: 8px;
}
#templateInfoLabel {
    font-size: 12px;
    font-weight: 600;
    color: #b8b8d0;
}
#templateInfoValue {
    font-size: 12px;
    color: #e4e4f0;
}
#detailButtons {
    background-color: transparent;
}

#editorToolbar {
    background-color: #1e1e36;
    border-bottom: 1px solid #3a3a55;
}
#editorToolbarBtn {
    background-color: transparent;
    color: #b8b8d0;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 12px;
}
#editorToolbarBtn:hover {
    background-color: #2e2e50;
    color: #7b9cff;
    border-color: #4a4a68;
}
#editorToolbarBtn:checked {
    background-color: #2e2e50;
    color: #7b9cff;
    font-weight: 600;
}
#editorToolbarSep {
    color: #4a4a68;
    padding: 0px;
    max-width: 2px;
}
#propertiesPanel {
    background-color: #1e1e36;
    border-right: 1px solid #3a3a55;
}
#propertiesSectionTitle {
    font-size: 11px;
    font-weight: 700;
    color: #9898b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 0px;
}
#fieldLabel {
    font-size: 12px;
    color: #b8b8d0;
    min-width: 70px;
}
#fieldToolbox {
    background-color: #1e1e36;
    border-left: 1px solid #3a3a55;
}
#fieldToolboxBtn {
    background-color: #2a2a48;
    color: #d0d0e8;
    border: 1px solid #4a4a68;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 12px;
    text-align: left;
}
#fieldToolboxBtn:hover {
    background-color: #2e2e50;
    color: #7b9cff;
    border-color: #6a6a88;
}
#canvasPanel {
    background-color: #22223a;
}
#editorCanvas {
    background-color: transparent;
    border: none;
}
#inspectorPanel {
    background-color: #1e1e36;
    border-top: 1px solid #3a3a55;
}
#inspectorLabel {
    font-size: 13px;
    color: #8888aa;
    font-style: italic;
}
#editorStatusBar {
    background-color: #2a2a48;
    border-top: 1px solid #3a3a55;
}
#editorStatusLabel {
    font-size: 11px;
    color: #9898b8;
}

#statusBar {
    background-color: #1e1e36;
    border-top: 1px solid #3a3a55;
    font-size: 12px;
    color: #9898b8;
    padding: 2px 12px;
}
#statusBar QLabel {
    padding: 0px 12px;
}

QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #4a4a68;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #6a6a88;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #4a4a68;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #6a6a88;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QToolTip {
    background-color: #e4e4f0;
    color: #16162a;
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}
"""
