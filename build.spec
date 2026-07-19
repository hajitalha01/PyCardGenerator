# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build specification for Card Generator.

Build the release executable:
    python -m PyInstaller build.spec

Build the portable (one-folder) version:
    python -m PyInstaller portable.spec

The resulting executable is placed in dist/ (or dist/portable/).
"""

from pathlib import Path

block_cipher = None

# ------------------------------------------------------------------
# Project paths
# ------------------------------------------------------------------
# Note: __file__ is NOT available in spec files (they are exec'd in
# a custom namespace).  Use a relative path from the working dir.
_PROJECT_ROOT = Path(".").resolve()

_DATAS: list[tuple[str, str]] = [
    # Config (constants, settings)
    ("config", "config"),
    # Database schema (DB file created at runtime)
    ("database/schema.sql", "database"),
    # Static assets (icons, fonts, templates)
    ("assets", "assets"),
]

# Every non-trivial module that PyInstaller's static analysis
# might miss — especially important for --onefile builds.
_HIDDEN_IMPORTS: list[str] = [
    # PySide6
    "PySide6.QtCore",
    "PySide6.QtWidgets",
    "PySide6.QtGui",
    # Pillow
    "PIL",
    "PIL._tkinter_finder",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    # ReportLab
    "reportlab",
    "reportlab.lib.units",
    "reportlab.pdfgen",
    "reportlab.pdfgen.canvas",
    # Application packages (explicit for one-file builds)
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
    "utils.resource_path",
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

# ------------------------------------------------------------------
# Analysis
# ------------------------------------------------------------------
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

# ------------------------------------------------------------------
# Single-file executable (dist/CardGenerator.exe)
# ------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="CardGenerator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(_PROJECT_ROOT / "assets" / "icons" / "app.ico"),
)

# ------------------------------------------------------------------
# COLLECT for the portable (one-folder) build — used by portable.spec
# ------------------------------------------------------------------
# (Defined in portable.spec which imports from here)
