# Python to EXE Converter

> Convert Python scripts to Windows executables with a professional bilingual GUI.

A PyQt5 wrapper around PyInstaller that turns one-click .py → .exe into a
real workflow: a beginner-friendly simple mode, batch conversion, 4 accessible
themes, 11 built-in templates, full Arabic and English UIs, code signing,
version metadata, build history, and a Windows manifest editor.

> 🇸🇦 العربية: راجع [README.md](README.md)

## Features

| Category | Capabilities |
|----------|-------------|
| **Core** | One-file or onedir builds, custom icon, hidden imports, extra data files, UPX compression, optimization levels |
| **Templates** | 11 pre-configured project types (GUI, Console, Flask, FastAPI, Streamlit, Pandas, Pygame, Kivy, Discord, Click CLI, Custom) |
| **Smart Analysis** | AST-based import detection (incl. `__import__` and `importlib`), `requirements.txt` import, hidden-imports auto-suggest |
| **Deployment** | Splash screen, Windows manifest (DPI, UAC, supported OS), Authenticode code signing, post-build smoke test |
| **Installer** | Full Inno Setup pipeline: generated `.iss`, stable upgrade-safe AppId, 13 languages, shortcuts, file association, signed `Setup.exe` |
| **Metadata** | Embed company name, product/file version, description, copyright, etc. in the EXE properties |
| **UX** | Simple/advanced modes, drag & drop, command preview (dry-run), real-time colored log with search + severity filter + export, icon preview at 4 sizes, 15+ keyboard shortcuts |
| **Themes** | Dark, Light, Nord, High-contrast, plus `auto` following the OS. Every palette clears WCAG AA 4.5:1, enforced by tests. Font zoom to 200% |
| **Batch** | Queue many `.py` files and build them all with one configuration, sequentially, with a per-file report |
| **Presets** | Save the current configuration under a name; export/import to share |
| **Progress** | Progress bar follows the phase PyInstaller announces, and names it; desktop notification when a build finishes |
| **i18n** | Full Arabic (RTL) and English (LTR) translations, switchable live without a restart |
| **History** | Persistent log of last 20 builds with one-click restore |
| **Updates** | Optional, off by default: reports a newer GitHub release. Never downloads or runs anything |

## Requirements

- Python 3.8+
- PyQt5 >= 5.15
- PyInstaller >= 6.0 (offered for install on first build, with consent)

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
| `Ctrl+M` | Toggle simple/advanced mode |
| `Ctrl` `+` | Increase font size |
| `Ctrl` `-` | Decrease font size |
| `Ctrl+0` | Reset font size |
| `F5` | Auto-detect imports |

## Simple and Advanced Modes

A first run shows three tabs — Main, Templates, About — because nine tabs of
PyInstaller options is a lot to meet when all you want is one `.exe`. The mode
button (or `Ctrl+M`) reveals the rest, and the choice is remembered. Hidden
tabs keep their contents: switching modes mid-setup loses nothing.

## Tabs Overview

### ⚙️ Main Settings
File pickers for source, output directory, icon (with a live preview at
16/32/48/64px — the sizes Windows requests, where a PNG renamed to `.ico`
gives itself away). Core PyInstaller flags (`--onefile`, `--windowed`,
`--clean`, `--noconfirm`, `--strip`), plus the build log with text search and
a severity filter.

### 📚 Batch
Queue several `.py` files and build them all with the current settings. Runs
strictly sequentially: PyInstaller shares `build/` and `dist/`, so concurrent
runs sharing an output directory corrupt each other's intermediate files.

### 🔧 Advanced
Extra data files, hidden imports (with auto-detect and requirements.txt
import), optimization level, UPX compression, raw PyInstaller arguments.

### 📝 Version Info
Eight standard Windows metadata fields (CompanyName, FileDescription,
FileVersion, ProductVersion, etc.). When any field is filled, a temp
`version.txt` is generated and passed via `--version-file`.

### 🚀 Deploy
> On Linux and macOS this tab shows a banner naming what will not take effect:
> signing needs `signtool.exe` and a manifest is a Windows PE resource. The
> controls stay visible — the builder itself is cross-platform.

