# Python to EXE Converter

> Convert Python scripts to Windows executables with a professional bilingual GUI.

A PyQt5 wrapper around PyInstaller that turns one-click .py → .exe into a
real workflow: 11 built-in templates, full Arabic and English UIs, code
signing, version metadata, build history, and a Windows manifest editor.

> 🇸🇦 العربية: راجع [README.md](README.md)

## Features

| Category | Capabilities |
|----------|-------------|
| **Core** | One-file or onedir builds, custom icon, hidden imports, extra data files, UPX compression, optimization levels |
| **Templates** | 11 pre-configured project types (GUI, Console, Flask, FastAPI, Streamlit, Pandas, Pygame, Kivy, Discord, Click CLI, Custom) |
| **Smart Analysis** | AST-based import detection (incl. `__import__` and `importlib`), `requirements.txt` import, hidden-imports auto-suggest |
| **Deployment** | Splash screen, Windows manifest (DPI, UAC, supported OS), Authenticode code signing, post-build smoke test |
| **Metadata** | Embed company name, product/file version, description, copyright, etc. in the EXE properties |
| **UX** | Drag & drop, command preview (dry-run), real-time colored log with search/export, dark/light theme, 10+ keyboard shortcuts |
| **i18n** | Full Arabic (RTL) and English (LTR) translations with on-the-fly locale switching |
| **History** | Persistent log of last 20 builds with one-click restore |

## Requirements

- Python 3.8+
- PyQt5 >= 5.15
- PyInstaller >= 5.0 (auto-installed on first build)

## Installation

```bash
git clone https://github.com/abosalehg-ui/python_to_exe.git
cd python_to_exe
pip install -r requirements.txt
python python_to_exe.py
```

Or via the package entry point:

```bash
pip install -e .
py2exe-gui
```

## Quick Start

1. Launch the app: `python python_to_exe.py`
2. **Main Settings** tab → choose your `.py` file (or drag and drop it)
3. **Templates** tab → pick a preset matching your project type
4. Click **🚀 Start Build**
5. Output appears in `<output_dir>/dist/`

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open source file |
| `Ctrl+B` | Start build |
| `Ctrl+Shift+B` | Cancel build |
| `Ctrl+P` | Preview PyInstaller command (dry-run) |
| `Ctrl+L` | Clear log |
| `Ctrl+E` | Export log |
| `Ctrl+S` | Save settings |
| `Ctrl+T` | Toggle theme (dark/light) |
| `Ctrl+F` | Focus log search |
| `F5` | Auto-detect imports |

## Tabs Overview

### ⚙️ Main Settings
File pickers for source, output directory, icon. Core PyInstaller flags
(`--onefile`, `--windowed`, `--clean`, `--noconfirm`, `--strip`).

### 🔧 Advanced
Extra data files, hidden imports (with auto-detect and requirements.txt
import), optimization level, UPX compression, raw PyInstaller arguments.

### 📝 Version Info
Eight standard Windows metadata fields (CompanyName, FileDescription,
FileVersion, ProductVersion, etc.). When any field is filled, a temp
`version.txt` is generated and passed via `--version-file`.

### 🚀 Deploy
- **Splash:** image path → `--splash`
- **Manifest:** DPI awareness, UAC level, supported Windows versions → XML → `--manifest`
- **Code signing:** post-build `signtool.exe` invocation with timestamp URL
- **Smoke test:** run the built EXE briefly to verify it starts

### 📋 Templates
11 presets including:

| Template | Type | Hidden Imports |
|----------|------|----------------|
| GUI (PyQt5/Tkinter) | windowed, onefile | PyQt5.QtWidgets, QtCore, QtGui |
| Console | console, onefile | — |
| Web (Flask/Django) | console, onedir | flask, jinja2, werkzeug |
| Data (Pandas/NumPy) | console, onefile | pandas, numpy, openpyxl |
| Game (Pygame) | windowed, onedir | pygame |
| **FastAPI** | console, onefile | fastapi, uvicorn, starlette, pydantic |
| **Streamlit** | console, onedir | streamlit, altair, click, tornado |
| **Kivy** | windowed, onefile | kivy |
| **Discord Bot** | console, onefile | discord, aiohttp |
| **Click CLI** | console, onefile | click |
| Custom | — | — |

### 🕓 History
Last 20 builds with timestamp, duration, success status. One click
restores the exact config.

### ℹ️ About
Developer info and feature summary.

## Code Signing Setup

The Deploy tab signs the resulting EXE via `signtool.exe` (Windows SDK).
Required:

- `.pfx` certificate file
- Certificate password (entered in masked field — **never logged**)
- Timestamp URL (default: `http://timestamp.digicert.com`)

The signing command is built by `core/code_signer.py` and includes
`/fd sha256 /td sha256 /tr <url>`. Password is redacted before display.

## Development

```bash
pip install -r requirements-dev.txt
pytest tests/                   # 160+ unit tests
ruff check py2exe_gui/ tests/   # lint
```

### Project Structure

```
py2exe_gui/
├── app.py                # Application bootstrap
├── constants.py
├── strings.py            # All UI strings (Ar/En) + locale proxy
├── styles.py             # Dark + light themes
├── templates.py          # Build templates registry
├── core/                 # UI-independent, fully tested
│   ├── builder.py
│   ├── config.py
│   ├── dependency_analyzer.py
│   ├── version_info.py
│   ├── manifest_generator.py
│   ├── code_signer.py
│   ├── smoke_test.py
│   ├── build_history.py
│   └── log_formatter.py
└── ui/
    ├── main_window.py
    ├── conversion_thread.py
    └── dialogs.py
```

### Running Tests

```bash
pytest tests/                              # all
pytest tests/test_builder.py -v            # one module
pytest --cov=py2exe_gui.core --cov-report=term
```

CI runs pytest on Python 3.9 – 3.12 plus ruff on every push.

## Roadmap

See [IDEAS.md](IDEAS.md) for the full roadmap. Currently:

- ✅ **Phase 1:** Modular split, tests, CI, packaging
- ✅ **Phase 2:** UX improvements (drag/drop, preview, themes, shortcuts)
- ✅ **Phase 3:** Multi-language (Arabic + English)
- ✅ **Phase 4:** Pro features (AST analyzer, version info, history)
- ✅ **Phase 5:** Deployment (splash, manifest, signing, smoke test)
- ✅ **Phase 6:** Extra templates + English docs
- ⏳ **Phase 7:** Auto-updater, PyQt6 upgrade, dashboard

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines, the development
setup, and the code review process.

## Troubleshooting

**ModuleNotFoundError when running the built EXE**
The Auto-detect button (F5) parses your source with AST and lists likely
imports. For dynamic patterns missed by analysis, add them manually in
the **Advanced** tab.

**Large output size**
Disable `--onefile` (use onedir), enable `--strip`, and consider UPX
compression (requires UPX on PATH).

**Antivirus false positives**
This is a known PyInstaller issue. Code signing the EXE (Deploy tab) and
publishing to a reputable distribution channel both help. Avoid `--upx`
when targeting strict environments.

**Icon error**
Use a multi-resolution `.ico` file (not `.png` renamed). Tools like
ImageMagick can convert: `convert in.png -define icon:auto-resize=256,128,64,48,32,16 out.ico`

## License

© 2025 — All rights reserved.

## Credits

Developed by Abdulkareem Al-Aboud · abo.saleh.g@gmail.com
