# Release Notes — Card Generator v1.0.0

**Release date:** 2026-07-12

---

## Overview

Card Generator is a desktop application for producing professional ID cards. Users fill a clean form with cardholder details, see a live preview, and export high-resolution images or print-ready PDFs. All data is stored locally in an embedded SQLite database — no internet connection required.

This is the **initial production release**.

---

## Features

### Card Generation
- Manual entry of name, program, roll number, CNIC, and dates via an intuitive form
- Photo selection from disk with live preview
- Template-based layout system (create and manage card templates)
- Live preview updates as the user types (debounced, 150 DPI for speed)

### Template System
- **Template Manager** — create, rename, duplicate, and delete templates; upload front/back design images
- **Template Editor** — drag-and-drop canvas with text fields, photo fields, shapes; grid snapping; zoom; multi-select

### Export
- Export front card as PNG or JPEG (300 DPI)
- Export back card as PNG or JPEG
- Export combined front + back PDF (ReportLab, CR-80 / ID-1 size)
- Auto-generated semantic filenames (e.g. `JohnDoe_CS-001_Front.png`)
- Collision-safe file naming with `_1`, `_2` suffixes

### Card History
- Browse, search (250 ms debounce), and filter all generated cards
- Date-range presets (Today, This Week, This Month)
- Template-based filtering
- Column sorting (ascending / descending)
- Per-card preview (front + back images)
- Context menu: Open Preview, Edit Info, Regenerate, Download Again, Duplicate, Delete
- Bulk actions: Select All, Export Selected, Delete Selected
- Edit Information dialog for updating cardholder data post-generation

### Application
- Professional light-themed UI with QSS stylesheet
- Sidebar navigation with keyboard shortcuts (Ctrl+N/O/F/E/S)
- Window geometry persisted via QSettings
- Rotating log files (10 MB, 5 backups)
- SQLite database with WAL mode, foreign keys, and auto-schema migration

---

## Installation

### Option A — Installer (Recommended)
1. Download `CardGenerator_Setup_v1.0.0.exe`
2. Run the installer and follow the prompts
3. Launch from the Start Menu or desktop shortcut

### Option B — Portable
1. Download `CardGenerator_Portable_v1.0.0.zip`
2. Extract to any folder
3. Run `CardGenerator.exe`

### Option C — From Source
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## System Requirements

| Requirement | Minimum |
|-------------|---------|
| OS | Windows 10 (64-bit) |
| Python | 3.10+ (source only) |
| RAM | 4 GB |
| Disk | 200 MB |
| Display | 1280×720 |

---

## Known Issues

| ID | Description |
|----|-------------|
| K001 | **Undo/Redo in Template Editor** — Toolbar buttons are present but no undo stack is implemented |
| K002 | **QR / Barcode fields** — Toolbox buttons exist but rendering is not yet implemented; fields are silently skipped during export |
| K003 | **Dashboard** — Placeholder page with no statistics or quick actions |
| K004 | **Settings** — Placeholder page with no configurable options |
| K005 | **PDFService** — Skeleton class exists alongside the working `PDFExporter`; not currently wired |
| K006 | **Assets** — No bundled fonts, icons, or default template backgrounds are shipped |
| K007 | **Template info data** — Row selection in Template Manager uses placeholder values for info labels |

---

## Build Verification

### SHA-256 Checksums
```
CardGenerator_Setup_v1.0.0.exe   [calculated at build time]
CardGenerator_Portable_v1.0.0.zip [calculated at build time]
```

### Build Commands
```bash
# Install build tools
pip install pyinstaller

# One-file executable
python -m PyInstaller build.spec

# Portable (one-folder) version
python -m PyInstaller portable.spec

# Installer (requires Inno Setup 6)
iscc installer.iss
```

---

## Changelog

### v1.0.0 (2026-07-12)
- Initial production release
- Card generation with template-based layout
- High-resolution export (PNG, JPEG, PDF)
- Template Manager with CRUD operations
- Template Editor with drag-and-drop canvas
- Card History with search, filter, sort, and bulk actions
- Live preview (150 DPI, debounced)
- SQLite persistence with auto-migration
- Professional light-themed UI
- PyInstaller single-file executable
- Inno Setup installer
- Portable (one-folder) distribution

---

## License

MIT
