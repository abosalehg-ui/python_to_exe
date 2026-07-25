# Changelog

All notable changes to this project are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
