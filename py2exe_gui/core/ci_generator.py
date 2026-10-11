"""The GitHub Actions workflow for a project: ``.github/workflows/p2e-release.yml``.

Written **into the user's repository**, next to their ``p2e.toml``, and only
after they saw the whole file and said yes (the GUI shows it in a dialog, the
command line prints it and asks, or takes ``--yes``). What it does:

* a ``build`` job on ``windows-latest``, ``macos-latest`` and ``ubuntu-latest``
  that installs this tool's command line (without Qt), runs
  ``py2exe-gui release --no-tag --no-publish`` against the project file —
  the doctor, the build, signing on Windows, the installer, the portable
  ZIP, the Linux and macOS packages, the checksums — and uploads the release
  folder as an artifact;
* pip caching (``actions/setup-python``) and a cache of the build
  intermediates (``actions/cache``);
* a ``release`` job, on a ``v*`` tag only, that downloads the three
  artifacts, merges the checksum files and creates the GitHub Release with
  ``gh``, using the workflow's own token.

Secrets (a Windows certificate as base64 and its password; a macOS
certificate, its password, the signing identity and the notarization
account) are referenced as ``${{ secrets.NAME }}`` and nothing else: this
module never reads one, so it cannot write one. A test feeds secret-looking
values through every input and checks the output for them.

The YAML is rendered from strings on purpose (no PyYAML in the core): the
output has comments, and its shape must not depend on a dumper's choices.
"""

import os
import re
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from py2exe_gui.constants import APP_VERSION
from py2exe_gui.core.diagnostics import build_root
from py2exe_gui.core.fixes import SEVERITY_ERROR, SEVERITY_WARNING, Finding
from py2exe_gui.core.platform_support import is_supported
from py2exe_gui.core.release import git

WORKFLOW_RELATIVE = ".github/workflows/p2e-release.yml"
WORKFLOW_NAME = "p2e release"
#: How the runner gets this tool's command line. Pinned to a branch rather
#: than a release so a project on 2.0.0-dev can use it today; the user may
#: replace it with a tag (``@v2.0.0``) or a PyPI requirement.
DEFAULT_TOOL_REQUIREMENT = "py2exe-gui @ git+https://github.com/abosalehg-ui/python_to_exe.git@main"
DEFAULT_PYTHON = "3.12"
RUNNERS = (("windows-latest", "Windows"), ("macos-latest", "macOS"), ("ubuntu-latest", "Linux"))
ACTIONS = {
    "checkout": "actions/checkout@v4",
    "setup-python": "actions/setup-python@v5",
    "cache": "actions/cache@v4",
    "upload": "actions/upload-artifact@v4",
    "download": "actions/download-artifact@v4",
}

#: Every secret the workflow can name, with the step that needs it.
SECRET_NAMES = {
    "WINDOWS_CERT_BASE64": "sign_windows",
    "WINDOWS_CERT_PASSWORD": "sign_windows",
    "MACOS_CERT_BASE64": "notarize_macos",
    "MACOS_CERT_PASSWORD": "notarize_macos",
    "MACOS_SIGN_IDENTITY": "notarize_macos",
    "MACOS_NOTARY_APPLE_ID": "notarize_macos",
    "MACOS_NOTARY_TEAM_ID": "notarize_macos",
    "MACOS_NOTARY_PASSWORD": "notarize_macos",
}
_SECRET_REF = re.compile(r"\$\{\{\s*secrets\.([A-Za-z0-9_]+)\s*\}\}")
_VERSION_RE = re.compile(r"^3\.(\d{1,2})$")