- **Splash:** image path → `--splash`
- **Manifest:** DPI awareness, UAC level, supported Windows versions → XML → `--manifest`
- **Code signing:** post-build `signtool.exe` invocation with timestamp URL
- **Smoke test:** run the built EXE briefly to verify it starts

### 📦 Installer
Completes the chain: `.py` → **PyInstaller** → `.exe` → **Inno Setup** →
`Setup.exe`.

Requires [Inno Setup 6](https://jrsoftware.org/isdl.php). `ISCC.exe` is located
via the `INNO_SETUP_ISCC` environment variable, then `PATH`, then the standard
`C:\Program Files (x86)\Inno Setup 6\` install directories.

| Generated section | Contents |
|---|---|
| `[Setup]` | Stable `AppId`, version, publisher, privileges (admin / current user), architecture, compression, license, setup icon |
| `[Languages]` | 13 bundled Inno Setup languages; Arabic via an external `.isl` |
| `[Tasks]` / `[Icons]` | Desktop shortcut, Start-menu entry, uninstall shortcut |
| `[Files]` | Single EXE (onefile) or the whole output folder (onedir) |
| `[Registry]` | Optional file association with icon and open command |
| `[Run]` | Optional launch-after-install |

Two actions are available: **Generate .iss only** (inspect the script before
running anything) and **Build installer now** (compiles via `ISCC.exe` on a
background thread).

Notes:
- The `AppId` is a UUIDv5 derived from *(publisher, app name)*. Keeping it
  stable is what makes a newer setup **upgrade** the existing install rather
  than installing side by side.
- Inno Setup does **not** ship an Arabic translation. Selecting Arabic without
  supplying an `Arabic.isl` logs a warning and falls back rather than failing
  the compile.
- Enabling installer signing passes the Deploy tab's `signtool` command to ISCC
  as `/Sbyparam=`, so `Setup.exe` itself is Authenticode-signed.

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
`/fd sha256 /td sha256 /tr <url>`. The password is redacted before display.

### Two signing modes

| Mode | How it works | When to use |
|---|---|---|
| `.pfx` file | `signtool /f <cert> /p <password>` | Simplest, personal machine |
| Windows certificate store | `signtool /n "<subject name>"` | **More secure** — no password on the command line |

> ⚠️ In `.pfx` mode the password is passed as a command-line argument, and on
> Windows any process running as the same user can read another process's
> command line. Redaction protects the *log*, not the process table. On a
> shared machine, enable "Use a certificate from the Windows certificate store".

## Security notes

### Shared settings files

When you load a `.json` settings file you did not write yourself, the app
inspects the extra-arguments field for flags that execute code:

`--runtime-hook` · `--additional-hooks-dir` · `--add-binary` · `--upx-dir` · `--runtime-tmpdir`

If any are present you get an explicit warning before it is applied.
`--runtime-hook` injects code into **every** EXE you subsequently produce —
including ones you sign and distribute. Only accept it from a source you trust.

### PyInstaller installation

Never installed silently. If it is missing you are shown the exact command
(`pip install pyinstaller>=6.0,<7`) and decide for yourself.

### Where settings live

| OS | Path |
|---|---|
| Windows | `%APPDATA%\py2exe_gui\` |
| macOS | `~/Library/Application Support/py2exe_gui/` |
| Linux | `$XDG_CONFIG_HOME/py2exe_gui/` or `~/.config/py2exe_gui/` |

Earlier versions wrote these into the current working directory; they are
migrated once on first run.

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
- ✅ **Phase 7:** Full Inno Setup installer pipeline
- ✅ **Phase 8:** Repository-review fixes, tab split, per-user config paths
- ✅ **Phase 9:** Simple mode, 4 themes + auto, font zoom, tray notifications,
  log filtering, real stage-based progress, batch conversion, presets,
  opt-in update check
- ⏳ **Next:** venv management, multi-file projects, Linux/macOS installers,
  `.spec` editor, VirusTotal, PySide6 migration —
  see [UI_IMPROVEMENT_PLAN.md](UI_IMPROVEMENT_PLAN.md)

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
