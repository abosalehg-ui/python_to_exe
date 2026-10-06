# Changelog

All notable changes to this project are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