@dataclass
class CiOptions:
    """Everything the template needs, all derived from the project file and
    the repository layout — never from the environment."""

    app_name: str = "app"
    project_rel: str = "p2e.toml"  # the project file, relative to the repo root
    release_root_rel: str = "release"  # where ``release/<version>/`` lands
    build_cache_rel: str = "build"  # the engine's intermediates
    requirements_rel: str = ""  # the project's requirements.txt, if any
    python_version: str = DEFAULT_PYTHON
    engine: str = "pyinstaller"
    tag_prefix: str = "v"
    branch: str = "main"
    formats: List[str] = field(default_factory=list)
    sign_windows: bool = False
    cert_path_rel: str = ""  # where the decoded certificate must be written
    notarize_macos: bool = False
    allow_doctor_errors: bool = False
    draft: bool = False
    prerelease: bool = False
    tool_requirement: str = DEFAULT_TOOL_REQUIREMENT

    def secrets_used(self) -> List[str]:
        used = []
        for name, step in SECRET_NAMES.items():
            if (step == "sign_windows" and self.sign_windows) or (
                    step == "notarize_macos" and self.notarize_macos):
                used.append(name)
        return used


# ── From the project to the options ───────────────────────────────────────


def repo_root(folder: str, runner: Optional[Callable] = None) -> str:
    """The git work tree holding ``folder``, or '' when it is not in one."""
    try:
        return git.run_git(["rev-parse", "--show-toplevel"], folder, runner).strip()
    except git.GitError:
        return ""


def _relative(path: str, root: str) -> str:
    rel = os.path.relpath(path, root)
    return rel.replace(os.sep, "/")


def options_for(project, project_path: str, root: str = "",
                python_version: str = "", tool_requirement: str = "",
                branch: str = "main") -> Tuple[CiOptions, List[Finding]]:
    """The options for ``project`` (loaded from ``project_path``) in the
    repository rooted at ``root`` (default: the project file's folder), and
    the findings that explain what the workflow cannot do."""
    project_path = os.path.abspath(project_path)
    project_dir = os.path.dirname(project_path)
    findings: List[Finding] = []
    if not root:
        root = project_dir
        findings.append(Finding("ci_not_git", SEVERITY_WARNING, {"path": project_dir}))
    root = os.path.abspath(root)
    opts = CiOptions(app_name=project.display_name() or "app")
    opts.project_rel = _relative(project_path, root)
    release_root = os.path.join(build_root(project.build) or project_dir, "release")
    opts.release_root_rel = _relative(release_root, root)
    opts.build_cache_rel = _relative(os.path.join(build_root(project.build) or project_dir,
                                                  "build"), root)
    if opts.release_root_rel.startswith("..") or opts.project_rel.startswith(".."):
        findings.append(Finding("ci_output_outside_repo", SEVERITY_ERROR,
                                {"path": release_root, "root": root}))
    requirements = os.path.join(project_dir, "requirements.txt")
    if os.path.isfile(requirements):
        opts.requirements_rel = _relative(requirements, root)
    ci = project.ci
    version = (python_version or ci.python_version or DEFAULT_PYTHON).strip()
    opts.python_version = version if _VERSION_RE.match(version) else DEFAULT_PYTHON
    opts.engine = project.build.engine or "pyinstaller"
    opts.tag_prefix = project.release.tag_prefix or "v"
    opts.branch = branch or "main"
    opts.draft = bool(project.release.draft)
    opts.prerelease = bool(project.release.prerelease)
    opts.formats = list(project.packaging.enabled_formats())
    opts.allow_doctor_errors = bool(ci.allow_doctor_errors)
    opts.tool_requirement = (tool_requirement or DEFAULT_TOOL_REQUIREMENT).strip()
    signing = project.signing
    if ci.sign_windows:
        if signing.enabled and signing.cert_path and not signing.use_cert_store:
            opts.sign_windows = True
            opts.cert_path_rel = _relative(signing.cert_path, root)
        else:
            findings.append(Finding("ci_signing_not_configured", SEVERITY_WARNING, {}))
    opts.notarize_macos = bool(ci.notarize_macos)
    return opts, findings


# ── Rendering ─────────────────────────────────────────────────────────────


