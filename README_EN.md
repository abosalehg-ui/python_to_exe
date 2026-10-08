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
| **Project Doctor** *(1.3)* | Pre-build checkup for code that runs under Python but breaks once frozen: uninstalled imports, unbundled data files, relative paths, `multiprocessing` without `freeze_support()`, `input()`/`sys.stdout` in windowed apps, no entry point, fake `.ico` files. Readiness score out of 100, one-click fixes, copyable code snippets |
| **Diagnostics** *(1.3)* | Reads the build log, the user-relevant part of `warn-*.txt`, and the built EXE's own traceback; explains it and offers fixes. **Diagnostic run** builds a console copy of a windowed app to read the error it would otherwise hide. "Apply and rebuild" button |
| **Knowledge base** *(1.3)* | `py2exe_gui/knowledge/packages.json`: what 45 popular packages need to survive PyInstaller (collect flags, hidden imports, data folders, pip names, size notes) |
| **Isolated build env** *(1.4)* | A per-project virtual environment holding only what the project imports (helpers included), created with `uv` when available or `venv` + pip, only after you approve the exact commands. `p2e-build.lock` pins versions for reproducible builds |
| **Size lab** *(1.4)* | What's inside the EXE, library by library, read from PyInstaller's own TOC files; one-click `--exclude-module` suggestions; comparison with the previous build. Real example: a Pillow app went from 30.1 MB to 14.2 MB (−53%) in an isolated environment |
| **Build report** *(1.4)* | Self-contained HTML per build: sizes, breakdown, SHA-256, Python/PyInstaller versions, doctor notes, options |
| **Windows Sandbox** *(1.4)* | Generates a `.wsb` that runs the build on a clean, throw-away Windows (output mapped read-only) |
| **Runtime Kit** *(1.5)* | Optional `p2e_runtime` package embedded in *your* EXE, one checkbox per service: `resource_path()`, a rotating log file for windowed apps, a crash reporter (saved report + native dialog, nothing sent), single instance. Standard library only, Python 3.8+, works with tkinter, Qt and console apps. Nothing on by default, no telemetry |
| **Signed self-updater** *(1.5)* | `update.json` signed with **Ed25519** (pure-Python verifier that passes the RFC 8032 test vectors); HTTPS only, redirects to HTTP refused, size and SHA-256 checked before anything is replaced. One-file EXEs swap in place and restart; folder builds launch a verified installer. Key pair and a *Create signed update.json* helper in the app |
| **Nuitka engine** *(2.0)* | Choose **PyInstaller** or **Nuitka** (`engine` in `p2e.toml`, or `build --engine nuitka`). Nuitka compiles your modules to C: typically fewer antivirus false positives and extraction made **harder, not impossible**; builds are slower because a C compiler runs. What an engine cannot do (Runtime Kit, manifest...) is named before building; fixes are translated to Nuitka's options or marked as having no equivalent — no engine ever gets an option it does not have. The doctor checks the C compiler (MSVC/MinGW on Windows, gcc/clang elsewhere), the Python version and, on Linux, `patchelf`/`readelf`. **No download without your consent**: if Nuitka asks to download a tool, you are asked, for that build only. The size lab reads Nuitka's compilation report |
| **Project file** *(1.6)* | One `p2e.toml` in your repository describes the whole project — build, Version Info, manifest, installer, signing (never the password), Runtime Kit and release settings. Paths are relative to the file, so a fresh checkout builds the same way. The GUI, presets, history and the command line all use this one model |
| **Command line** *(1.6)* | `py2exe-gui init / doctor / build / size / env / release`, headless, no PyQt5 needed — for CI and scripts. Build logs stream with stage markers |
| **One-click release** *(1.6)* | Version bump everywhere at once → notes drafted from `git log` → doctor gate → build → sign → installer → portable ZIP → `SHA256SUMS.txt` → signed `update.json` → git tag → GitHub release → winget manifests. A dry run shows every action first; nothing is tagged or uploaded before you confirm |
| **Icon Studio** *(1.3)* | Real multi-size `.ico` (16–256px) from an image or from letters, drawn with Qt — no Pillow needed |
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
py2exe-gui                 # the window
py2exe-gui --help          # the command line
```

To keep the GitHub token in the operating system's credential store
(Windows Credential Manager, macOS Keychain, Secret Service), install the
optional extra: `pip install -e ".[release]"`. Without it, the release reads
`GITHUB_TOKEN` from the environment.

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
| `Ctrl+S` | Save the project (a settings file when no project is open) |
| `Ctrl+Shift+S` | Save the project as… |
| `Ctrl+N` | New project |
| `Ctrl+Shift+O` | Open a project |
| `Ctrl+T` | Toggle theme (dark/light) |
| `Ctrl+F` | Focus log search |
| `Ctrl+M` | Toggle simple/advanced mode |
| `Ctrl` `+` | Increase font size |
| `Ctrl` `-` | Decrease font size |
| `Ctrl+0` | Reset font size |
| `F5` | Auto-detect imports |

## Simple and Advanced Modes

A first run shows five tabs — Main, Project Doctor, Size & Environment, Templates, About —
because eleven tabs of
PyInstaller options is a lot to meet when all you want is one `.exe`. The mode
button (or `Ctrl+M`) reveals the rest, and the choice is remembered. Hidden
tabs keep their contents: switching modes mid-setup loses nothing.

## Project file (`p2e.toml`)

**Project ▸ Init project from this script** (or `py2exe-gui init app.py`)
writes `p2e.toml` beside the script from the current settings. Commit it:
everyone who clones the repository — and every CI job — builds the same way.

```toml
schema = 2

