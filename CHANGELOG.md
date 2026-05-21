# Changelog

All notable changes to this project are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