def _q(text: str) -> str:
    """A double-quoted YAML scalar."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _sh(text: str) -> str:
    """A POSIX single-quoted word for a ``run:`` line.

    Single quotes are the only quoting the shell never looks inside: a
    double-quoted word would still expand ``$VAR``, ``$(...)`` and
    backticks, so a project name (which comes from a shared file) could run
    a command on the runner. A literal ``'`` is written as ``'\\''``.
    """
    return "'" + text.replace("'", "'\\''") + "'"


def _ps(text: str) -> str:
    """A PowerShell single-quoted literal (no interpolation; ``'`` is doubled)."""
    return "'" + text.replace("'", "''") + "'"


def _artifact_stem(name: str) -> str:
    """An artifact name without the characters GitHub rejects."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip()).strip("-.")
    return cleaned or "app"


def render_workflow(opts: CiOptions) -> str:
    """The workflow text. Pure: the same options give the same bytes."""
    out: List[str] = []
    add = out.append
    add(f"# Generated by Python to EXE Converter {APP_VERSION} (py2exe-gui ci).")
    add(f"# Builds {opts.app_name} from {opts.project_rel} on Windows, macOS and Linux,")
    add(f"# and publishes a GitHub Release when a {opts.tag_prefix}* tag is pushed.")
    add("#")
    add("# Secrets are referenced by name only (Settings → Secrets and variables → Actions):")
    for name in opts.secrets_used():
        add(f"#   {name}")
    if not opts.secrets_used():
        add("#   (none: signing and notarization are off)")
    add("# This file holds no credential; regenerate it with: py2exe-gui ci --yes")
    add("")
    add(f"name: {_q(WORKFLOW_NAME)}")
    add("")
    add('"on":')
    add("  push:")
    add(f"    branches: [{_q(opts.branch)}]")
    add(f"    tags: [{_q(opts.tag_prefix + '*')}]")
    add("  pull_request:")
    add("  workflow_dispatch:")
    add("")
    add("permissions:")
    add("  contents: read")
    add("")
    add("env:")
    add('  PYTHONUTF8: "1"')
    add('  PIP_DISABLE_PIP_VERSION_CHECK: "1"')
    if opts.engine == "nuitka":
        add('  NUITKA_UPDATE_CHECK: "never"')
    add("")
    add("jobs:")
    out += _build_job(opts)
    add("")
    out += _release_job(opts)
    return "\n".join(out) + "\n"


def _build_job(opts: CiOptions) -> List[str]:
    lines: List[str] = []
    add = lines.append
    add("  build:")
    add("    name: Build (${{ matrix.os }})")
    add("    runs-on: ${{ matrix.os }}")
    add("    strategy:")
    add("      fail-fast: false")
    add("      matrix:")
    add("        os: [" + ", ".join(runner for runner, _label in RUNNERS) + "]")
    add("    steps:")
    add(f"      - uses: {ACTIONS['checkout']}")
    add("        with:")
    add("          fetch-depth: 0  # the release notes come from the git log")
    add("")
    add(f"      - uses: {ACTIONS['setup-python']}")
    add("        with:")
    add(f"          python-version: {_q(opts.python_version)}")
    add("          cache: pip")
    add("          cache-dependency-path: |")
    add(f"            {opts.project_rel}")
    if opts.requirements_rel:
        add(f"            {opts.requirements_rel}")
    add("")
    add("      - name: Cache the build intermediates")
    add(f"        uses: {ACTIONS['cache']}")
    add("        with:")
    add("          path: |")
    add(f"            {opts.build_cache_rel}")
    if opts.engine == "nuitka":
        add("            ~/.cache/Nuitka")
        add("            ~/Library/Caches/Nuitka")
        add("            ~/AppData/Local/Nuitka/Nuitka/Cache")
    hashed = ", ".join("'" + p + "'" for p in (opts.project_rel, opts.requirements_rel) if p)
    add(f"          key: p2e-{opts.engine}-${{{{ runner.os }}}}-${{{{ hashFiles({hashed}) }}}}")
    add(f"          restore-keys: p2e-{opts.engine}-${{{{ runner.os }}}}-")
    add("")
    add("      - name: Install Python to EXE Converter (command line only, no Qt)")
    add("        run: |")
    add("          python -m pip install --upgrade pip")
    add(f"          python -m pip install --no-deps {_sh(opts.tool_requirement)}")
    deps = ['"pyinstaller>=6.0"', '"tomli>=1.1; python_version < \'3.11\'"']
    if opts.engine == "nuitka":
        deps.append('"nuitka[onefile]>=4.2,<5"')
    add("          python -m pip install " + " ".join(deps))
    add("          py2exe-gui --version")
    if opts.requirements_rel:
        add("")
        add("      - name: Install the project's requirements")
        add(f"        run: python -m pip install -r {_sh(opts.requirements_rel)}")
    if opts.sign_windows:
        add("")
        add("      - name: Write the Windows signing certificate (from a secret, to a temp file)")
        add("        if: runner.os == 'Windows' && github.event_name != 'pull_request'")
        add("        shell: pwsh")
        add("        env:")
        add("          CERT_BASE64: ${{ secrets.WINDOWS_CERT_BASE64 }}")
        add("        run: |")
        add(f"          $target = {_ps(opts.cert_path_rel)}")
        add("          New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null")
        add("          [IO.File]::WriteAllBytes($target, [Convert]::FromBase64String($env:CERT_BASE64))")
    if opts.notarize_macos:
        add("")
        add("      - name: Import the macOS signing certificate into a temporary keychain")
        add("        if: runner.os == 'macOS' && github.event_name != 'pull_request'")
        add("        env:")
        add("          CERT_BASE64: ${{ secrets.MACOS_CERT_BASE64 }}")
        add("          CERT_PASSWORD: ${{ secrets.MACOS_CERT_PASSWORD }}")
        add("        run: |")
        add('          keychain="$RUNNER_TEMP/p2e-signing.keychain-db"')
        add('          printf \'%s\' "$CERT_BASE64" | base64 --decode > "$RUNNER_TEMP/p2e-cert.p12"')
        add('          security create-keychain -p "" "$keychain"')
        add('          security set-keychain-settings -lut 21600 "$keychain"')
        add('          security unlock-keychain -p "" "$keychain"')
        add('          security import "$RUNNER_TEMP/p2e-cert.p12" -P "$CERT_PASSWORD" -A -t cert -f pkcs12 -k "$keychain"')
        add('          security set-key-partition-list -S apple-tool:,apple: -s -k "" "$keychain"')
        add('          security list-keychains -d user -s "$keychain" login.keychain-db')
        add('          rm -f "$RUNNER_TEMP/p2e-cert.p12"')
    add("")
    add("      - name: Doctor, build, sign, package, checksums (py2exe-gui release)")
    if opts.sign_windows or opts.notarize_macos:
        add("        env:")
        if opts.sign_windows:
            add("          P2E_SIGN_PASSWORD: ${{ secrets.WINDOWS_CERT_PASSWORD }}")
        if opts.notarize_macos:
            add("          P2E_MACOS_SIGN_IDENTITY: ${{ secrets.MACOS_SIGN_IDENTITY }}")
    command = ["py2exe-gui", "--lang", "en", "release", "--project", _sh(opts.project_rel),
               "--yes", "--no-tag", "--no-publish", "--allow-downloads"]
    if opts.allow_doctor_errors:
        command.append("--allow-doctor-errors")
    add("        run: " + " ".join(command))
    if opts.notarize_macos:
        add("")
        add("      - name: Notarize and staple the .dmg")
        add("        if: runner.os == 'macOS' && github.event_name != 'pull_request'")
        add("        env:")
        add("          APPLE_ID: ${{ secrets.MACOS_NOTARY_APPLE_ID }}")
        add("          TEAM_ID: ${{ secrets.MACOS_NOTARY_TEAM_ID }}")
        add("          APP_PASSWORD: ${{ secrets.MACOS_NOTARY_PASSWORD }}")
        add("        run: |")
        add(f"          for dmg in {_sh(opts.release_root_rel)}/*/*.dmg; do")
        add('            [ -f "$dmg" ] || continue')
        add('            xcrun notarytool submit "$dmg" --apple-id "$APPLE_ID" --team-id "$TEAM_ID" --password "$APP_PASSWORD" --wait')
        add('            xcrun stapler staple "$dmg"')
        add("          done")
    add("")
    add(f"      - uses: {ACTIONS['upload']}")
    add("        with:")
    add(f"          name: {_q(_artifact_stem(opts.app_name) + '-${{ runner.os }}')}")
    add(f"          path: {_q(opts.release_root_rel)}")
    add("          if-no-files-found: error")
    return lines


def _release_job(opts: CiOptions) -> List[str]:
    lines: List[str] = []
    add = lines.append
    add("  release:")
    add("    name: GitHub Release")
    add(f"    if: startsWith(github.ref, 'refs/tags/{opts.tag_prefix}')")
    add("    needs: build")
    add("    runs-on: ubuntu-latest")
    add("    permissions:")
    add("      contents: write")
    add("    steps:")
    add(f"      - uses: {ACTIONS['download']}")
    add("        with:")
    add("          path: artifacts")
    add("")
    add("      - name: Merge the checksum files and create the release")
    add("        env:")
    add("          GH_TOKEN: ${{ github.token }}")
    # The app name reaches the shell through the environment, never inline:
    # a quoted YAML scalar cannot run anything, and "$APP_TITLE" expands to
    # the bytes as written.
    add(f"          APP_TITLE: {_q(opts.app_name)}")
    add("        run: |")
    add("          set -eu")
    add("          cat artifacts/*/*/SHA256SUMS.txt | sort -k2 > SHA256SUMS.txt")
    add("          notes=$(find artifacts -mindepth 3 -maxdepth 3 -name RELEASE_NOTES.md | head -n 1)")
    add("          files=$(find artifacts -mindepth 3 -maxdepth 3 -type f \\")
    add("            ! -name SHA256SUMS.txt ! -name RELEASE_NOTES.md ! -name '*.iss' | sort)")
    flags = ["--verify-tag", '--title "$APP_TITLE $GITHUB_REF_NAME"']
    if opts.draft:
        flags.append("--draft")
    if opts.prerelease:
        flags.append("--prerelease")
    add('          gh release create "$GITHUB_REF_NAME" --repo "$GITHUB_REPOSITORY" \\')
    add("            " + " ".join(flags) + " \\")
    add('            ${notes:+--notes-file "$notes"} SHA256SUMS.txt $files')
    return lines


# ── Files ─────────────────────────────────────────────────────────────────


def workflow_path(root: str) -> str:
    return os.path.join(os.path.abspath(root), *WORKFLOW_RELATIVE.split("/"))


def write_workflow(text: str, path: str) -> str:
    """Write ``path`` (creating ``.github/workflows``). The caller asked first."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path


def referenced_secrets(text: str) -> List[str]:
    """Every ``${{ secrets.NAME }}`` in ``text``, in order, without repeats."""
    seen: List[str] = []
    for match in _SECRET_REF.finditer(text):
        if match.group(1) not in seen:
            seen.append(match.group(1))
    return seen


def formats_by_runner(opts: CiOptions) -> Dict[str, List[str]]:
    """Which of the project's package formats each runner builds."""
    platforms = {"windows-latest": "win32", "macos-latest": "darwin", "ubuntu-latest": "linux"}
    return {runner: [f for f in opts.formats if is_supported(f, platforms[runner])]
            for runner, _label in RUNNERS}


def host_platform() -> str:  # pragma: no cover - trivial
    return sys.platform