[project]
name = "Image Tool"
version = "1.4.2"

[build]
source = "app.py"            # relative to this file
engine = "pyinstaller"       # the build engine (new in 2.0)
onefile = true
hidden_imports = ["PIL._tkinter_finder"]
isolated_env = true          # a flag — never an interpreter path

[installer]
enabled = true
app_version = "1.4.2"        # kept in step with [project] by a release

[signing]
enabled = true
cert_path = "certs/me.pfx"   # the password is typed at signing time, never stored

[release]
repository = "me/image-tool"

[release.winget]
enabled = true
identifier = "Me.ImageTool"
```

- **New / Open / Save / Save As** and **Recent projects** are in the
  **Project** menu (`Ctrl+N`, `Ctrl+Shift+O`, `Ctrl+S`, `Ctrl+Shift+S`). The
  title shows the project's name and a `*` while there are unsaved changes.
  Dropping a `p2e.toml` onto the window opens it.
- The file is **versioned** (`schema = 2` since 2.0); a file written by a newer
  app is refused with a clear message instead of being half-read. A 1.6 file
  (`schema = 1`) is migrated on load to `engine = "pyinstaller"`, and a file
  that names an engine this version does not know is refused, never built
  with another engine.
- JSON settings files, presets and history from earlier versions still load.

## Command line

`py2exe-gui` with no arguments opens the window. With a command it runs
headless and never imports PyQt5. Every command takes `--project PATH`
(default `./p2e.toml`) and `--lang ar|en`.

| Command | What it does |
|---|---|
| `py2exe-gui init app.py [--name N] [--set-version X.Y.Z] [--force]` | Create `p2e.toml` for a script |
| `py2exe-gui doctor [--json]` | The project doctor; exit code 1 if it finds errors |
| `py2exe-gui build [--strict] [--yes] [--engine nuitka] [--allow-downloads]` | Run the doctor, then build (in the isolated environment if the project says so). The log streams with `==> [stage] NN%` markers. `--strict` stops on doctor errors. `--engine` picks the engine for this run; `--allow-downloads` lets Nuitka download what it needs (otherwise you are asked) |
| `py2exe-gui size [--json]` | The size lab on the last build |
| `py2exe-gui env create\|lock\|delete [--yes]` | The isolated build environment |
| `py2exe-gui release (--set-version X.Y.Z \| --bump major\|minor\|patch) [--notes FILE] [--dry-run] [--push-tag] [--no-tag] [--no-publish] [--allow-doctor-errors] [--yes]` | The release pipeline (below) |

**Consent works as in the window.** A step that reaches the network, installs
or deletes — and a project file whose settings would run its own code
(`--runtime-hook`, `--upx-dir`, an update key that is not yours) — asks at the
prompt, or needs `--yes` given up front. In a non-interactive session without
`--yes` it is refused with exit code 4; it never happens silently.

| Exit code | Meaning |
|---|---|
| 0 | Success |
| 1 | The doctor found errors, or the build or release failed |
| 2 | Invalid arguments |
| 3 | Project file missing, invalid or refused |
| 4 | A step needed consent that was not given |
| 5 | A required tool or environment is missing |
| 130 | Interrupted |

A CI job is three lines (on a Windows runner for a `.exe`; Linux and macOS
runners build native binaries):

```bash
pip install git+https://github.com/abosalehg-ui/python_to_exe
py2exe-gui doctor
py2exe-gui build --strict --yes
```

## Release

The **🚀 Release** tab and `py2exe-gui release` run the same pipeline:

1. **Version** — semantic version, written to the project, Version Info
   (`1.4.2.0`), the installer and the Runtime Kit together.
2. **Notes** — drafted from `git log <last tag>..HEAD`, grouped by
   Conventional Commit prefix (`feat:`, `fix:`…); edit them in the tab or pass
   `--notes FILE`.
3. **Doctor gate** — errors block the release unless you explicitly override.
4. **Build** in the configured environment.
5. **Sign** with signtool (Windows), password never logged.
6. **Installer** with Inno Setup (Windows).
7. **Portable ZIP** of the one-file EXE or the folder (reproducible bytes).
8. **`SHA256SUMS.txt`** for every artifact.
9. **Signed `update.json`** for the Runtime Kit's updater, pointing at the
   release asset.
10. **git tag** `vX.Y.Z` (the version bump is committed first); pushing it is
    a separate opt-in.
11. **GitHub release** via the REST API — created or completed, assets
    uploaded, draft/pre-release as configured.
12. **winget** — the three manifest files (schema 1.28.0) with the real URL and
    SHA-256, checked against the schema's required fields. Generated only; you
    submit them.

Every release is first planned as a **dry run** that changes nothing; the
final confirmation lists exactly what will be written, run, committed,
tagged, pushed and uploaded. Each step can be repeated: running the same
release again reuses the tag, the GitHub release and the assets already
uploaded.

## Tabs Overview

### ⚙️ Main Settings
File pickers for source, output directory, icon (with a live preview at
16/32/48/64px — the sizes Windows requests, where a PNG renamed to `.ico`
gives itself away). Core PyInstaller flags (`--onefile`, `--windowed`,
`--clean`, `--noconfirm`, `--strip`), plus the build log with text search and
a severity filter.

### ⚖️ Size & Environment
Choose between the current Python and an **isolated environment** for the
project (stored under the per-user cache folder, never in your project). The
tab shows what will be installed — from `p2e-build.lock`, `requirements.txt`, or
the imports — and creates it only after showing you the exact commands. Below,
the **size lab** breaks the last build down by library and offers exclusions
for libraries your code never imports; the **build report** option writes
`<name>-build-report.html` beside `dist/` after each successful build.

### 🧰 Runtime Kit
One checkbox per service the built program gets, each with a one-line
explanation, and a preview of exactly what is embedded (the two-line runtime
hook and `p2e_runtime.json`). The updater section holds the update URL, this
build's version, the embedded public key (*Use my key*), installer arguments
for folder builds, and the key actions: **generate**, **back up** (with a
warning, refused inside the project folder) and **import**. *Publish an
update* writes `update.json` and `update.json.sig` next to a new build;
nothing is uploaded. Your app calls `p2e_runtime.updates.check()` and
`apply(info)` from its own UI; an opt-in check at start-up asks with a native
dialog on Windows.

### 🚀 Release
Version field with patch/minor/major buttons and **Apply to every tab** (a
warning lists any tab whose version disagrees), the notes editor (*Draft from
git*, *From file*), GitHub settings (repository, tag prefix, draft,
pre-release, which files to upload), the token (stored in the OS keyring, shown
only as "stored"), winget identifiers, and the step checklist with live status.
*Dry run* is ticked by default.

### 🩺 Project Doctor
Readiness score, every predicted and actual problem in one list, and the fix
for each. Tick the fixes you want, then **Apply** or **Apply and rebuild**.
Problems that need a change in your code come with a snippet to copy (for
example `resource_path()` for bundled data files); missing packages come with
the `pip install` command. **🧪 Diagnostic run** builds a console copy of a
windowed app into `<output>/p2e_diagnostic`, runs it from a neutral folder,
and reads the traceback the windowed build would have hidden.

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

### Runtime Kit and the updater

- The Runtime Kit is stored in settings as **booleans and text only**. The
  runtime hook is written by the app at build time and never stored, so a
  shared settings file cannot point it at code or an executable — while a
  `--runtime-hook` typed into the extra arguments is still flagged.
- A shared settings file that sets an **update key that is not yours** is
  shown before it is applied: whoever holds that key could install programs
  on your users' machines.
- The updater refuses any `update.json` not signed with your key or not
  served over HTTPS (redirects included), checks size and SHA-256 before
  replacing anything, and never accepts an older or equal version.
- The private key lives in `<config folder>/signing/` with owner-only
  permissions, and never in the project, a build, a settings or preset file,
  or the log. **If you lose it, programs you shipped can no longer be
  updated** — back it up.

### Project files and the release

- A `p2e.toml` is shared content. Opening one goes through the same
  confirmation as a JSON settings file (now also for `--upx-dir`).
- A project file **cannot** hold a password, a token or a private key, and
  cannot name an interpreter or a tool to run: such a file is refused, with
  the key named. Tool locations (ISCC, the base Python) are per-user
  settings.
- The **GitHub token** is read from the OS keyring or `GITHUB_TOKEN`. It is
  never written to the project, the settings, a preset, the history or a log,
  is sent only to the API host (redirects are not followed), and is redacted
  from every message. The certificate password is likewise kept out of every
  log — including the `/Sbyparam` argument of a signed installer, where 1.5
  still printed it.
- The release never pushes a tag or uploads anything before the final
  confirmation; `--yes` is that confirmation on the command line.

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
pytest tests/ -m "not slow"                  # 1519 tests
ruff check py2exe_gui/ p2e_runtime/ tests/   # lint
```

