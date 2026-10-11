# Changelog

All notable changes to this project are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### 2.0.0 — Every platform, every engine

The 2.0 release of [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md), built as seven
milestones, each merged on its own (`2.0.0-dev` while it was in progress):
the engine layer, Nuitka, compare mode, the CI generator and the Linux/macOS
packagers, offline licensing, the projects workspace, and the move to
PySide6. Newest first.

#### Milestone 7 — PySide6 and the 2.0.0 release

**Added**
- **`py2exe_gui/qt.py`**, the one place that imports a Qt binding. It
  prefers **PySide6** and falls back to **PyQt5**: `QT_API=pyside6|pyqt5`
  forces one, a binding already loaded in the process wins (two are never
  loaded side by side), then PySide6, then PyQt5. It exports `Signal`,
  `Slot`, `Property` (PyQt5's `pyqtSignal`/`pyqtSlot`/`pyqtProperty` under
  PySide6's names), `QAction` and `QShortcut` (`QtGui` in Qt 6, `QtWidgets`
  in Qt 5), and any other Qt class by name (module `__getattr__`, searched
  in `QtWidgets`, `QtGui`, `QtCore`); plus `describe()` ("PySide6 6.11.2
  (Qt 6.11.2)", shown in the About tab), `configure_high_dpi()` and
  `application_font()`. Without a binding it raises a `ModuleNotFoundError`
  naming both.
- **PySide6 6.12.0 is excluded on Python < 3.12** (`PySide6>=6.5,<6.12`
  there, `>=6.5` from 3.12): that release releases `True`/`False` once
  too often on every signal emission and the process aborts with
  `bool_dealloc` after a few thousand emissions, which a build log reaches
  ([PYSIDE-3477](https://bugreports.qt.io/browse/PYSIDE-3477), reported
  2026-10-09, no fix version yet). Measured here: 6.10.3 and 6.11.2 fine on
  3.11, 6.12.0 aborts on 3.10 and 3.11 and is fine on 3.12 (immortal
  bools). A test emits 20,000 signals in a subprocess and documents it.
- **PySide6 is the default dependency**; PyQt5 is the optional extra
  `py2exe-gui[pyqt5]`. CI runs the whole GUI suite twice, once per binding
  (the PyQt5 job removes PySide6 first, as a user of the extra would have
  it), and the Qt-less core job is unchanged.
- **`tests/test_qt_leak.py`** (a real build, marked `slow`, with a CI job
  of its own): from a process that has the converter's binding loaded, a
  standard-library-only program is built through the application's own
  isolated environment (`plan_environment` → `prepare_build` → `run_build`,
  one-folder). The test proves the environment's interpreter cannot import
  PySide6 or PyQt5, that no file under `dist/` and no line of PyInstaller's
  `*.toc` and `warn-*.txt` names PySide6, PyQt5, shiboken or a Qt library,
  and that the program runs. The converter's binding never reaches the
  user's program: PyInstaller runs in the project's own interpreter and
  only bundles what the program imports.
- **`tests/test_qt_isolation.py`** (no Qt needed; runs in the core job):
  static scans that nothing in `core/`, the command line's modules and
  `p2e_runtime/` imports Qt, that only `qt.py` imports a binding directly,
  and a subprocess that blocks both bindings and imports every core module,
  the command line and the Runtime Kit.
- **`tests/test_qt_compat.py`** (both bindings): the binding policy, the
  exported names, scoped enums, a signal across threads, the Arabic
  rendering of the application font (shaped glyphs with ink, not
  missing-glyph boxes, and a wider advance than Latin), the window in
  Arabic (right-to-left, the binding named in About), and a 150 % display
  (`QT_SCALE_FACTOR=1.5` in a subprocess: a widget's device pixel ratio
  follows under Qt 5 and Qt 6, with `PassThrough` rounding on Qt 6).
- About tab: the Qt binding and version (`ABOUT_QT_FMT`, Arabic and
  English, the version wrapped in `ltr()`).

**Changed**
- Every Qt import in `app.py`, `ui/` and the tests goes through
  `py2exe_gui.qt`; `core/` still imports no Qt, whichever binding is used.
- What both bindings accept, everywhere: **fully scoped enums**
  (`Qt.AlignmentFlag.AlignLeft`, `QMessageBox.StandardButton.Yes`,
  `QFrame.Shape.HLine`, ...; PyQt5 ≥ 5.11 and PySide6 both have them),
  **`exec()`** instead of the Qt 5-only `exec_()` (dialogs, menus, the
  application), and `QFont.setBold()` instead of a weight in the `QFont`
  constructor.
- **High DPI**: the Qt 5 attributes (`AA_EnableHighDpiScaling`,
  `AA_UseHighDpiPixmaps`) are set on Qt 5 only — Qt 6 scales by default
  and warns about them — and the `PassThrough` rounding policy on both, so
  a 150 % display scales by 1.5 rather than 2.
- **Fonts**: the application font is still "Segoe UI" 10 pt, now with
  Arabic-capable fallbacks (`Noto Sans Arabic`, `Noto Naskh Arabic`, `Noto
  Sans`, `DejaVu Sans`, `Geeza Pro`, `Arial`) through `QFont.setFamilies`,
  so a Linux or macOS machine without Segoe UI gets a real Arabic face
  before Qt's own fallback.
- `pyproject.toml`: version **2.0.0**, the description no longer says
  PyQt5, the `gui` marker says "a Qt binding".
- The CHANGELOG's six `2.0.0-dev` milestone entries are this one section.

**Decisions**
- A compat module rather than `qtpy`: the application uses a few dozen
  classes and three differences; a dependency to hide them is more than
  it hides, and `qtpy` would also have to be excluded from users' builds.
- PySide6 first because of its licence (LGPL-3.0, see the pull request),
  its wheels for every Python this project supports, and Qt 6; PyQt5 kept
  because 1.x users have it installed and the code costs nothing to keep
  on both. PyQt6 and PySide2 are not supported: `qt.py` names them only to
  block them in the isolation tests.
- The GUI tests patch `exec` (not `exec_`) on the dialogs: under PySide6
  the old patch of `exec_` left the real modal dialog open and the suite
  hung on the first dialog.
- **PySide6 findings, worked around rather than waited out:**
  the session `QApplication` is now torn down in order at the end of the
  suite (windows closed, top-level widgets deleted, posted deletions
  flushed, the application shut down) — a widget destroyed after Qt's
  statics made PySide6 crash the interpreter *after* "N passed"; and the
  Project menu is kept by reference on the window — PySide6 6.10 hands the
  `QMenuBar.addMenu()` result to Python and deletes the menu with its
  wrapper (6.12 and PyQt5 leave it with the bar).

**Verified**
- Linux container, offscreen (`QT_QPA_PLATFORM=offscreen`), Python
  3.11.17: the non-slow suite under **PySide6 6.11.2 (Qt 6.11.2)** and under
  **PyQt5 5.15.11 (Qt 5.15.14)**: 1975 passed, 3 skipped each, exit code 0;
  with both bindings blocked (`sys.modules[...] = None`): 1689 passed,
  14 skipped (the GUI modules); on **Python 3.9.25 with PySide6 6.10.3**:
  1975 passed.
  `ruff check` clean.
- The leak test under PySide6: the isolated environment (uv, PyInstaller
  6.22.3) cannot import either binding; the one-folder build of the sample
  is 19 MB, 10 files under `_internal/` (`libpython3.11`, `libsqlite3`,
  `base_library.zip`, ...), none of them Qt; the program ran and printed
  its JSON.
- `docs/screenshots/2.0/m7_main_{ar,en}.png` and `m7_about_{ar,en}.png`:
  the main window and the About tab under PySide6, Arabic and English,
  1080×1050 offscreen; the same at `QT_SCALE_FACTOR=2` rendered at
  2160×2100 with a device pixel ratio of 2 (not committed).
- **Not executed:** Windows and macOS (Segoe UI and Geeza Pro, the system
  tray, the native high-DPI path, the `.exe` build of the leak test);
  PyQt6 and PySide2 (unsupported by design); a real high-DPI monitor
  (the check uses `QT_SCALE_FACTOR`).

**Not done**
- No `qtpy`-style support for PyQt6 or PySide2.
- The 1.x templates still name `PyQt5` in the GUI template's hidden
  imports: they describe the *user's* program, and PyQt5 is still the
  common case there.

#### Milestone 6 — Projects workspace

**Added**
- **`core/workspace.py`** (no Qt): one `ProjectSummary` per recent
  `p2e.toml` — name and version from the file; the last build (result, time,
  size) and the output sizes of the successful builds from the build history
  (`size_bytes`, kept since 1.4); the last release from the
  `release/<version>/` folders the 1.6 pipeline writes (version, folder
  time, file count, whether `SHA256SUMS.txt` is there); and
  `sparkline_points()`, the size line as plain coordinates, mirrored for a
  right-to-left layout so time runs in the reading direction. A file that is
  gone is `missing`, one that cannot be used (bad TOML, a refused secret, a
  newer schema, an unknown engine) is `unreadable` with the error's code;
  `summarize_project` never raises.
- **Home tab** (`ui/tabs/home_tab.py`, "🏠 Projects"), first in both modes:
  one card per recent project with the name, version, path, last build line,
  a painted sparkline (`SizeSparkline`, sizes also in its tooltip and
  accessible name), the size change since the previous build, the last
  release line, and *Open · Build · Release · Remove from list*. The buttons
  forward to the window's existing `open_project_path`, `start_conversion`
  and `start_release`: a build from a card is the Convert button's build, a
  release still goes through the dry run and the confirmation. A missing or
  unreadable file shows the reason and only *Remove*. The window starts on
  this tab when there are recent projects, on Main otherwise, and the cards
  are rebuilt after a project is opened or saved, a build or a release
  finishes, and on a theme or language switch.
- Strings in Arabic and English (`TAB_HOME`, `HOME_*`, `BTN_HOME_*`,
  `LOG_HOME_*`); a `projectCard` style in every theme.

**Decisions**
- No new persistence: the last release is read from the folders on disk.
  Nothing records what was published on GitHub, so the card says "last
  release" of the local pipeline, never "published".
- *Build* on the project that is already open does not reopen the file, so
  unsaved edits in the form are built as they are and no save question is
  asked first; on another project the usual open (with its untrusted-flags
  check) runs first and a declined open starts nothing.
- The history keeps 20 builds for every project together, so a sparkline
  has at most that many points and usually far fewer; the view says how many
  builds it counts.

**Verified**
- Real PyInstaller 6.22.3 builds on Linux (Python 3.11, PyQt5 5.15.11)
  through the window's own `start_conversion`: three builds of one project
  with growing imports (6.9 MB, 7.7 MB, 8.1 MB; 7.6–8.0 s each), one failing
  build of a project with a syntax error (4.2 s), and a full release of the
  first project with `py2exe-gui release --no-tag --no-publish` (EXE,
  portable ZIP, `SHA256SUMS.txt`, notes). `docs/screenshots/2.0/m6_home_ar.png`
  and `m6_home_en.png` show that workspace, plus a project whose file was
  deleted after it was opened.
- 20 core tests (`tests/test_workspace.py`) and 24 headless GUI tests
  (`tests/test_ui_home.py`). **Not executed:** Windows and macOS.

**Not done**
- No `projects` command on the command line, and no cross-machine list:
  the recent list is the one in the per-user settings file.

#### Milestone 5 — Offline licensing

**Added**
- **`p2e_runtime.license`** (ships inside the user's app; standard library
  plus the kit's existing Ed25519 verifier, no new dependency): a licence is
  a JSON payload `{name, email, product, expiry (optional), features[]}`
  signed with Ed25519 and encoded as grouped base32 (`XXXXX-XXXXX-…`,
  tolerant of case, whitespace, dashes and O/0, I/1, B/8 mix-ups).
  `verify(key, public_key, product)` returns a `LicenseInfo` or `None` for a
  bad signature, the wrong product, an expired key or garbage and never
  raises on user input; `inspect()` also says *why* (`invalid`, `expired`,
  `wrong_product`); `check(key)` uses the public key and product bundled in
  `p2e_runtime.json`. The expiry day itself is still valid.
- **Converter side** (`core/licensing.py`): the licence key pair is created
  and stored with the **1.5 update-key mechanism** (`update_signing`: same
  file format, same `signing/` folder, owner-only permissions) in a file of
  its own, `license_signing_key.json`, so whoever issues licences cannot
  publish updates. Requests are validated (name, product, email shape, ISO
  expiry not in the past, feature names) and every issued key is checked
  with the runtime's verifier before it is returned. A new Runtime Kit
  service **`licensing`** embeds the product name and the **public** key
  only (`p2e.toml` → `[runtime_kit] licensing, license_product,
  license_public_key`). A test walks every file of a written kit and a
  saved `p2e.toml` and proves the private key is in neither.
- **GUI**: a *🔑 Offline licensing* group in the Runtime Kit tab (product,
  public key, *Use my licence key*, create/back up/import for the licence
  key) and a **licence generator dialog** (name, email, product, expiry or
  perpetual, features → key, with *Copy the key*). The 1.5 key export/import
  handlers were generalised over the two key files.
- **Command line**: `py2exe-gui license issue --name N [--email E]
  [--product P] [--expiry YYYY-MM-DD] [--feature F]… [--create-key]`,
  `license key [--create-key]`, `license verify KEY [--product P]`. The key
  pair is created only after a yes or `--create-key`; a broken key file is
  never replaced silently.
- Finding codes `kit_license_key_missing`, `kit_license_key_invalid`
  (errors that stop the build) and `kit_license_client_side` (info, shown
  whenever licensing is on).

**Honesty**
- The UI, the doctor, the command line and the docs (Arabic and English)
  say the same thing: a check inside a distributed program deters casual
  copying and makes keys impossible to forge without the private key, but
  can be patched out by whoever holds the program, and the expiry relies on
  the customer's clock. No server, no stronger promise anywhere.

**Verified**
- Real PyInstaller 6.22.3 build on Linux (Python 3.11) with licensing on
  (`tests/test_runtime_license_e2e.py`, marked `slow`): built in 8.0 s,
  7.3 MB; the program accepted a valid key (also typed in lower case with
  spaces) and refused a key with one letter changed, another product's key,
  an expired key, another developer's key and garbage, all without a
  traceback; a key for a short name, an email and one feature is 311
  characters; verification inside the frozen app took ~10 ms. Every file
  under `dist/` and `build/` was scanned: the private key is in none, the
  public key is. **Not executed:** the build on Windows or macOS.

#### Milestone 4 — CI generator and Linux/macOS packagers

**Added**
- **Packagers** (`core/packagers/`): one `Packager` interface for an
  **AppImage** (`appimagetool`), a **`.deb`** (`dpkg-deb`, with
  `DEBIAN/control`, a `.desktop` entry and a hicolor icon) and a **`.dmg`**
  (`hdiutil`, an `.app` bundle with `Info.plist`, optional `codesign`). The
  package metadata lives in a new `[packaging]` section of `p2e.toml`; the
  formats a host cannot build are named before the build
  (`platform_support`: AppImage and `.deb` are Linux-only, `.dmg` macOS-only).
- **Consent before any download**: `appimagetool` and the AppImage runtime
  file are fetched only after a yes (GUI question, CLI prompt,
  `--allow-downloads`), into the per-user tools folder, and the tool is run
  with `--runtime-file` so it never goes online during a build. The SHA-256
  of each download is logged and compared with the one recorded here.
- **Release step `packages`** between the portable ZIP and the checksums:
  the packages are checksummed and uploaded with the release.
- **CI generator** (`core/ci_generator.py`): writes
  `.github/workflows/p2e-release.yml` into the project's repository — a
  Windows/macOS/Linux matrix that installs the command line (no Qt), runs
  `py2exe-gui release --no-tag --no-publish` against `p2e.toml` with pip
  and build caching, uploads the release folder, and a tag-triggered (`v*`)
  job that merges the checksums and creates the GitHub Release with `gh`.
  Secrets (`WINDOWS_CERT_BASE64`, `WINDOWS_CERT_PASSWORD`, `MACOS_*`) are
  referenced as `${{ secrets.NAME }}` only; a test pushes secret-looking
  values through every input and checks none reaches the output. Options in
  a new `[ci]` section.
- **Nothing is written without a preview**: the GUI shows the whole file
  with its path and the secret names and writes only on *Write the file*;
  `py2exe-gui ci` prints it and asks (or takes `--yes`; `--print` only shows).
- **Platforms tab** (`🌍`): package formats and metadata, *Build packages
  from the last build*, GitHub Actions options and the preview button.
- Command line: `py2exe-gui package [--format appimage|deb|dmg] [--yes]
  [--allow-downloads] [--json]`, `py2exe-gui ci [--yes] [--print] [--python
  X.Y] [--tool REQ] [--branch NAME]`, `release --allow-downloads`, and
  `P2E_MACOS_SIGN_IDENTITY` for the `.dmg`.
- Icons for Linux packages with the standard library only: a `.png` as is,
  a `.ico` holding a PNG or a 32-bit BMP converted, otherwise a plain
  placeholder tile (reported as a warning).

**Verified**
- Real `.deb` and AppImage built in a Linux container from a PyInstaller
  one-file build, inspected (`dpkg-deb -I/-c`, `--appimage-extract`) and run;
  the full CI command `release --yes --no-tag --no-publish --allow-downloads`
  produced the binary, the ZIP, both packages and `SHA256SUMS.txt` in 9 s.
  `actionlint` 1.7.7 accepts the generated workflow. The `.dmg`, Windows
  signing and macOS notarization steps were **not** executed (no such host).

#### Milestone 3 — Compare mode

**Added**
- **Compare mode** (`core/compare.py`): builds the same project with
  PyInstaller and Nuitka into `<output>/p2e_compare/<engine>` and shows size,
  build time, start-up time, smoke result and unsupported features side by
  side, with a recommendation and its reasons. Size tab button, and
  `py2exe-gui compare [--runs N] [--timeout S] [--json]`.
- **Start-up benchmark** (`core/startup_bench.py`): several runs, median of
  one method: process exit, the Runtime Kit probe (`P2E_RUNTIME_PROBE=1`),
  first output, or "still running after N s". The method is always shown.

**Fixed**
- The smoke test and the benchmark now end the whole process group on a
  timeout; PyInstaller onefile children were left running before.
- `kill_tree` only signals a process group the program itself leads. A test
  stand-in with `pid = 1` made it send SIGKILL to process group 1, which
  took down the whole GitHub Actions runner (every CI run since milestone 3
  died after 45 minutes with no logs) and a container's init when the suite
  ran locally.
- Engines create the output folder before building.

#### Milestone 2 — Nuitka

**Added**
- **Nuitka engine** (`core/engines/nuitka.py`), chosen in the main tab, with
  `engine = "nuitka"` in `p2e.toml`, or `py2exe-gui build --engine nuitka`.
  Every option was mapped from the installed Nuitka's own `--help`
  (**verified against Nuitka 4.2.2**, kept as a test fixture; a test checks
  that every option the engine can emit is documented there): `--mode=onefile`/
  `standalone`, output folder and file name, `--windows-console-mode=disable`,
  the icon, Version Info (`--company-name`, `--product-name`, `--file-version`,
  `--product-version`, `--file-description`, `--copyright`), data files and
  folders, included modules, `--python-flag` for the optimization level, UPX
  (the `upx` plugin) and the one-file splash screen on Windows.
- Same output layout as PyInstaller: `dist/<name>` for one file (Nuitka's
  intermediates in `build/nuitka/`), `dist/<name>.dist/` for a folder.
- **Fix model per engine**: fixes keep PyInstaller's vocabulary and are
  translated for the engine that builds (`--collect-data` →
  `--include-package-data`, `--collect-submodules` → `--include-package`,
  `--copy-metadata` → `--include-distribution-metadata`, `--exclude-module` →
  `--nofollow-import-to`...). What has no equivalent (`--collect-binaries`, the
  Runtime Kit) is shown as "no equivalent in this engine" and never applied.
- **Knowledge base**: optional `engines` section per package
  (`{"nuitka": {"plugins": [...], "notes": {...}}}`), validated, backward
  compatible; `PyQt5 → pyqt5` and `tkinter → tk-inter`, both from real builds.
- **Doctor checks for Nuitka**: a C compiler (MSVC or MinGW on Windows, gcc or
  clang elsewhere, `CC` honoured), the Python version Nuitka supports (3.15 is
  only experimental in 4.2.2), `patchelf` and `readelf` on Linux, Nuitka
  itself, plugins a package needs, and every feature the project asks for that
  the engine lacks.
- **Consent for downloads**: Nuitka runs with stdin closed, so its own prompt
  answers "no". If it stopped for a download, the GUI asks (and the CLI asks,
  or takes `--allow-downloads`) and adds `--assume-yes-for-downloads` to that
  one build only. Installing Nuitka is offered with the exact `pip` command.
- Progress stages and diagnostics read from **real** Nuitka output (logs in
  `tests/data/nuitka/`): plugin needed, download declined, missing
  `patchelf`/`readelf`, no working C compiler, syntax errors, experimental
  Python, Nuitka not installed; runtime tracebacks from `<name>.dist/` and the
  one-file extraction folder lead to the same fixes as with PyInstaller.
- **Size lab without TOC files**: Nuitka's compilation report (`--report`)
  plus a walk of the `<name>.dist` folder. The program binary is split only
  into what can be measured: the bytecode blob (stdlib) and "compiled code
  and the Python runtime".
- The build report names the engine and its version.

**Security**
- Nuitka options that run code or tools named by the settings
  (`--user-plugin`, `--user-package-configuration-file`, `--upx-binary`,
  `--force-runtime-environment-variable`, ...) and `--assume-yes-for-downloads`
  in a shared file now need the same confirmation as `--runtime-hook`.
- Nuitka's update check is off (`--update-check=never`,
  `NUITKA_UPDATE_CHECK=never`): its `--version` otherwise goes online.

#### Milestone 1 — Engine abstraction

First milestone of the 2.0 release of [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md)
(pillar 4, architectural requirement 1). A pure refactor: no build changes.
Every test that existed before passes unchanged, and so do the real
PyInstaller builds (`pytest -m slow`).

**Added**
- **`core/engines/`**: the `Engine` interface (`base.py`) — `name`,
  `is_available(python)`/`version(python)`, `build_command(config, python)`,
  a stage tracker for progress, `locate_output(config)`/`locate_executable`,
  engine-specific build-log patterns (`log_findings`), the files a build
  leaves behind (`build_findings`), the size lab (`analyze_size`) and a
  **feature matrix** (onefile, onedir, windowed, icon, Version Info, splash,
  manifest, UPX, strip, optimize, data files, hidden imports, excluded
  modules, Runtime Kit, size report, warn file). `features_used(config)` and
  `Engine.unsupported_features(config)` say what a project asks for that an
  engine cannot do.
- **`core/engines/pyinstaller.py`**: today's PyInstaller logic, moved — the
  command, its phases, where its output lands, and its own log patterns
  (two Qt bindings, a missing `--add-data` source, an icon in the wrong
  format).
- `get_engine(name)` / `engine_for(config)`; nothing else names an engine class.
- **`BuildConfig.engine`** (default `"pyinstaller"`), in settings, presets,
  history and `p2e.toml`.

**Changed**
- `p2e.toml` is now **schema 2**. A 1.6 file (schema 1) is migrated on load
  with `build.engine = "pyinstaller"`; the bump makes 1.6 refuse a 2.0 file
  ("written by a newer version") instead of silently building a project meant
  for another engine with PyInstaller. A project that names an engine this
  version does not know is refused with the name, never replaced.
- `builder.build_pyinstaller_command` and `build_stages.BuildStageTracker`/
  `STAGES`/`stage_keys`/`stage_for` are thin backward-compatible shims over
  the engine; `diagnose_output(..., engine=)` and the headless build runner go
  through the engine the config selects.

### 1.6.0 — From project to product

Fourth release of [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md) (pillars 7 and 6):
a project is one file in your repository, it builds from the command line,
and it releases with one button — from the version bump to a published
GitHub release.

#### Added
- **Project file `p2e.toml`** and **`ProjectConfig`**, the single settings
  model the roadmap's architectural requirement 2 asked for: build settings,
  Version Info, manifest, installer, signing (certificate path or store
  subject and timestamp URL — never the password), `isolated_env`, the Runtime
  Kit and release settings. Versioned (`schema = 1`) with a migration chain;
  paths stored relative to the file with `/` and resolved on load. Read with
  `tomllib` (3.11+) or `tomli` (declared for older Pythons only); written by a
  small, dedicated writer (`core/toml_writer.py`) that round-trips escapes,
  arrays, nested tables and Arabic text.
- **Project menu**: New, Open, Save, Save As, Recent projects (kept in the
  settings), Init project from this script. The window title shows the
  project's name and an unsaved-changes marker; dropping a `p2e.toml` opens it;
  `Ctrl+S` saves the project when one is open.
- **Command line** — `py2exe-gui init | doctor | build | size | env | release`,
  each with `--project` (default `./p2e.toml`). With no arguments the window
  opens as before. Headless, and never imports PyQt5. `doctor --json` and
  `size --json` for machines; `build` runs the doctor first, streams the
  PyInstaller log with `==> [stage] NN%` markers (`BuildStageTracker`) and
  `--strict` stops on doctor errors. Exit codes 0/1/2/3/4/5/130 are documented
  in `--help` and the READMEs.
- **Release pipeline** (`core/release/`, new 🚀 **Release** tab): version bump
  applied to the project, Version Info, the installer and the Runtime Kit
  together → notes drafted from `git log <last-tag>..HEAD`, grouped by
  Conventional Commit prefix, editable (or `--notes FILE`) → doctor gate →
  build → signtool → Inno Setup → reproducible portable ZIP →
  `SHA256SUMS.txt` → the Runtime Kit's signed `update.json` for the new
  version → git tag (the bump is committed first; pushing is a separate
  opt-in) → GitHub release through the REST API (draft/pre-release, assets
  uploaded) → winget manifests (version, installer, defaultLocale; schema
  1.28.0, checked against the official schema files' required fields,
  enums and patterns). Every step is a separate, idempotent unit: running the
  same release again reuses the tag, the release and the uploaded assets.
- **Dry run** for the whole pipeline: it reads the project, git and the
  doctor, predicts every file name and command, and changes nothing. The same
  action list feeds the final confirmation, which lists exactly what will be
  written, run, committed, tagged, pushed and uploaded.
- The Release tab: version with patch/minor/major and **Apply to every tab**
  (a warning names any tab whose version disagrees), notes editor, GitHub and
  winget settings, the token field, and the step checklist with live status.
  Arabic (RTL) and English.

#### Changed
- Each tab now reads and applies its own part of `ProjectConfig`;
  `MainWindow._current_config`/`_apply_config` no longer copy fields one by
  one. Settings files, presets and build history store the project's JSON
  form, which keeps the old build keys at the top level: every existing JSON
  file, preset and history entry still loads, and a pre-1.6 file only touches
  the build settings it holds.
- Switching language no longer resets the deploy and installer tabs (the
  project model carries the whole form across the rebuild).
- The ISCC path is now a per-user setting (it names a program to run).
- New themed styles for the menu bar and menus.

#### Security
- A project file is untrusted shared content: opening one goes through the
  same dangerous-settings confirmation as a JSON file (`builder.find_dangerous_args`),
  which now also covers a `upx_dir` setting (UPX is an executable). A file
  that holds a password, a token or a private key — by key name, or a value
  that looks like a GitHub token or a PEM key — or that names an interpreter
  or a tool to run, is refused with the key named.
- The **GitHub token** comes from the OS keyring (`keyring`, optional:
  `pip install ".[release]"`) or `GITHUB_TOKEN`. It is never stored in the
  project, the settings, a preset, the history or a log; it is sent only to
  the API host (and `uploads.github.com` for the official API), redirects are
  not followed, and every message is redacted. Tests grep logs, outputs,
  settings and release files for it.
- **Fixed a 1.5 leak:** a signed installer passes the whole signtool command,
  `/p <password>` included, as one `/Sbyparam=…` argument to ISCC, and
  `redact_password` only looked at separate `/p` tokens — the certificate
  password was written to the log. It now redacts a password embedded in an
  argument as well.
- The CLI's consent rules match the GUI's: network, install and delete
  steps, and a project file whose settings run code, need a yes at the prompt
  or `--yes`; a non-interactive session without it is refused (exit code 4).
  No password or token is ever a command-line flag (`P2E_SIGN_PASSWORD`,
  `GITHUB_TOKEN`, or a prompt).

#### Measured (Linux, Python 3.12, PyInstaller 6.22, a one-line app)
- `init` 0.02 s · `doctor` 0.01 s · `build` 9.9 s · `release --dry-run` 0.09 s ·
  full release 10.0 s (the build is almost all of it) with 6 API requests
  (two lookups, one create, three uploads).
- Release folder: the 7.1 MiB executable, the 7.0 MiB portable ZIP,
  `SHA256SUMS.txt`, `RELEASE_NOTES.md` and the three winget files.
- 1519 fast tests (up from 1217), plus the new slow end-to-end test
  (`init → build → release --dry-run → release` against a local fake GitHub
  API, real PyInstaller). Core coverage without PyQt5: 96.7 %.

#### Not verified here (Linux)
- signtool and Inno Setup run only on Windows: those steps are tested with a
  recording runner, not the real tools.
- The winget files are checked against the official 1.28.0 JSON schemas, but
  not with `winget validate`.
- Uploads are tested against a local fake of the GitHub API, not GitHub.

### 1.5.0 — Runtime Kit

Third release of [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md) (pillar 5): every
other packaging tool stops once the EXE exists; this one now makes the
*produced program* better after it ships.

#### Added
- **Runtime Kit** (new 🧰 tab, shown in simple mode). `p2e_runtime`, a separate
  package — standard library only, Python 3.8+, no GUI toolkit, so it works in
  tkinter, Qt, wx and console apps — that the converter embeds in the EXE,
  **one checkbox per service, all off by default**:
  - **`resource_path()`** — bundled files found the same way in development,
    one-file and folder builds (`from p2e_runtime import resource_path`).
  - **Log file for windowed apps** — when `sys.stdout`/`sys.stderr` are `None`
    they go to a rotating log in `%LOCALAPPDATA%\<App>\logs` (XDG state /
    `~/Library/Logs` elsewhere). A console app keeps its console.
  - **Crash reporter** — `sys.excepthook` and `threading.excepthook` save a
    report (traceback, app version, OS, Python, time; no environment, user or
    machine name) to `…\<App>\crashes` and say where in a native dialog
    (`MessageBoxW`, stderr elsewhere). An optional support page opens **only if
    the user clicks Yes**; nothing is sent.
  - **Single instance** — a named mutex on Windows, an `fcntl` lock elsewhere;
    a second copy shows a message and exits.
  - **Signed self-updater** — `update.json` plus `update.json.sig`, an
    **Ed25519** signature over the manifest's exact bytes, checked against the
    public key embedded in the app *before* the JSON is read. HTTPS only;
    redirects are re-checked, so HTTPS → HTTP is refused. The download's size
    and SHA-256 must match before anything is replaced. One-file builds: the
    running EXE is renamed to `.old`, the new one moved in, the app restarted
    with PyInstaller's environment reset, and `.old` removed on the next start.
    Folder builds: the manifest points to an installer, which is verified and
    launched with the configured arguments. `p2e_runtime.updates.check()` /
    `apply(info)` are synchronous and UI-free; an opt-in start-up check asks
    with a native Yes/No dialog on Windows and never installs without one.
- **Verify-only Ed25519 in pure Python**, after the RFC 8032 reference code,
  with the checks it requires (`S < L`, canonical points). The converter signs
  with the same point arithmetic; the runtime cannot sign.
- **Signing key management** — *Generate key pair*, *Back up* (after a warning;
  refused inside the project or output folder) and *Import*. The private key
  lives in `<config>/signing/` with owner-only permissions and is never
  written to the project, a build, a settings or preset file, or the log.
  Replacing a key asks first and keeps the old one.
- **Publish an update** — writes and signs `update.json` next to a new build
  (the result is re-verified by the runtime's own code first). Nothing is
  uploaded; GitHub Releases is 1.6.
- **Preview** of exactly what is embedded: the two-line runtime hook and
  `p2e_runtime.json`. The command preview, the diagnostic run (crash dialog and
  start-up check left out so it never blocks or reaches the network) and batch
  builds (one kit per job) embed it too.
- **Doctor**: with `resource_path` on, the relative-paths finding offers the
  one-line `from p2e_runtime import resource_path` instead of a function to
  paste. `stream_in_windowed`, `package_console_streams` and the runtime
  `streams_none` gain an **alternative fix** — *redirect output to a log file*
  — next to *turn the console back on* (new `runtime` fix kind, a 🔀 button on
  the Doctor tab). New findings: code importing `p2e_runtime` with the kit off,
  and every updater misconfiguration (no/insecure URL, no/invalid key, unusable
  version, bad support link, folder build needs an installer).
- **Build report** lists the Runtime Kit services embedded.

#### Security
- The kit is configured through **structured `BuildConfig` fields** (booleans
  and text, strictly typed on load), never through `extra_args`. The converter
  writes the runtime hook itself at build time and passes it to PyInstaller
  without storing it, so it does not trip the untrusted-settings warning,
  while a `--runtime-hook` inside `extra_args` still does.
- A settings file, preset or history entry that sets an update key **other than
  your own** is shown before it is applied (it would let that key's owner
  install programs on your users' machines), as is a crash-dialog support link.
- `http://localhost` is accepted only behind a test-only flag that the UI and
  settings files cannot set.
- The converter's smoke test and diagnostic run start the EXE with
  `P2E_RUNTIME_NO_DIALOGS=1`: on Windows a crash dialog would otherwise keep a
  crashed app "alive" until the timeout and the test would pass. Dialogs fall
  back to stderr, and the start-up update check is skipped (nobody to ask).

#### Fixed (found by the real build)
- PyInstaller's bootloader calls `sys.__stdout__.flush()` at exit whenever
  `sys.stdout` was replaced; with `__stdout__` still `None` that raised, and the
  crash reporter would have filed a crash on every normal exit. The log
  redirection fills `__stdout__`/`__stderr__` too.
- After an update, the restarted copy could find the single-instance lock still
  held by the exiting one and quit; the lock is now released before the
  restart.
- `QPlainTextEdit` had no theme rule (a white box in the dark theme).
- In Arabic, code inside sentences (`print()`, `/SILENT`) and the key
  fingerprint came out reordered. Qt 5.15 did not keep `print()` intact inside
  an LRI/PDI isolate, so this tab brackets such runs with left-to-right marks;
  checkbox labels, which reorder mixed text regardless, are pure Arabic.

#### Measured
- A one-file "hello" build: **7.08 MiB** without the kit, **7.26 MiB** with
  four services, **7.81 MiB** with all five — services are imported by name, so
  the updater's `ssl`/`urllib` are only bundled when it is on.
- Signature verification: about 4 ms per check in CPython.

#### Tests
- 280 new tests (1223 total, 6 of them `slow`): all five RFC 8032 §7.1 vectors
  for the verifier *and* the signer; tampered manifest, tampered or truncated
  signature, wrong key, malleable `S`, non-canonical points; SHA-256 and size
  mismatches (the old EXE untouched); HTTP, HTTP-redirect and non-localhost
  refusals; version ordering; `resource_path` frozen (one-file and folder) and
  not; report content; the lock (including after its holder dies); the
  rename/swap/rollback on this OS and the Windows branches through injected
  functions; an updater integration test against `http.server`. A `slow`
  test builds a real EXE with every service and checks, from a neutral
  folder: bundled data found, a crash report written, a second copy exits,
  `print`/`sys.stdout.write` reach the log with no descriptors 1 and 2, and a
  signed update from a local server replaces the running EXE, restarts it and
  removes `.old`. Core tests pass without PyQt5 and on Python 3.9; the
  runtime's tests also on 3.8.
- **Not verified here (Linux CI):** the real Windows rename of a running
  `.exe`, `MessageBoxW`, and the named mutex. Their logic is tested through
  injected functions only.

### 1.4.0 — Isolated build environment, size lab, build report

Second release of [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md): smaller EXEs,
reproducible builds, and a record of what went into each one.

#### Added
- **Isolated build environment per project** (new ⚖️ *Size & Environment* tab,
  shown in simple mode). PyInstaller bundles whatever its hooks find installed,
  so building from a Python full of libraries bloats the EXE. The environment
  holds only what the project imports — following imports through its own
  helper modules and packages (`core/project_scan.py`), mapped to PyPI names
  through the knowledge base — or, when present, `requirements.txt`, or the new
  `p2e-build.lock`. Created with `uv` when installed (seconds) or `venv` + pip;
  if a guessed package name fails, the rest are retried one at a time and the
  failures named. **Nothing runs before the exact commands are shown and
  approved.** Environments live in the per-user *cache* folder
  (`%LOCALAPPDATA%` on Windows, not the roaming profile). Building, the
  diagnostic run, batch builds, the command preview and the PyInstaller check
  all use the environment's interpreter; building with an environment that does
  not exist yet offers to create it first.
- **Lock file** — `🔒 Save lock file` writes `p2e-build.lock` (exact versions,
  build tooling left out) next to the project; environments are then rebuilt
  from it.
- **The doctor checks the build interpreter**, not the app's own Python: an
  environment is asked in one subprocess what it can import. Its checks also
  follow local helper modules now, so a package imported only by `helpers.py`
  is reported missing too. With an environment not yet created, one
  `env_not_created` finding replaces a flood of "missing package" errors.
- **Size lab.** After each build, what is inside — library by library — read
  from PyInstaller's own TOC files (`ast.literal_eval`, never executed). The
  compressed module archive's real size is spread over its modules, so the
  figures add up to what is on disk (verified: 64.8 MB inventoried for a
  64.8 MB folder build). Distribution-named folders (`pillow.libs`) are counted
  with their package (`PIL`). Shows the change against the previous build of
  the same script (sizes are now stored in build history), and hints when
  libraries the code never imports take up space or when a one-file EXE is big
  enough to start slowly.
- **Slimming suggestions** — curated `--exclude-module` candidates (tkinter,
  unused Qt bindings, matplotlib, IPython, pytest…) present in the bundle but
  never imported by the project; *Exclude* or *Exclude and rebuild*. The doctor
  loop catches it if a library did need one.
- **HTML build report** after each successful build (on by default):
  `<name>-build-report.html` beside `dist/` with sizes, breakdown, largest
  files, SHA-256, Python/PyInstaller/platform versions, doctor notes and the
  PyInstaller options. One self-contained file — no scripts, no external
  resources — with every value escaped; RTL in Arabic, light and dark.
- **🧊 Test in Windows Sandbox** (Doctor tab) — writes a `.wsb` that maps the
  output read-only into a clean, throw-away Windows and runs the EXE. Where
  Sandbox is unavailable it says so and how to test on a clean machine instead.

#### Fixed
- The `&` in a tab title was eaten as a keyboard mnemonic ("Size _Environment").
- Tree widgets and scroll areas had no theme rules (white table, pale text).
- Sizes and percentages read "MB 41.6" in right-to-left text; they are now
  isolated as left-to-right runs in the app and in the report.

#### Measured
- A Pillow-only app: **30.1 MB** built from the system Python (which pulled in
  numpy) → **14.2 MB** from its isolated environment (**−53%**).

#### Tests
- 116 new tests (943 total): import scanning, environment planning, lock files,
  safe deletion (never outside the environments folder), the import checker,
  TOC parsing (including that it never executes), grouping, size accounting,
  suggestions, history sizes, the report (escaping, RTL, empty sections), the
  `.wsb` XML, and the tab's wiring. Core tests still pass without PyQt5 and on
  Python 3.9.

### 1.3.0 — Project doctor and diagnostics

First release of [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md): the tool now
answers "why won't my EXE work?" instead of only running PyInstaller.

#### Added
- **Project doctor** (new 🩺 tab, shown in simple mode too) — reads the
  script with `ast`, never runs it, and reports what works under Python but
  breaks once frozen: imports the build interpreter cannot resolve (the EXE
  would die with `ModuleNotFoundError`), data files the code opens that are not
  bundled, relative paths that resolve against the working folder rather than
  the bundle, `multiprocessing` without `freeze_support()`, `input()` and direct
  `sys.stdout`/`sys.stderr` use in windowed apps, a script with no entry point
  (and which sibling looks like the real one), two Qt bindings, and `.ico`
  files that are renamed PNGs or hold a single size. Readiness score out of
  100, also shown as a badge beside the source field. Re-examines on its own
  when the script, icon or console options change.
- **One-click fixes.** Each finding carries the config changes that resolve
  it (hidden import, bundled file/folder, `--collect-*`/`--copy-metadata`/
  `--exclude-module`, console back on, a different entry script). Tick, then
  *Apply* or *Apply and rebuild*. The user's source is never edited: fixes
  that need a code change come as a snippet to copy (`resource_path()`,
  `freeze_support()`, silencing `None` streams, a `main()` guard), and
  missing packages come with their `pip install` command.
- **Build and runtime diagnostics.** After every build the doctor reads the
  build log (multiple Qt bindings, unreadable icon format, a locked output
  file, `--add-data` paths that do not exist, PyInstaller not installed) and
  `warn-<name>.txt`, keeping only modules *the user's code* imports — the raw
  file lists dozens of harmless platform modules. A warn file older than the
  build is ignored. The smoke test now keeps everything the EXE printed and
  runs it from a neutral folder, as a shortcut would; its traceback is matched
  against known failures (missing module or package metadata, missing data
  file inside `_MEI…`/`_internal`, Flask `TemplateNotFound`, lost stdin,
  `None` streams, DLL load failures). An unrecognised traceback is surfaced
  verbatim, never guessed at. A failed build's message box says how many
  likely causes the doctor found.
- **Diagnostic run.** A windowed EXE that crashes shows its traceback in a
  dialog, so no test could read it. The button builds the same app with the
  console on into `<output>/p2e_diagnostic` (the real build is untouched),
  runs it, and diagnoses what it printed.
- **Package knowledge base** — `py2exe_gui/knowledge/packages.json`, 45
  entries keyed by import name: pip names that differ (`cv2` → `opencv-python`),
  collection flags (`docx`, `pptx`, `customtkinter`, `apscheduler`, `whisper`…),
  hidden imports (`tkcalendar` → `babel.numbers`, `pyttsx3`, `plyer`), folders
  a framework expects (`flask` → `templates`/`static`), packages that write to
  console streams (`tqdm`, `uvicorn`), and size notes. Data, not code, so it can
  grow by pull request; shipped in the wheel via `package-data`.
- **🎨 Icon Studio** — builds a real `.ico` with all seven sizes Windows asks
  for (16–256px), from an image (fitted, not stretched) or from one or two
  letters on a coloured shape. Drawn with Qt and packed as PNG-in-ICO, so no
  Pillow dependency.

#### Fixed
- Dialogs had no themed background: their labels used the theme's light text
  colour on the platform's default light grey. `QDialog` now shares the main
  window's background rule.

#### Tests
- 161 new tests (827 total): every doctor check, every diagnostic pattern
  (fed with verbatim PyInstaller 6 / CPython output), the warn-file parser and
  its filtering, the knowledge file's schema and bilingual notes, `.ico`
  packing, fix application, the Doctor tab, the diagnostic thread, and Icon
  Studio. Core tests still run without PyQt5 and on Python 3.9.

### Phase 9 — Interface overhaul and new features

Implements [UI_IMPROVEMENT_PLAN.md](UI_IMPROVEMENT_PLAN.md): the whole of its
Phase 9 (interface) plus the batch, update-check and preset items from Phase 10.

#### Added — interface
- **Simple mode, and it is the default.** A new user met nine tabs of
  PyInstaller options when all they wanted was one `.exe`. Simple mode shows
  three (Main, Templates, About); `Ctrl+M` or the mode button reveals the rest.
  A one-time welcome dialog asks which to start in. Hidden tabs are detached
  from the tab bar, never destroyed, so switching modes mid-setup loses nothing.
- **Two new themes and an automatic one.** `nord` and `high-contrast` join dark
  and light, and `auto` follows the OS setting (registry on Windows, `defaults`
  on macOS, `gsettings`/`GTK_THEME` on Linux). Selectable from the Templates
  tab; `Ctrl+T` still flips dark/light.
- **Font zoom** — `Ctrl++` / `Ctrl+-` / `Ctrl+0`, persisted, clamped to
  0.7×–2.0×. Every size in the stylesheet scales, not just the log.
- **System tray icon and desktop notifications.** A build runs for minutes; the
  only way to know it had finished was to keep watching the window. Notifies on
  success and failure, and only when the window is not already focused.
  Degrades to a no-op where no tray exists (headless CI, bare WMs).
- **Log severity filter** — All / Errors / Warnings / Success, beside the
  existing text search. Export still writes the *whole* log, not just what the
  filter shows.
- **Icon preview** at 16/32/48/64px, the sizes Windows actually requests. A PNG
  renamed to `.ico` gives itself away here instead of in the taskbar.
- **Platform notices.** The Deploy, Installer and Version Info tabs now say
  plainly, up front, that signing, manifests, version resources and Inno Setup
  only take effect when building on Windows. Previously they rendered
  identically on Linux and macOS and the failure only surfaced after a build as
  a tool-not-found error.

#### Added — features
- **Batch conversion** (new `📚` tab): queue several `.py` files and build them
  all with the current settings, with a per-file status marker and a summary.
  Runs strictly sequentially — PyInstaller shares `build/` and `dist/` and
  concurrent runs corrupt each other's intermediates. Verified end to end
  against PyInstaller 6.22.
- **Named presets**: save the current form under a name and restore it in one
  click, plus export/import for sharing. An imported preset goes through the
  same `--runtime-hook` confirmation as a settings file.
- **Update check** — report-only and **off by default**. Reports a newer
  GitHub release and offers to open the page; it never downloads or runs
  anything, matching the explicit-consent rule Phase 8 applied to `pip install`.

#### Fixed
- **Progress bar reflected chattiness, not progress.** It nudged forward
  whenever a line containing `Analyzing`/`Processing`/`Building` appeared, so
  two projects sat at completely different values at the same point in the
  build. `core/build_stages.py` now reads the phase PyInstaller announces
  (`Building PYZ`, `Building EXE`, …) and names it above the bar. Progress is
  monotonic and never reaches 100 from log text alone — only a zero exit code
  means done.
- **Contrast failures across both existing themes.** The light theme's primary
  Build button was white-on-`#40a02b` at **2.96:1**, well under WCAG AA; the
  status bar was 3.59:1 (dark) and 3.73:1 (light), and the About tab's muted
  text 4.45:1. Every palette now clears 4.5:1 on text, buttons, tabs and status
  bar, enforced by tests over all four themes.
- **Theme changes left earlier log lines in the old palette**, because colours
  are baked into the HTML when a line is appended. The log now re-renders from
  a buffer on theme change.
- **`closeEvent` could orphan a running build**: it only checked the conversion
  thread, and did not clean up temp files on the way out.

#### Changed
- **`styles.py` is palette-driven.** Two hand-maintained ~200-line CSS strings
  became one template rendered from a colour table, so a theme is now a
  dictionary of colours (and adding the two new ones did not duplicate a single
  selector). `DARK_THEME`, `LIGHT_THEME` and `THEMES` still exist and still
  render the same rules.
- **`MainWindow.__init__` no longer blocks.** The first-run dialog and update
  check moved to `run_startup_tasks()`, called by `app.main` after the window is
  shown — a constructor that opens a modal cannot be instantiated by a test.
- `is_windows()` accepts `cygwin` and `msys`, which do reach the Windows SDK.
- Version bumped to 1.2.0; presets live in `presets.json` beside settings and
  history.

329 -> 666 tests. Core coverage 97%.


### Phase 8 — Priority fix plan (review items 3-30)

Implements the prioritised fix plan from the full repository review. Items 1,
2, 4, 5 and 12 shipped in Phase 7; this covers the rest.

#### Fixed — critical
- **Silent dependency install** (`main_window.py`): `pip install pyinstaller`
  ran unattended on the first build — no consent, no version pin, from
  whatever index the environment pointed at. The user now sees the exact
  command and must approve it, and the requirement is pinned to `>=6.0,<7`.

#### Fixed — important
- **UI froze during post-build steps**: signing waits on a timestamp server
  (up to 120s) and the smoke test waits on the new EXE; both ran inline on the
  UI thread. Moved to `PostBuildThread`, which chains into the installer step.
- **Untrusted settings files**: loading a config containing `--runtime-hook`,
  `--additional-hooks-dir`, `--add-binary`, `--upx-dir` or `--runtime-tmpdir`
  now warns and requires confirmation. Such a file injects code into every EXE
  produced — including ones the user then signs. Also applied when restoring
  from build history.
- **Window did not fit a 1366x768 laptop**: the 1080x800 minimum was a hard
  floor. Now 900x600 minimum with 1080x800 as the default size.
- **Accessibility**: every icon-only browse button gained a tooltip and an
  accessible name (five identical "📂" buttons previously announced nothing);
  buttons gained a visible focus ring.
- **About tab was unreadable in the light theme**: it was one HTML blob with
  dark-theme colours and `direction: rtl` baked in. Rebuilt from themed
  widgets driven by the stylesheet, so it follows both theme and locale.
- **Dialogs forced RTL** regardless of locale; they now inherit direction.
- **Clearing build history** asks first — 20 records, no undo.
- **Standard-library list** held 11 names, so auto-detect suggested `typing`,
  `collections`, `logging` and friends as hidden imports. Now uses
  `sys.stdlib_module_names` (~300 names) with a fallback for Python < 3.10.
- **Certificate password on the command line**: signtool can now select a
  certificate from the Windows store by subject (`/n`), so no password is
  passed as an argument at all.

#### Fixed — polish
- Log colours: one palette per theme. The single shared palette failed WCAG AA
  on 3/5 levels against the light background and 2/5 against the dark one.
  Measured ratios are documented and enforced by a test.
- `styles.py` is the only colour source; the duplicate table in
  `log_formatter.py` is gone, as is the unused `LogColors` class and the dead
  `version_info._PathBundle`.
- Temp version/manifest files are cleaned on every exit path and before being
  re-created (one path leaked into `%TEMP%`).
- `version_info` escaping now covers newline, carriage return, tab and control
  characters — a pasted multi-line value used to break out of the generated
  Python literal. Non-ASCII is left verbatim so Arabic stays readable.
- `BuildRecord.from_dict` ignores unknown keys, and one malformed entry no
  longer discards the entire history file.
- `except Exception: pass` replaced with typed handling that reports the
  reason via `last_error` and the build log.
- Settings and history moved from the working directory to the per-user config
  directory, with a one-time migration of any legacy file.
- Log search is debounced (it re-searched on every keystroke); the stylesheet
  uses point sizes so system font scaling applies; Arabic locales get a font
  stack that actually ships Arabic glyphs.

#### Changed
- **`main_window.py` split into tab widgets** (1,886 -> 1,050 lines). Each tab
  lives in `py2exe_gui/ui/tabs/` and owns its own controls and handlers; the
  window keeps orchestration. Tabs construct standalone, so they can be tested
  in isolation.
- **Language switching no longer requires a restart.** `retranslate()`
  snapshots the form, rebuilds the central widget under the new locale and
  restores state, including the log and keyboard shortcuts.

#### Added
- `tests/test_pyinstaller_flags_integration.py` — asks PyInstaller `--help`
  which options exist and asserts every flag the builder emits is real. This
  is the check that was missing when `-O2` and `--upx-level` shipped. Includes
  a `slow`-marked end-to-end build that runs the produced executable.
- Headless GUI suite for `MainWindow`, previously at 0% coverage.
- `pip-audit` and Dependabot (pip + github-actions); the CI test job enforces
  `--cov-fail-under=90` on `py2exe_gui.core` and a separate job runs the GUI
  tests offscreen.

160 -> 329 tests.


### Phase 7 — Full installer pipeline (PyInstaller → Inno Setup)

#### Added
- `core/installer.py`: `InstallerConfig` + a pure `generate_iss_script()` that
  emits a complete Inno Setup 6 script (`[Setup]`, `[Languages]`, `[Tasks]`,
  `[Files]`, `[Icons]`, `[Registry]`, `[Run]`)
- Deterministic `AppId` derived from (publisher, app name) via UUIDv5, so a new
  Setup.exe **upgrades** the previous install instead of installing beside it
- `find_iscc()` — locates `ISCC.exe` via `INNO_SETUP_ISCC`, PATH, then the
  standard Inno Setup 6/5 install directories
- `build_iscc_command()` with optional `/Sbyparam=` wiring, so the produced
  Setup.exe can be Authenticode-signed with the Deploy tab's certificate
- New "📦 Installer" tab: identity, output, license/README/setup icon,
  privileges, architecture, compression, 13 bundled languages (+ optional
  unofficial Arabic `.isl`), desktop icon, launch-after-install, file
  association, and an ISCC path picker
- "Generate .iss only" (dry run) and "Build installer now" actions
- `InstallerThread` — the compiler runs off the UI thread
- 66 new tests (`tests/test_installer.py`, plus builder coverage)

#### Fixed
- **`--optimize`**: the optimization dropdown emitted `-O1`/`-O2`, which
  PyInstaller rejects with `unrecognized arguments` — every build with a
  non-zero optimization level failed. Now emits `--optimize LEVEL`.
- **UPX**: `--upx-level=N` is not a PyInstaller option and broke every build
  with UPX enabled; `--upx-dir=upx` pointed at a non-existent relative folder.
  The level spinbox is replaced by a UPX directory picker, and the flag is
  omitted entirely when no directory is given (PyInstaller then searches PATH).
- **`--add-data`**: `DEST` is a destination *directory*, so `file.txt;file.txt`
  buried each extra file inside a folder of its own name. Files now go to `.`
  and directories keep their own name.
- **Extra arguments**: `str.split()` shredded any quoted path containing
  spaces; replaced with platform-aware `shlex` tokenization.

#### Changed
- Minimum PyInstaller bumped to `>=6.0` (required by `--optimize`)
- `BuildConfig` gained `upx_dir`; `upx_level` is retained but ignored so old
  saved configs still load
- CI workflow declares `permissions: contents: read`

### Phase 6 — Templates & Documentation

#### Added
- 5 new built-in templates: FastAPI, Streamlit, Kivy, Discord bot, Click CLI
- English README (`README_EN.md`) with full feature coverage
- Bilingual `CONTRIBUTING.md` with development setup and architecture rules
- `CHANGELOG.md` recording all phases
- GitHub issue templates for bug reports and feature requests

### Phase 5 — Deployment Features

#### Added
- Splash screen field (`--splash`)
- Windows manifest generator: DPI awareness, UAC level, supported OS versions
- Code signing via `signtool.exe` (with password redaction in logs)
- Post-build smoke test runner
- New "🚀 Deploy" tab grouping all four sections

#### Changed
- `BuildConfig` gained `splash_image` and `manifest_file` fields
- Post-build hook runs on success: locate EXE → sign → smoke-test → cleanup

### Phase 4 — Pro Features

#### Added
- AST-based dependency analyzer (catches `__import__`, `importlib.import_module`, conditional imports)
- `requirements.txt` import → hidden imports
- Version info editor (8 Windows metadata fields, `--version-file`)
- Build history (last 20 builds, persistent, with one-click restore)
- New tabs: "📝 Version Info" and "🕓 History"

#### Changed
- `BuildConfig` gained `version_file` field
- `dependency_analyzer` rewritten on top of `ast.parse` with line-based fallback

### Phase 3 — Internationalization

#### Added
- Full English translation (`class En` in `strings.py`)
- Locale proxy (`_LocaleProxy`) for live language switching
- Language selector combo box (persisted)
- RTL/LTR layout direction switches with the locale
- 12 i18n tests including key-parity check between `Ar` and `En`

#### Changed
- Template keys are now stable ASCII identifiers
  (`gui`/`console`/`web`/`data`/`game`/`custom`)
- `templates.py` provides `template_name()` and `template_description()`
  helpers that resolve through the active locale

### Phase 2 — UX Improvements

#### Added
- Drag & drop: `.py/.pyw` → source, `.ico` → icon, others → extras
- Command preview dialog (Ctrl+P) with copy-to-clipboard
- Real-time log search, severity-based coloring, export to file
- Light theme (Catppuccin-Latte) + dark/light toggle (Ctrl+T)
- 10 keyboard shortcuts for common actions

### Phase 1 — Foundation

#### Added
- `py2exe_gui/` package layout (split 1,243-line monolith into 16 modules)
- `core/` modules: UI-independent, fully testable
- `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`
- GitHub Actions CI: pytest matrix (Python 3.9–3.12) + ruff lint
- Test suite (38 tests covering builder, config, dependency analyzer)
- `IDEAS.md` with the full roadmap

#### Changed
- `python_to_exe.py` is now a 23-line entry point that delegates to
  `py2exe_gui.app.main`. Existing `python python_to_exe.py` invocation
  preserved for backward compatibility.

---

## [1.0.0] — 2025

Initial single-file PyQt5 wrapper around PyInstaller with Arabic GUI.

- 4 tabs (Main, Advanced, Templates, About)
- 6 built-in templates
- Save/load JSON settings
- Real-time progress bar with PyInstaller log
