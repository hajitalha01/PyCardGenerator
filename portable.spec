# -*- mode: python ; coding: utf-8 -*-
"""Portable (one-folder) PyInstaller build for Card Generator.

Produces a self-contained dist/portable/CardGenerator/ directory
that can be run without installation on any Windows machine.

Usage:
    python -m PyInstaller portable.spec
"""

from pathlib import Path

# ------------------------------------------------------------------
# Read the Analysis parameters from build.spec by re-execing just
# the parts we need.  The simplest portable approach is to add
# a small wrapper spec that COLLECTs the EXE output.
# ------------------------------------------------------------------

block_cipher = None

# Re-use _PROJECT_ROOT logic
_PROJECT_ROOT = Path(".").resolve()

_DATAS: list[tuple[str, str]] = [
    ("config", "config"),
    ("database/schema.sql", "database"),
    ("assets", "assets"),
]

_HIDDEN_IMPORTS: list[str] = [
    "PySide6.QtCore",
    "PySide6.QtWidgets",
    "PySide6.QtGui",
    "PIL",
    "PIL._tkinter_finder",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    "reportlab",
    "reportlab.lib.units",
    "reportlab.pdfgen",
    "reportlab.pdfgen.canvas",
    "config",
    "config.constants",
    "config.settings",
    "controllers",
    "controllers.binding_manager",
    "controllers.card_controller",
    "controllers.form_binder",
    "controllers.template_controller",
    "database",
    "database.card_repository",
    "database.db_manager",
    "database.template_repository",
    "fields",
    "fields.field_definition",
    "fields.field_type",
    "fields.field_validator",
    "models",
    "models.card",
    "models.card_data_model",
    "models.field",
    "models.template",
    "services",
    "services.export",
    "services.export.export_manager",
    "services.export.export_validator",
    "services.export.exceptions",
    "services.export.file_name_generator",
    "services.export.image_exporter",
    "services.export.pdf_exporter",
    "services.pdf_service",
    "services.preview",
    "services.preview.preview_cache",
    "services.preview.preview_renderer",
    "services.render_service",
    "services.renderers",
    "services.renderers.image_renderer",
    "services.renderers.photo_renderer",
    "services.renderers.text_renderer",
    "utils",
    "utils.helpers",
    "utils.logger",
    "utils.validators",
    "views",
    "views.card_generator_view",
    "views.card_history_view",
    "views.dashboard_view",
    "views.main_window",
    "views.preview_manager",
    "views.settings_view",
    "views.template_editor_view",
    "views.template_manager_view",
    "views.widgets",
    "views.widgets.canvas_items",
    "views.widgets.card_preview_panel",
    "views.widgets.card_preview_widget",
    "views.widgets.editor_canvas",
    "views.widgets.preview_canvas",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=_DATAS,
    hiddenimports=_HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CardGenerator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=str(_PROJECT_ROOT / "assets" / "icons" / "app.ico"),
)

# ------------------------------------------------------------------
# COLLECT — one-folder output: dist/portable/CardGenerator/
# ------------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CardGenerator",
)