### Project Structure

```
p2e_runtime/              # Runtime Kit embedded in EXEs (stdlib only, 3.8+)
├── __init__.py           # install(), resource_path()
├── paths.py, config.py   # bundle/user folders, p2e_runtime.json
├── logs.py               # rotating log for windowed apps
├── crash.py              # crash reporter
├── single_instance.py    # named mutex (Windows) / fcntl lock (POSIX)
├── updates.py            # signed self-updater
└── _ed25519.py           # verify-only Ed25519 (RFC 8032)
py2exe_gui/
├── app.py                # Application bootstrap (GUI, or the CLI with a command)
├── cli.py                # py2exe-gui init/doctor/build/size/env/release (no PyQt5)
├── texts.py              # Qt-free locale text for release steps (CLI + GUI)
├── constants.py
├── strings.py            # All UI strings (Ar/En) + locale proxy
├── styles.py             # Dark + light themes
├── templates.py          # Build templates registry
├── knowledge/packages.json  # what popular packages need to be frozen
├── core/                 # UI-independent, fully tested
│   ├── engines/          # build engines behind one Engine interface (2.0)
│   │   ├── base.py       #   interface, feature matrix, stage tracker
│   │   ├── pyinstaller.py#   command, phases, output, log patterns
│   │   ├── nuitka.py     #   Nuitka, mapped from its own --help (4.2.2)
│   │   ├── nuitka_report.py # size lab from Nuitka's --report XML
│   │   └── prerequisites.py # C compiler, Python version, patchelf checks
│   ├── builder.py        # command-line helpers (+ compatibility shim)
│   ├── config.py
│   ├── dependency_analyzer.py
│   ├── version_info.py
│   ├── manifest_generator.py
│   ├── code_signer.py
│   ├── smoke_test.py
│   ├── project_doctor.py     # pre-build checks
│   ├── diagnostics.py        # build log, warn file, EXE traceback
│   ├── fixes.py              # shared Finding/Fix model
│   ├── knowledge.py          # package knowledge base loader
│   ├── icon_studio.py        # .ico writer/reader
│   ├── project_scan.py       # imports followed through local modules
│   ├── venv_manager.py       # per-project isolated environments
│   ├── size_analyzer.py      # bundle inventory from PyInstaller's TOC files
│   ├── build_report.py       # self-contained HTML report
│   ├── sandbox.py            # Windows Sandbox .wsb
│   ├── runtime_kit.py        # hook, p2e_runtime.json and options for the build
│   ├── update_signing.py     # signing key, Ed25519 signing, update.json
│   ├── project_file.py       # ProjectConfig + p2e.toml (schema, paths, refusals)
│   ├── toml_writer.py        # the TOML writer (the stdlib only reads TOML)
│   ├── build_runner.py       # headless build: prepare, stream, clean up
│   ├── release/              # versioning, changelog, git, artifacts,
│   │                         # credentials, github, winget, pipeline
│   ├── build_history.py
│   └── log_formatter.py
└── ui/
    ├── main_window.py
    ├── conversion_thread.py
    └── dialogs.py
```

### Running Tests

```bash
pytest tests/ -m "not slow"                # fast suite
pytest tests/ -m slow                      # real PyInstaller builds (minutes)
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
- ✅ **1.3:** Project doctor, build/runtime diagnostics with one-click fixes,
  diagnostic run, package knowledge base, Icon Studio
- ✅ **1.4:** Isolated per-project build environment + lock file, size lab with
  slimming suggestions, HTML build report, Windows Sandbox testing
- ✅ **1.5:** Runtime Kit (`p2e_runtime`): Ed25519-signed self-updater, crash
  reporter, single instance, `resource_path()`, log file for windowed apps
- ✅ **1.6:** `p2e.toml` project file as the single settings model, headless
  command line, one-click release (GitHub Releases, checksums, signed
  update manifest, winget manifests)
- 🚧 **2.0 (in progress):** ✅ engine layer `core/engines/` (milestone 1),
  ✅ Nuitka engine (milestone 2); next compare mode, CI for all platforms, licensing, projects
  workspace, PySide6 — see [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md)
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
