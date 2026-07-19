# Card Generator

A desktop application for generating ID cards from user input.

Built with Python 3.12, PySide6, SQLite, Pillow, and ReportLab.

## Features

- Manual entry of cardholder information via a clean form interface
- Live preview of the card while typing
- Download front card, back card, and combined PDF
- Fully offline — no internet connection required

## Project Structure

```
Card Generator/
├── config/                  # Settings and constants
├── controllers/            # Business logic coordination
├── database/               # SQLite connection and schema
├── models/                 # Data models (template, field, card)
├── services/               # Rendering and PDF generation
├── views/                  # UI views and windows
├── views/widgets/          # Custom Qt widgets
├── utils/                  # Helpers, validators, logger
├── assets/                 # Static resources
├── uploads/                # User-uploaded images

├── logs/                   # Application logs
├── tests/                  # Test suite
├── main.py                 # Entry point
├── requirements.txt        # Python dependencies
└── build.spec              # PyInstaller build config
```

## Getting Started

1. Create a virtual environment:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:

   ```bash
   python main.py
   ```

## Building for Release

### Prerequisites
```bash
pip install pyinstaller
# For the installer: install Inno Setup 6 from https://jrsoftware.org/isinfo.php
```

### Build Targets

| Command | Output | Description |
|---------|--------|-------------|
| `python -m PyInstaller build.spec` | `dist/CardGenerator.exe` | Single-file executable (~67 MB) |
| `python -m PyInstaller portable.spec` | `dist/CardGenerator/` | One-folder portable version (~163 MB) |
| `iscc installer.iss` | `dist/CardGenerator_Setup_v1.0.0.exe` | Inno Setup installer |
| `python scripts/build_assets.py` | `assets/icons/app.ico` | Regenerates the application icon |

### Release Artifacts

After a full build, the `dist/release/` folder contains:

- `CardGenerator_v1.0.0.exe` — Standalone executable (double-click to run)
- `CardGenerator_Portable_v1.0.0.zip` — Portable version (extract and run)
- `CardGenerator_Setup_v1.0.0.exe` — Windows installer (requires Inno Setup)

## Architecture

The application follows **Clean Architecture** principles:

- **Views** — PySide6 UI components (presentation layer)
- **Controllers** — Coordinate user actions between views and services
- **Services** — Business logic (rendering, PDF generation)
- **Database** — SQLite persistence via the DatabaseManager
- **Models** — Plain dataclasses for type-safe data transfer

## License

MIT
