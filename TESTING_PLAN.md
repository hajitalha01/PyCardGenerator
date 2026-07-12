# Card Generator — Complete Testing Plan

**Author:** Senior QA Engineer  
**Date:** 2026-07-12  
**Version:** 1.0.0  
**Scope:** Full functional, boundary, error-handling, and regression testing

---

## Table of Contents

1. [Scope & Methodology](#1-scope--methodology)
2. [Environment & Prerequisites](#2-environment--prerequisites)
3. [Feature Test Areas](#3-feature-test-areas)
   - 3.1 Dashboard
   - 3.2 Template Manager
   - 3.3 Template Editor
   - 3.4 Card Generator (Form + Preview)
   - 3.5 Export (Image + PDF)
   - 3.6 Card History
   - 3.7 Settings
4. [Cross-Functional Test Areas](#4-cross-functional-test-areas)
   - 4.1 Navigation & Shortcuts
   - 4.2 Window State Persistence
   - 4.3 Database Integrity
   - 4.4 Rendering Pipeline
   - 4.5 File I/O
5. [Test Checklist](#5-test-checklist)
6. [Bug Report Log](#6-bug-report-log)

---

## 1. Scope & Methodology

### In Scope
- All 7 user-facing views (Dashboard, Template Manager, Template Editor, Card Generator, Card History, Settings, Export)
- Form binding & data model pipeline (BindingManager, CardDataModel, FormBinder)
- Rendering pipeline (RenderService, PreviewRenderer, text/photo/image renderers)
- Export pipeline (ExportManager, ImageExporter, PDFExporter)
- Database layer (DatabaseManager, CardRepository, TemplateRepository)
- Validation layer (ExportValidator, CardDataModel.validate, utility validators)
- Preview system (PreviewManager, PreviewCache, PreviewCanvas)
- Navigation, keyboard shortcuts, window state persistence

### Out of Scope
- Performance / load testing
- Security / penetration testing
- Cross-platform testing (Windows-only app)
- Accessibility (screen reader, colour contrast ratios)

### Test Types
| Type | Description |
|------|-------------|
| Normal | Happy-path flow using expected inputs |
| Edge | Boundary values (min, max, empty, null) |
| Invalid | Deliberately wrong data types, formats |
| Robustness | Large files, missing resources, concurrent clicks |
| Regression | Re-test fixed bugs against previous failures |

---

## 2. Environment & Prerequisites

### Hardware
- Windows 10/11 x64
- 1920×1080 or higher display
- 4 GB RAM minimum

### Software
- Python 3.10+
- Dependencies from `requirements.txt` (PySide6, Pillow, ReportLab)
- Write access to `%USERPROFILE%/AppData/Local/CardGenerator/`

### Test Data
- Photo files: `photo_100x100.png`, `photo_1920x1080.jpg`, `photo_10x10.png`, `photo_invalid.txt`
- Template background images: `front_design.png`, `back_design.jpg`
- Large file: `photo_50mb.jpg`
- Unicode name file: `photo_ñño_ü_é.png`
- Clean database (delete `database/card_generator.db` before each full test pass)

---

## 3. Feature Test Areas

### 3.1 Dashboard

| ID | Test Case | Input | Expected Result | Type |
|----|-----------|-------|-----------------|------|
| D-01 | Navigate to Dashboard | Click Dashboard in sidebar | Page displays "Dashboard" title and welcome text | Normal |
| D-02 | Dashboard is default page | Launch application | Dashboard is shown as the first active view | Normal |

### 3.2 Template Manager

| ID | Test Case | Input | Expected Result | Type |
|----|-----------|-------|-----------------|------|
| TM-01 | View template list (empty) | Navigate to Template Manager | Empty table shown, no errors | Normal |
| TM-02 | Create a new template | Click "New Template" | Template created, signal emitted | Normal |
| TM-03 | Select template in list | Click a row | Right panel shows template info, previews | Normal |
| TM-04 | Upload front design image | Click "Upload Front Design", pick PNG | Front preview updates, resolution label changes | Normal |
| TM-05 | Upload back design image | Click "Upload Back Design", pick JPEG | Back preview updates | Normal |
| TM-06 | Upload non-image file | Pick a `.txt` file | File dialog rejects / QPixmap.isNull() — no crash | Invalid |
| TM-07 | Upload corrupt image | Pick a truncated `.png` | Graceful failure, preview unchanged | Invalid |
| TM-08 | Delete template | Click "Delete Template", confirm "Yes" | Template removed from DB and list | Normal |
| TM-09 | Cancel delete | Click "Delete Template", confirm "No" | Template preserved | Normal |
| TM-10 | Delete when no template selected | Click "Delete Template" | Signal emitted with id=0, no crash | Edge |
| TM-11 | Duplicate template | Click "Duplicate Template" | Signal emitted, handled by parent | Normal |
| TM-12 | Refresh template list | Click "Refresh" | Table reloads from database | Normal |
| TM-13 | Template with very long name | Create template with 500 chars | Name truncated or rejected by DB constraint | Edge |
| TM-14 | Template name special characters | Name with `<>:"/\|?*` | Characters sanitised or rejected | Edge |
| TM-15 | Template name Unicode | Name with Chinese/Arabic/Emoji chars | Stored and displayed correctly | Edge |
| TM-16 | Row selection shows dummy data | Select a row | Info labels populated (currently hardcoded dummy data) | Normal |

### 3.3 Template Editor

| ID | Test Case | Input | Expected Result | Type |
|----|-----------|-------|-----------------|------|
| TE-01 | Open editor | Navigate to Template Editor | Canvas, toolbar, properties panel, toolbox display | Normal |
| TE-02 | Add text field | Click "Add Text Field" | Text field item appears on canvas | Normal |
| TE-03 | Add photo field | Click "Add Photo Field" | Photo field placeholder appears | Normal |
| TE-04 | Add rectangle shape | Click "Rectangle" | Rectangle shape appears on canvas | Normal |
| TE-05 | Add QR field | Click "Add QR Field" | Button click handled (no-op currently) | Normal |
| TE-06 | Add Barcode field | Click "Add Barcode Field" | Button click handled (no-op currently) | Normal |
| TE-07 | Select item on canvas | Click a field item | Item highlights, inspector shows item type | Normal |
| TE-08 | Move item | Drag item on canvas | Item moves, position updates | Normal |
| TE-09 | Resize item | Drag resize handle | Item dimensions change | Normal |
| TE-10 | Delete item | Select item, press Delete | Item removed from canvas | Normal |
| TE-11 | Zoom in | Ctrl+Scroll up or click "Zoom In" | Canvas zooms in, zoom % updates | Normal |
| TE-12 | Zoom out | Ctrl+Scroll down or click "Zoom Out" | Canvas zooms out | Normal |
| TE-13 | Reset zoom | Click "Reset Zoom" | Zoom returns to 100% | Normal |
| TE-14 | Fit to screen | Click "Fit to Screen" | Card fits visible area | Normal |
| TE-15 | Toggle grid | Click "Grid" button | Grid visibility / snapping toggles | Normal |
| TE-16 | Change grid size | Set Grid Size to 50 px | Grid spacing updates | Normal |
| TE-17 | Change card width | Set Card Width to 10.0 mm | Canvas updates, label shows new size | Edge |
| TE-18 | Change card width to max | Set Card Width to 200.0 mm | Canvas updates | Edge |
| TE-19 | Change card height to min | Set Card Height to 10.0 mm | Canvas updates | Edge |
| TE-20 | Canvas with many items | Add 100 text fields | Canvas responsive, no crash | Robustness |
| TE-21 | Undo / Redo | Click "Undo" then "Redo" | Currently no-op — no undo stack | Normal |
| TE-22 | Save layout | Click "Save Layout" | Signal emitted | Normal |
| TE-23 | Open template | Click "Open Template" | Signal emitted | Normal |
| TE-24 | Mouse position tracking | Move mouse over canvas | Status bar shows X/Y coordinates | Normal |
| TE-25 | Keyboard nudge | Select item, press arrow keys | Item moves 1px (or 10px with Shift) | Normal |
| TE-26 | Copy / paste | Select item, Ctrl+C, Ctrl+V | Item duplicated | Normal |
| TE-27 | Double-click text field | Double-click text field item | Inline editing enabled | Normal |
| TE-28 | Snap-to-grid | Drag item near grid line | Item snaps to nearest grid | Normal |
| TE-29 | Select multiple items | Ctrl+click two items | Both items selected | Normal |

### 3.4 Card Generator (Form + Preview)

| ID | Test Case | Input | Expected Result | Type |
|----|-----------|-------|-----------------|------|
| CG-01 | Open Card Generator | Navigate to Card Generator | Form with Name, Program, Roll No, CNIC, dates, template selector displayed | Normal |
| CG-02 | Type name field | Enter "John Doe" | Preview updates with name (debounced ~50ms) | Normal |
| CG-03 | Type all text fields | Fill all fields | All values reflected in data model | Normal |
| CG-04 | Select date from picker | Pick issue/expiry date | Date displayed in yyyy-MM-dd format | Normal |
| CG-05 | Select template from combo | Select a template | Template loaded, preview shows fields | Normal |
| CG-06 | Select "– Select Template –" | Reset to placeholder | Preview clears to placeholder | Normal |
| CG-07 | Choose photo | Select a valid PNG/JPG | Photo preview updates | Normal |
| CG-08 | Choose photo and cancel | Open dialog, press Cancel | Photo path unchanged | Normal |
| CG-09 | Choose invalid file type | Pick `.exe` file | File dialog rejects by filter | Invalid |
| CG-10 | Clear form | Click "Clear Form", confirm "Yes" | All fields reset to defaults, preview clears | Normal |
| CG-11 | Cancel clear | Click "Clear Form", confirm "No" | All fields preserved | Normal |
| CG-12 | Very long name | Enter 500 chars | Preview auto-resizes font to fit | Edge |
| CG-13 | Name with special chars | Enter `@#$%^&*()` | Characters displayed or filtered | Edge |
| CG-14 | Name with Unicode | Enter `José Hernández ñoño übel` | Unicode rendered correctly | Edge |
| CG-15 | Empty required fields | Click Download before filling form | Validation errors shown, export blocked | Invalid |
| CG-16 | Photo path with spaces | Select photo from path with spaces | Photo loads correctly | Edge |
| CG-17 | Photo path with Unicode | Select photo from `C:/Usuarios/` path | Photo loads correctly | Edge |
| CG-18 | Rapid typing | Type 20 chars in 200ms | Only one debounced preview update fires | Robustness |
| CG-19 | Template with many fields | Select template with 50 fields | All fields rendered in preview | Robustness |
| CG-20 | No template selected | Try to export | Validation error: "No template selected" | Invalid |
| CG-21 | Clear form resets photo | Clear form | Photo label returns to "No photo selected" | Normal |
| CG-22 | Info bar updates | Change template/values | Template name, image, status shown | Normal |

### 3.5 Export (Image + PDF)

| ID | Test Case | Input | Expected Result | Type |
|----|-----------|-------|-----------------|------|
| EX-01 | Export front as PNG | Click "Download Front", choose path | PNG saved at 300 DPI | Normal |
| EX-02 | Export front as JPEG | Choose `.jpg` extension | JPEG saved at 300 DPI, quality=95 | Normal |
| EX-03 | Export back as PNG | Click "Download Back", choose path | Back image saved | Normal |
| EX-04 | Export combined PDF | Click "Download PDF", choose path | Two-page PDF: front=page1, back=page2 | Normal |
| EX-05 | Cancel save dialog | Press Cancel in file dialog | Export cancelled, no file written | Normal |
| EX-06 | Export without template | Click any Download button | Validation error shown | Invalid |
| EX-07 | Export without photo | Click Download when template has photo field | "A photo is required" error | Invalid |
| EX-08 | Export with missing temp files | Delete temp files during export | Error handled, no crash | Robustness |
| EX-09 | Rapid double-click Download | Click Download twice quickly | Second click blocked by `_export_in_progress` flag | Robustness |
| EX-10 | Export path read-only | Choose read-only directory | ExportError raised with message | Invalid |
| EX-11 | Export to path with special chars | Save to `C:/My Cards/Ñoño's card #1.png` | File saved successfully | Edge |
| EX-12 | Export success dialog | Complete export | "Export Successful" dialog shown | Normal |
| EX-13 | Open folder from success dialog | Click "Open Folder" | Explorer opens with file selected | Normal |
| EX-14 | Export another from success dialog | Click "Export Another" | Returns to save dialog | Normal |
| EX-15 | File exists — overwrite | Save to existing file path | Save dialog lets user overwrite | Normal |
| EX-16 | Generated filename format | Export front with name "John", roll "CS-001" | Suggested: `John_CS-001_Front.png` | Normal |
| EX-17 | Generated filename Unicode | Export with name "José" | Sanitised: `Jos_Front.png` | Edge |
| EX-18 | Export back — no back template fields | Export back with only front fields | Blank or placeholder back image | Edge |
| EX-19 | Combined PDF cleanup | Export combined PDF | Temp PNGs deleted after PDF creation | Normal |
| EX-20 | Combined PDF — temp delete failure | Temp file locked by another process | Warning logged, no crash | Robustness |

### 3.6 Card History

| ID | Test Case | Input | Expected Result | Type |
|----|-----------|-------|-----------------|------|
| CH-01 | View history (empty) | Navigate to Card History | "No cards" empty state shown | Normal |
| CH-02 | Search by name | Enter "John" in search box | Cards with "John" in name shown (250ms debounce) | Normal |
| CH-03 | Search by roll number | Enter "CS-2024-001" | Matching cards shown | Normal |
| CH-04 | Search by card ID | Enter "#5" or "5" | Card with id=5 shown | Normal |
| CH-05 | Search with no results | Enter "zzznotexist" | "No results" empty state shown | Normal |
| CH-06 | Clear search | Click "Clear" | All cards shown again | Normal |
| CH-07 | Filter by date — Today | Click "Today" | Cards created today only | Normal |
| CH-08 | Filter by date — This Week | Click "This Week" | Cards created this week | Normal |
| CH-09 | Filter by date — This Month | Click "This Month" | Cards created this month | Normal |
| CH-10 | Filter by date — All Time | Click "All Time" | All cards shown | Normal |
| CH-11 | Filter by template | Select a template from dropdown | Cards using that template only | Normal |
| CH-12 | Filter by template — All | Select "All Templates" | All cards shown | Normal |
| CH-13 | Sort by column | Click "Name" header | Table sorted by name ascending | Normal |
| CH-14 | Sort by column (toggle) | Click "Name" header again | Table sorted by name descending | Normal |
| CH-15 | Select a single card | Click a row | Preview panel shows card front/back + metadata | Normal |
| CH-16 | Select multiple cards | Ctrl+click rows | Preview panel clears (no single selection) | Normal |
| CH-17 | Checkbox — Select All | Check "Select All" checkbox | All rows checked | Normal |
| CH-18 | Checkbox — Deselect All | Uncheck "Select All" | All rows unchecked | Normal |
| CH-19 | Delete single card | Right-click → "Delete", confirm "Yes" | Card removed from DB and list | Normal |
| CH-20 | Delete single card — cancel | Confirm "No" | Card preserved | Normal |
| CH-21 | Bulk delete | Check 3 cards → "Delete Selected" → confirm | All 3 cards removed | Normal |
| CH-22 | Bulk delete — no selection | Click "Delete Selected" without checks | "No Selection" info shown | Invalid |
| CH-23 | Export selected cards | Check cards → "Export Selected", choose folder | Output files copied to chosen folder | Normal |
| CH-24 | Export selected — no selection | Click "Export Selected" without checks | "No Selection" info shown | Invalid |
| CH-25 | Context menu — Open Preview | Right-click → "Open Preview" | Row selected, preview shown | Normal |
| CH-26 | Context menu — Edit Info | Right-click → "Edit Information" | Dialog opens, changes can be saved | Normal |
| CH-27 | Edit Info — cancel | Edit dialog → Cancel | No changes persisted | Normal |
| CH-28 | Context menu — Regenerate | Right-click → "Regenerate Card" | Card re-rendered, outputs updated | Normal |
| CH-29 | Regenerate — no template | Card has template_id=None | Error message: "no template assigned" | Invalid |
| CH-30 | Regenerate — template deleted | Template no longer in DB | Error message: "template not found" | Invalid |
| CH-31 | Context menu — Download Again | Right-click → "Download Again" | Save dialog, file copied from existing output | Normal |
| CH-32 | Download Again — no output files | Card with no output paths | "No Output" error shown | Invalid |
| CH-33 | Context menu — Duplicate | Right-click → "Duplicate" | New card created with same data, re-rendered | Normal |
| CH-34 | Duplicate — progress dialog | Duplicate a card | Modal progress shown during render | Normal |
| CH-35 | Preview loads existing images | Select card with front_output + back_output | Both previews display images | Normal |
| CH-36 | Preview — missing output file | card.front_output points to deleted file | QPixmap.isNull() — placeholder shown, no crash | Robustness |
| CH-37 | Table with many cards | 10,000 cards in DB | Table scrollable, responsive | Robustness |
| CH-38 | Search with SQL injection | Enter `' OR 1=1 --` | Parameterised query prevents injection | Security |

### 3.7 Settings

| ID | Test Case | Input | Expected Result | Type |
|----|-----------|-------|-----------------|------|
| ST-01 | Navigate to Settings | Click "Settings" in sidebar | Page displays "Settings" title and description | Normal |

---

## 4. Cross-Functional Test Areas

### 4.1 Navigation & Shortcuts

| ID | Test Case | Input | Expected Result | Type |
|----|-----------|-------|-----------------|------|
| NV-01 | Navigate via sidebar | Click each nav button | Correct view displayed, button highlighted | Normal |
| NV-02 | Ctrl+N shortcut | Press Ctrl+N | Navigates to Card Generator | Normal |
| NV-03 | Ctrl+O shortcut | Press Ctrl+O | Navigates to Template Manager | Normal |
| NV-04 | Ctrl+F shortcut | Press Ctrl+F | Navigates to Card History | Normal |
| NV-05 | Ctrl+E shortcut | Press Ctrl+E | Navigates to Card Generator | Normal |
| NV-06 | Ctrl+S shortcut | Press Ctrl+S | Status bar shows "Save" message | Normal |
| NV-07 | Sidebar button stays highlighted | Navigate between views | Active button checked, others unchecked | Normal |

### 4.2 Window State Persistence

| ID | Test Case | Input | Expected Result | Type |
|----|-----------|-------|-----------------|------|
| WS-01 | Window size restored | Resize window, close, reopen | Window opens at same size | Normal |
| WS-02 | Window position restored | Move window, close, reopen | Window opens at same position | Normal |
| WS-03 | First launch | Delete QSettings, launch app | Default window size applied | Normal |

### 4.3 Database Integrity

| ID | Test Case | Input | Expected Result | Type |
|----|-----------|-------|-----------------|------|
| DB-01 | Fresh database creation | Delete .db file, launch app | DB created with schema, no errors | Normal |
| DB-02 | Schema migration | Add column, launch app with old DB | Migration adds column gracefully | Normal |
| DB-03 | Foreign key — cascade delete | Delete template with fields | Fields also deleted | Normal |
| DB-04 | Foreign key — SET NULL | Delete template used by cards | Card template_id set to NULL | Normal |
| DB-05 | Concurrent writes | Rapid create/delete cards | No database locked errors | Robustness |
| DB-06 | WAL mode enabled | Check PRAGMA journal_mode | Returns "wal" | Normal |

### 4.4 Rendering Pipeline

| ID | Test Case | Input | Expected Result | Type |
|----|-----------|-------|-----------------|------|
| RP-01 | Render with background image | Template has front_image path | Background rendered on canvas | Normal |
| RP-02 | Render without background | Template front_image=None | White canvas created | Normal |
| RP-03 | Background image not found | front_image path deleted | Falls back to white canvas, no crash | Robustness |
| RP-04 | Text field with long value | 1000 chars in a 50×20 mm field | Auto-resize reduces font until text fits | Edge |
| RP-05 | Text field — empty value | Field with no default and no user value | Nothing rendered for that field | Normal |
| RP-06 | Text field — background color | Field with `#FF0000` background | Coloured background rectangle drawn | Normal |
| RP-07 | Text field — rotation | Field with 90° rotation | Text rotated 90° around field centre | Normal |
| RP-08 | Text field — opacity 50% | Field with 0.5 opacity | Text semi-transparent | Normal |
| RP-09 | Text field — bold + italic | Bold=True, Italic=True | Bold-italic font variant used | Normal |
| RP-10 | Text field — font not found | Font family "NonExistentFont" | Falls back to Pillow default font | Robustness |
| RP-11 | Photo field — normal | Photo 500×500 px, 100×100 mm field | Photo scaled (fill) to field dimensions | Normal |
| RP-12 | Photo field — small photo | Photo 10×10 px, large field | Photo upscaled (blurry but no crash) | Edge |
| RP-13 | Photo field — no photo | photo_path=None | Field silently skipped | Normal |
| RP-14 | Photo field — file not found | photo_path deleted | Warning logged, field skipped | Robustness |
| RP-15 | Photo field — rounded corners | Default 8mm radius | Corners rendered with rounding | Normal |
| RP-16 | Photo field — border | Default 1mm border | White border drawn | Normal |
| RP-17 | Static image field — valid | Image path provided | Image composited at field position | Normal |
| RP-18 | Static image field — not found | Image path invalid | Warning logged, field skipped | Robustness |
| RP-19 | QR / Barcode fields | Fields with QR or barcode type | Logged as "not yet implemented — skipped" | Normal |
| RP-20 | Field z-order | Two overlapping fields | Higher z_order rendered on top | Normal |
| RP-21 | DPI conversion accuracy | Card 85.6×54.0 mm at 300 DPI | Canvas size: 1011×638 px (85.6*300/25.4) | Normal |
| RP-22 | Preview DPI (150) | Preview at 150 DPI | Canvas size: ~505×319 px | Normal |
| RP-23 | Multiple visible fields | Template with 10 visible fields | All 10 rendered in correct z-order | Normal |

### 4.5 File I/O

| ID | Test Case | Input | Expected Result | Type |
|----|-----------|-------|-----------------|------|
| FI-01 | Image format — PNG | Export as `.png` | RGBA PNG saved | Normal |
| FI-02 | Image format — JPEG | Export as `.jpg` | RGB JPEG saved (alpha removed) | Normal |
| FI-03 | Image format — invalid extension | Force `.bmp` | Saved as PNG (default fallback) | Edge |
| FI-04 | Large image render | 1920×1080 photo | Rendered within reasonable time | Robustness |
| FI-05 | Large image — memory | 50 MB photo file | No MemoryError, graceful handling | Robustness |
| FI-06 | Generated cards directory | Render a card | File created under `generated_cards/` | Normal |
| FI-07 | Uploads directory | Choose photo | Photo displayed from uploads | Normal |
| FI-08 | Log file creation | Launch app | `logs/application.log` created | Normal |
| FI-09 | Log rotation | Generate 10 MB of logs | Rotated to `.1`, `.2` backups | Normal |
| FI-10 | Unicode filename in export | Name="José" | File saved with sanitised name | Edge |

---

## 5. Test Checklist

Use this checklist to track test execution. Mark each item as **PASS** / **FAIL** / **N/A**.

### 5.1 Dashboard
- [ ] D-01 Dashboard displays on navigation
- [ ] D-02 Dashboard is default landing page

### 5.2 Template Manager
- [ ] TM-01 Empty state
- [ ] TM-02 Create template
- [ ] TM-03 Select template row
- [ ] TM-04 Upload front design (valid image)
- [ ] TM-05 Upload back design (valid image)
- [ ] TM-06 Upload non-image file
- [ ] TM-07 Upload corrupt image
- [ ] TM-08 Delete template (confirm)
- [ ] TM-09 Delete template (cancel)
- [ ] TM-10 Delete with no selection
- [ ] TM-11 Duplicate template
- [ ] TM-12 Refresh list
- [ ] TM-13 Very long template name
- [ ] TM-14 Special chars in name
- [ ] TM-15 Unicode in name
- [ ] TM-16 Row selection info

### 5.3 Template Editor
- [ ] TE-01 Editor opens
- [ ] TE-02 Add text field
- [ ] TE-03 Add photo field
- [ ] TE-04 Add rectangle
- [ ] TE-05 Add QR field (no-op)
- [ ] TE-06 Add Barcode field (no-op)
- [ ] TE-07 Select item
- [ ] TE-08 Drag-move item
- [ ] TE-09 Resize item
- [ ] TE-10 Delete item
- [ ] TE-11 Zoom in
- [ ] TE-12 Zoom out
- [ ] TE-13 Reset zoom
- [ ] TE-14 Fit to screen
- [ ] TE-15 Toggle grid
- [ ] TE-16 Change grid size
- [ ] TE-17 Change card width (min)
- [ ] TE-18 Change card width (max)
- [ ] TE-19 Change card height (min)
- [ ] TE-20 Many items (100)
- [ ] TE-21 Undo / Redo (no-op)
- [ ] TE-22 Save layout signal
- [ ] TE-23 Open template signal
- [ ] TE-24 Mouse position tracking
- [ ] TE-25 Arrow key nudge
- [ ] TE-26 Copy / paste
- [ ] TE-27 Double-click text inline edit
- [ ] TE-28 Snap-to-grid
- [ ] TE-29 Multi-select

### 5.4 Card Generator
- [ ] CG-01 Form displays
- [ ] CG-02 Typing updates preview
- [ ] CG-03 All fields store values
- [ ] CG-04 Date picker works
- [ ] CG-05 Template selection loads fields
- [ ] CG-06 Reset template to "-- Select --"
- [ ] CG-07 Choose photo (valid)
- [ ] CG-08 Cancel photo dialog
- [ ] CG-09 Invalid photo file type
- [ ] CG-10 Clear form (confirm)
- [ ] CG-11 Clear form (cancel)
- [ ] CG-12 Very long name (500 chars)
- [ ] CG-13 Special chars in name
- [ ] CG-14 Unicode in name
- [ ] CG-15 Validates required fields on export
- [ ] CG-16 Photo path with spaces
- [ ] CG-17 Photo path with Unicode
- [ ] CG-18 Rapid typing debounce
- [ ] CG-19 Template with many fields
- [ ] CG-20 Export without template
- [ ] CG-21 Clear form resets photo
- [ ] CG-22 Info bar updates

### 5.5 Export
- [ ] EX-01 Front PNG export
- [ ] EX-02 Front JPEG export
- [ ] EX-03 Back PNG export
- [ ] EX-04 Combined PDF export
- [ ] EX-05 Cancel save dialog
- [ ] EX-06 Export without template
- [ ] EX-07 Export without photo (required)
- [ ] EX-08 Missing temp files
- [ ] EX-09 Rapid double-click guard
- [ ] EX-10 Read-only output directory
- [ ] EX-11 Special chars in output path
- [ ] EX-12 Success dialog
- [ ] EX-13 Open folder from dialog
- [ ] EX-14 Export Another
- [ ] EX-15 File overwrite
- [ ] EX-16 Generated filename format
- [ ] EX-17 Unicode filename sanitisation
- [ ] EX-18 No back fields export
- [ ] EX-19 Combined PDF temp cleanup
- [ ] EX-20 Temp delete failure logging

### 5.6 Card History
- [ ] CH-01 Empty state
- [ ] CH-02 Search by name
- [ ] CH-03 Search by roll number
- [ ] CH-04 Search by card ID
- [ ] CH-05 Search with no results
- [ ] CH-06 Clear search
- [ ] CH-07 Today filter
- [ ] CH-08 This Week filter
- [ ] CH-09 This Month filter
- [ ] CH-10 All Time filter
- [ ] CH-11 Template filter
- [ ] CH-12 Template filter — All
- [ ] CH-13 Sort by column
- [ ] CH-14 Sort toggle direction
- [ ] CH-15 Single card selection
- [ ] CH-16 Multi-card selection
- [ ] CH-17 Select All checkbox
- [ ] CH-18 Deselect All checkbox
- [ ] CH-19 Delete single (confirm)
- [ ] CH-20 Delete single (cancel)
- [ ] CH-21 Bulk delete
- [ ] CH-22 Bulk delete — no selection
- [ ] CH-23 Export selected cards
- [ ] CH-24 Export — no selection
- [ ] CH-25 Context menu — Open Preview
- [ ] CH-26 Context menu — Edit Info
- [ ] CH-27 Edit Info — cancel
- [ ] CH-28 Context menu — Regenerate
- [ ] CH-29 Regenerate — no template
- [ ] CH-30 Regenerate — missing template
- [ ] CH-31 Context menu — Download Again
- [ ] CH-32 Download — no output files
- [ ] CH-33 Context menu — Duplicate
- [ ] CH-34 Duplicate — progress dialog
- [ ] CH-35 Preview loads existing images
- [ ] CH-36 Preview — missing output file
- [ ] CH-37 Many cards (10,000)
- [ ] CH-38 SQL injection attempt

### 5.7 Settings
- [ ] ST-01 Settings page displays

### 5.8 Navigation
- [ ] NV-01 Sidebar navigation
- [ ] NV-02 Ctrl+N shortcut
- [ ] NV-03 Ctrl+O shortcut
- [ ] NV-04 Ctrl+F shortcut
- [ ] NV-05 Ctrl+E shortcut
- [ ] NV-06 Ctrl+S shortcut
- [ ] NV-07 Button highlight state

### 5.9 Window State
- [ ] WS-01 Window size restored
- [ ] WS-02 Window position restored
- [ ] WS-03 First launch defaults

### 5.10 Database
- [ ] DB-01 Fresh database creation
- [ ] DB-02 Schema migration
- [ ] DB-03 Cascade delete fields
- [ ] DB-04 SET NULL on cards
- [ ] DB-05 Concurrent writes
- [ ] DB-06 WAL mode

### 5.11 Rendering
- [ ] RP-01 Background image rendered
- [ ] RP-02 White canvas fallback
- [ ] RP-03 Missing background fallback
- [ ] RP-04 Long text auto-resize
- [ ] RP-05 Empty text field
- [ ] RP-06 Background colour
- [ ] RP-07 Text rotation
- [ ] RP-08 Text opacity
- [ ] RP-09 Bold + italic
- [ ] RP-10 Missing font fallback
- [ ] RP-11 Photo fill
- [ ] RP-12 Small photo upscale
- [ ] RP-13 Missing photo skip
- [ ] RP-14 Photo file not found
- [ ] RP-15 Rounded corners
- [ ] RP-16 Photo border
- [ ] RP-17 Static image composite
- [ ] RP-18 Static image not found
- [ ] RP-19 QR/Barcode skip
- [ ] RP-20 Z-order compositing
- [ ] RP-21 DPI conversion accuracy
- [ ] RP-22 Preview DPI (150)
- [ ] RP-23 Multiple visible fields

### 5.12 File I/O
- [ ] FI-01 PNG export
- [ ] FI-02 JPEG export
- [ ] FI-03 Invalid extension
- [ ] FI-04 Large image render
- [ ] FI-05 50 MB photo memory
- [ ] FI-06 Generated cards directory
- [ ] FI-07 Uploads directory
- [ ] FI-08 Log file creation
- [ ] FI-09 Log rotation
- [ ] FI-10 Unicode filename sanitisation

---

## 6. Bug Report Log

| Bug ID | Severity | Module | Description | Status | Fix Date |
|--------|----------|--------|-------------|--------|----------|
| BUG-001 | Critical | `main_window.py:82` | `QStackedWidget` initialised empty — `_build_views()` is defined but never called. All navigation targets receive an empty widget stack, resulting in blank pages for every view. | **FIXED** | 2026-07-12 |
| BUG-002 | Low | `Template Manager` | Template selection uses `row + 1` as template ID (line 457) instead of the actual database ID. Info labels display hardcoded dummy data. | **Open** | — |
| BUG-003 | Low | `Template Editor` | Undo/Redo toolbar buttons connected to `_on_toolbar_action` but no undo stack implemented — clicks do nothing. | **Open** | — |
| BUG-004 | Low | `Template Editor` | "Add QR Field", "Add Barcode Field", "Image", "Logo" toolbox buttons are not wired to canvas methods — clicks produce no visual result. | **Open** | — |
| BUG-005 | Low | `PDFService` | Entire class is a skeleton — `create_front_pdf`, `create_back_pdf`, `create_combined_pdf` all raise `NotImplementedError`. Not currently in use; `PDFExporter` is used instead. | **Open** | — |
| BUG-006 | Info | `Dashboard` | Placeholder only — no real content, statistics, or quick actions. | **Open** | — |
| BUG-007 | Info | `Settings` | Placeholder only — no configurable options. | **Open** | — |
| BUG-008 | Info | `assets/` | All asset directories (fonts, icons, templates) are empty. No default template backgrounds, icons, or bundled fonts. | **Open** | — |

---

*End of Test Plan*
