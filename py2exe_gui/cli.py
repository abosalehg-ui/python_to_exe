"""The command line: ``py2exe-gui <command>``, driven by the project file.

``py2exe-gui`` with no arguments opens the window; with a command it runs
headless and never imports PyQt5, so it works on a CI runner with no display
and no Qt installed.

The consent rules of the GUI carry over unchanged: nothing reaches the network
or installs anything without a yes — typed at the prompt, or given up front
with ``--yes``. In a non-interactive session without ``--yes`` such a step is
refused with a message, never performed silently. The same goes for a project
file whose settings would make the build run its code (``--runtime-hook``,
``--upx-dir``, an update key that is not yours).
"""

import argparse
import getpass
import json
import os
import subprocess
import sys
from typing import Callable, List, Optional

EXIT_OK = 0
EXIT_FAILED = 1  # doctor errors, failed build, failed release step
EXIT_USAGE = 2  # bad arguments (argparse uses 2 as well)
EXIT_PROJECT = 3  # project file missing, invalid or refused
EXIT_CONSENT = 4  # a step needed a yes it did not get
EXIT_TOOL = 5  # a required tool is missing (PyInstaller, the environment...)
EXIT_INTERRUPTED = 130

COMMANDS = ("init", "doctor", "build", "size", "env", "release")
SIGN_PASSWORD_ENV = "P2E_SIGN_PASSWORD"
LANG_ENV = "P2E_LANG"

#: Where isolated environments and the update-signing key live. None means
#: the per-user defaults (``paths``); tests point them at a temporary folder.
ENVS_ROOT: Optional[str] = None
SIGNING_KEY_FILE: Optional[str] = None

#: Tests only: lets ``release`` talk to a local fake API over http. Not
#: reachable from an argument, an environment variable or a project file.
ALLOW_INSECURE_LOCALHOST = False


class CliExit(Exception):
    def __init__(self, code: int, message: str = ""):
        super().__init__(message)
        self.code = code
        self.message = message


class Console:
    """Where output goes and how questions are asked (replaceable in tests)."""

    def __init__(self, yes: bool = False, interactive: Optional[bool] = None,
                 ask: Callable[[str], str] = input, out=None, err=None,
                 secret: Callable[[str], str] = getpass.getpass):
        self.yes = yes
        self.interactive = sys.stdin.isatty() if interactive is None else interactive
        self._ask = ask
        self._secret = secret
        self.out = out or sys.stdout
        self.err = err or sys.stderr

    def print(self, text: str = "") -> None:
        print(text, file=self.out, flush=True)

    def error(self, text: str) -> None:
        print(text, file=self.err, flush=True)

    def confirm(self, question: str) -> bool:
        """True to go ahead. Raises ``CliExit(EXIT_CONSENT)`` when nobody can answer."""
        from py2exe_gui.strings import S

        self.print(question)
        if self.yes:
            self.print(S.CLI_CONSENT_GIVEN)
            return True
        if not self.interactive:
            raise CliExit(EXIT_CONSENT, S.CLI_CONSENT_NEEDED)
        answer = self._ask(S.CLI_CONSENT_PROMPT).strip().lower()
        return answer in ("y", "yes", "ن", "نعم")

    def password(self, prompt: str) -> str:
        if not self.interactive:
            return ""
        return self._secret(prompt)


# ── Language ──────────────────────────────────────────────────────────────


def _requested_language(argv: List[str]) -> str:
    for index, arg in enumerate(argv):
        if arg == "--lang" and index + 1 < len(argv):
            return argv[index + 1]
        if arg.startswith("--lang="):
            return arg.split("=", 1)[1]
    if os.environ.get(LANG_ENV):
        return os.environ[LANG_ENV]
    try:
        from py2exe_gui.constants import SETTINGS_FILE

        with open(SETTINGS_FILE, encoding="utf-8") as f:
            saved = json.load(f).get("locale", "")
        if saved:
            return saved
    except (OSError, ValueError, AttributeError):
        pass
    # Terminals and CI logs read left to right; the GUI keeps Arabic first.
    return "en"


# ── Parser ────────────────────────────────────────────────────────────────


def engine_choices() -> List[str]:
    from py2exe_gui.core.engines import engine_names

    return engine_names()


def build_parser() -> argparse.ArgumentParser:
    from py2exe_gui.constants import APP_VERSION
    from py2exe_gui.strings import S

    parser = argparse.ArgumentParser(
        prog="py2exe-gui", description=S.CLI_DESCRIPTION, epilog=S.CLI_EXIT_CODES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"py2exe-gui {APP_VERSION}")
    parser.add_argument("--lang", choices=("ar", "en"), help=S.CLI_HELP_LANG)
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    def command(name: str, help_text: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_text, description=help_text, epilog=S.CLI_EXIT_CODES,
                           formatter_class=argparse.RawDescriptionHelpFormatter)
        p.add_argument("--project", default="p2e.toml", metavar="PATH", help=S.CLI_HELP_PROJECT)
        return p

    p = command("init", S.CLI_HELP_INIT)
    p.add_argument("script", help=S.CLI_HELP_SCRIPT)
    p.add_argument("--name", default="", help=S.CLI_HELP_NAME)
    p.add_argument("--set-version", dest="set_version", default="", metavar="X.Y.Z",
                   help=S.CLI_HELP_SET_VERSION)
    p.add_argument("--force", action="store_true", help=S.CLI_HELP_FORCE)

    p = command("doctor", S.CLI_HELP_DOCTOR)
    p.add_argument("--json", action="store_true", help=S.CLI_HELP_JSON)

    p = command("build", S.CLI_HELP_BUILD)
    p.add_argument("--strict", action="store_true", help=S.CLI_HELP_STRICT)
    p.add_argument("--yes", "-y", action="store_true", help=S.CLI_HELP_YES)
    p.add_argument("--engine", choices=engine_choices(), help=S.CLI_HELP_ENGINE)
    p.add_argument("--allow-downloads", dest="allow_downloads", action="store_true",
                   help=S.CLI_HELP_ALLOW_DOWNLOADS)

    p = command("size", S.CLI_HELP_SIZE)
    p.add_argument("--json", action="store_true", help=S.CLI_HELP_JSON)

    p = command("env", S.CLI_HELP_ENV)
    p.add_argument("action", choices=("create", "lock", "delete"))
    p.add_argument("--recreate", action="store_true", help=S.CLI_HELP_RECREATE)
    p.add_argument("--base-python", default="", metavar="PATH", help=S.CLI_HELP_BASE_PYTHON)
    p.add_argument("--yes", "-y", action="store_true", help=S.CLI_HELP_YES)

    p = command("release", S.CLI_HELP_RELEASE)
    group = p.add_mutually_exclusive_group()
    group.add_argument("--set-version", dest="set_version", default="", metavar="X.Y.Z",
                       help=S.CLI_HELP_RELEASE_VERSION)
    group.add_argument("--bump", choices=("major", "minor", "patch"), help=S.CLI_HELP_BUMP)
    p.add_argument("--notes", default="", metavar="FILE", help=S.CLI_HELP_NOTES)
    p.add_argument("--dry-run", action="store_true", help=S.CLI_HELP_DRY_RUN)
    p.add_argument("--allow-doctor-errors", action="store_true",
                   help=S.CLI_HELP_ALLOW_DOCTOR_ERRORS)
    p.add_argument("--no-tag", action="store_true", help=S.CLI_HELP_NO_TAG)
    p.add_argument("--push-tag", action="store_true", help=S.CLI_HELP_PUSH_TAG)
    p.add_argument("--no-publish", action="store_true", help=S.CLI_HELP_NO_PUBLISH)
    p.add_argument("--api-url", default="https://api.github.com", metavar="URL",
                   help=S.CLI_HELP_API_URL)
    p.add_argument("--yes", "-y", action="store_true", help=S.CLI_HELP_YES)
    return parser


# ── Shared helpers ────────────────────────────────────────────────────────


def _load(args, console: Console):
    from py2exe_gui.core.project_file import ProjectFileError, load_project
    from py2exe_gui.strings import S
    from py2exe_gui.texts import project_error_text

    path = os.path.abspath(args.project)
    if not os.path.isfile(path):
        raise CliExit(EXIT_PROJECT, S.CLI_NO_PROJECT.format(path=path))
    try:
        loaded = load_project(path)
    except ProjectFileError as e:
        raise CliExit(EXIT_PROJECT, S.CLI_PROJECT_INVALID.format(
            path=path, error=project_error_text(e))) from None
    for warning in loaded.warnings:
        console.error(S.CLI_PROJECT_WARNING.format(warning=warning))
    return loaded


def _review_untrusted(project, console: Console) -> None:
    """The dangerous-settings confirmation, as for a shared JSON file."""
    from py2exe_gui.core.project_file import untrusted_flags
    from py2exe_gui.core.runtime_kit import untrusted_risks
    from py2exe_gui.core.update_signing import read_public_key
    from py2exe_gui.strings import S

    lines = []
    flags = untrusted_flags(project.build)
    if flags:
        lines.append(S.MSG_DANGEROUS_ARGS_CONFIRM.format(
            flags="\n".join(f"  • {f}" for f in flags),
            args=project.build.extra_args or project.build.upx_dir,
        ))
    risks = untrusted_risks(project.build.runtime_kit, read_public_key(_signing_key_path()))
    for risk in risks:
        lines.append(getattr(S, f"KIT_RISK_{risk.code.upper()}").format(**risk.params))
    if not lines:
        return
    if not console.confirm("\n\n".join(lines)):
        raise CliExit(EXIT_CONSENT, S.CLI_DECLINED)


def _envs_root() -> str:
    from py2exe_gui.paths import envs_dir

    return ENVS_ROOT or envs_dir()


def _signing_key_path() -> str:
    from py2exe_gui.paths import signing_key_path

    return SIGNING_KEY_FILE or signing_key_path()


def _env_dir(project) -> str:
    from py2exe_gui.core.venv_manager import env_dir_for

    return env_dir_for(project.build.source, _envs_root())


def _build_python(project) -> str:
    """The interpreter that builds this project ('' = isolated env missing)."""
    from py2exe_gui.core.venv_manager import env_exists, env_python

    if not project.build.isolated_env:
        return sys.executable
    env_dir = _env_dir(project)
    return env_python(env_dir) if env_exists(env_dir) else ""


def _doctor(project, python: str):
    from py2exe_gui.core.knowledge import default_is_installed
    from py2exe_gui.core.project_doctor import examine
    from py2exe_gui.core.venv_manager import InstalledChecker

    checker = default_is_installed if python in ("", sys.executable) else InstalledChecker(python)
    return examine(project.build.source, project.build, is_installed=checker,
                   extra_features=project.features_used())


def _print_findings(report, console: Console) -> None:
    from py2exe_gui.strings import S
    from py2exe_gui.ui.finding_text import SEVERITY_ICONS, finding_title

    console.print(S.CLI_DOCTOR_SCORE.format(score=report.score, errors=report.count("error"),
                                            warnings=report.count("warning")))
    for finding in report.findings:
        icon = SEVERITY_ICONS.get(finding.severity, "•")
        console.print(f"  {icon} [{finding.code}] {finding_title(finding)}")


def _run_streaming(command: List[str], console: Console, cwd: str = "") -> int:
    from py2exe_gui.core.build_runner import stream_command

    return stream_command(command, cwd, console.print)


def _ensure_engine(engine, python: str, console: Console) -> None:
    """The build engine is installed in ``python``, or installed with consent."""
    from py2exe_gui.strings import S

    if engine.name == "pyinstaller":
        _ensure_pyinstaller(python, console)
        return
    if engine.is_available(python):
        return
    command = [python, "-m", "pip", "install", *engine.requirements()]
    if not console.confirm(S.MSG_INSTALL_ENGINE_CONFIRM.format(engine=engine.display_name,
                                                               cmd=quote_cmd(command))):
        raise CliExit(EXIT_CONSENT, S.LOG_INSTALL_ENGINE_DECLINED.format(
            engine=engine.display_name))
    if _run_streaming(command, console) != 0:
        raise CliExit(EXIT_TOOL, S.ERR_INSTALL_ENGINE_FAIL.format(engine=engine.display_name,
                                                                   error="pip"))


def quote_cmd(command: List[str]) -> str:
    from py2exe_gui.core.venv_manager import quote_command

    return quote_command(command)


def _ensure_pyinstaller(python: str, console: Console) -> None:
    from py2exe_gui.constants import PYINSTALLER_REQUIREMENT
    from py2exe_gui.strings import S

    try:
        subprocess.run([python, "-m", "PyInstaller", "--version"], capture_output=True,
                       check=True, timeout=120)
        return
    except (OSError, subprocess.SubprocessError):
        pass
    command = [python, "-m", "pip", "install", PYINSTALLER_REQUIREMENT]
    if not console.confirm(S.MSG_INSTALL_PYINSTALLER_CONFIRM.format(cmd=" ".join(command))):
        raise CliExit(EXIT_CONSENT, S.LOG_INSTALL_PYINSTALLER_DECLINED)
    if _run_streaming(command, console) != 0:
        raise CliExit(EXIT_TOOL, S.ERR_INSTALL_PYINSTALLER_FAIL.format(error="pip"))


# ── Commands ──────────────────────────────────────────────────────────────


def cmd_init(args, console: Console) -> int:
    from py2exe_gui.core.project_file import new_project_for_script, save_project
    from py2exe_gui.core.release.git import remote_slug
    from py2exe_gui.core.release.versioning import is_semver
    from py2exe_gui.strings import S

    script = os.path.abspath(args.script)
    if not os.path.isfile(script) or not script.lower().endswith((".py", ".pyw")):
        raise CliExit(EXIT_USAGE, S.CLI_INIT_NO_SCRIPT.format(path=script))
    if args.set_version and not is_semver(args.set_version):
        raise CliExit(EXIT_USAGE, S.CLI_BAD_VERSION.format(version=args.set_version))
    target = os.path.abspath(args.project)
    if os.path.exists(target) and not args.force:
        raise CliExit(EXIT_PROJECT, S.CLI_INIT_EXISTS.format(path=target))
    project = new_project_for_script(script, version=args.set_version)
    if args.name:
        project.name = args.name
    project.release.repository = remote_slug(os.path.dirname(target))
    save_project(project, target)
    console.print(S.CLI_INIT_DONE.format(path=target, name=project.display_name(),
                                         version=project.version))
    return EXIT_OK


def cmd_doctor(args, console: Console) -> int:
    from dataclasses import asdict

    from py2exe_gui.core.release.versioning import version_mismatches
    from py2exe_gui.strings import S
    from py2exe_gui.ui.finding_text import finding_title

    loaded = _load(args, console)
    project = loaded.project
    python = _build_python(project)
    report = _doctor(project, python)
    mismatches = version_mismatches(project)
    if args.json:
        payload = {
            "project": loaded.path,
            "source": project.build.source,
            "score": report.score,
            "errors": report.count("error"),
            "warnings": report.count("warning"),
            "findings": [dict(code=f.code, severity=f.severity, origin=f.origin,
                              title=finding_title(f), params=f.params,
                              fixes=[asdict(x) for x in f.fixes]) for f in report.findings],
            "version_mismatches": [asdict(m) for m in mismatches],
        }
        console.print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if project.build.isolated_env and not python:
            console.print(S.CLI_ENV_MISSING_NOTE)
        _print_findings(report, console)
        for change in mismatches:
            console.print(S.CLI_VERSION_MISMATCH.format(field=change.field, value=change.old,
                                                        expected=change.new))
    return EXIT_FAILED if report.count("error") else EXIT_OK


def cmd_build(args, console: Console) -> int:
    from py2exe_gui.core.build_runner import prepare_build, run_build
    from py2exe_gui.core.size_analyzer import format_size, output_path_for, path_size
    from py2exe_gui.strings import S
    from py2exe_gui.texts import is_rtl, runtime_texts
    from py2exe_gui.ui.finding_text import finding_title

    loaded = _load(args, console)
    project = loaded.project
    if getattr(args, "engine", None):
        project.build.engine = args.engine
    _review_untrusted(project, console)
    python = _build_python(project)
    if not python:
        console.print(S.CLI_ENV_NEEDED)
        _create_env(project, console, base_python="", recreate=False)
        python = _build_python(project)

    console.print(S.CLI_STAGE_MARKER.format(stage=S.CLI_STAGE_DOCTOR, percent=0))
    report = _doctor(project, python)
    _print_findings(report, console)
    if report.count("error") and args.strict:
        raise CliExit(EXIT_FAILED, S.CLI_STRICT_FAILED)

    from py2exe_gui.core.diagnostics import diagnose_output
    from py2exe_gui.core.engines import engine_for

    engine = engine_for(project.build)
    _ensure_engine(engine, python, console)
    allow_downloads = bool(getattr(args, "allow_downloads", False))
    prepared = prepare_build(project, python, runtime_texts(), is_rtl(),
                             allow_downloads=allow_downloads)
    if prepared.kit_errors:
        problems = "\n".join(f"• {finding_title(f)}" for f in prepared.kit_errors)
        raise CliExit(EXIT_FAILED, S.MSG_KIT_INVALID_FMT.format(problems=problems))
    if prepared.error:
        raise CliExit(EXIT_FAILED, prepared.error)
    if python != sys.executable:
        console.print(S.LOG_ENV_PYTHON.format(python=python))
    console.print(S.CONV_COMMAND.format(cmd=" ".join(prepared.command)).strip())

    def on_stage(stage: str, percent: int) -> None:
        label = getattr(S, f"STAGE_{stage.upper()}", stage)
        console.print(S.CLI_STAGE_MARKER.format(stage=label, percent=percent))

    if engine.name != "pyinstaller":
        console.print(S.LOG_ENGINE_BUILD.format(engine=engine.display_name))
    lines: List[str] = []

    def on_line(line: str) -> None:
        lines.append(line)
        console.print(line)

    outcome = run_build(prepared, on_line, on_stage)
    if not outcome.ok and not allow_downloads:
        # Nuitka asked to download a tool and got "no" (stdin is closed):
        # ask the person, and build again only if they say yes.
        declined = [f for f in diagnose_output("\n".join(lines), origin="build",
                                                engine=engine.name)
                    if f.code == "nuitka_download_declined"]
        if declined and console.confirm(S.CLI_DOWNLOAD_CONFIRM.format(
                tool=declined[0].params.get("tool") or "?")):
            console.print(S.LOG_NUITKA_DOWNLOAD_ALLOWED)
            prepared = prepare_build(project, python, runtime_texts(), is_rtl(),
                                     allow_downloads=True)
            outcome = run_build(prepared, on_line, on_stage)
    if not outcome.ok:
        console.print(S.CLI_STAGE_MARKER.format(stage=S.PROGRESS_FAILED, percent=100))
        raise CliExit(EXIT_FAILED, S.CONV_FAILED_MSG if not outcome.error else outcome.error)
    output = output_path_for(project.build)
    console.print(S.CLI_STAGE_MARKER.format(stage=S.CONV_SUCCESS, percent=100))
    if output:
        console.print(S.CLI_BUILD_OUTPUT.format(path=output, size=format_size(path_size(output))))
    return EXIT_OK


def cmd_size(args, console: Console) -> int:
    from py2exe_gui.core.size_analyzer import analyze, format_size, group_label_key
    from py2exe_gui.strings import S

    loaded = _load(args, console)
    report = analyze(loaded.project.build)
    if not report.ok:
        raise CliExit(EXIT_FAILED, S.CLI_SIZE_NO_BUILD)
    if args.json:
        console.print(json.dumps({
            "output": report.output_path,
            "output_bytes": report.output_bytes,
            "content_bytes": report.content_bytes,
            "groups": dict(report.ranked()),
            "largest_files": [{"name": n, "bytes": s} for n, s in report.largest_files],
        }, ensure_ascii=False, indent=2))
        return EXIT_OK
    console.print(S.CLI_SIZE_TOTAL.format(path=report.output_path,
                                          size=format_size(report.output_bytes)))
    for name, size in report.ranked(15):
        label = getattr(S, group_label_key(name), name) if group_label_key(name) else name
        share = 100.0 * size / report.content_bytes if report.content_bytes else 0.0
        console.print(f"  {format_size(size):>10}  {share:5.1f}%  {label}")
    return EXIT_OK


def _create_env(project, console: Console, base_python: str, recreate: bool) -> None:
    from datetime import datetime

    from py2exe_gui.constants import PYINSTALLER_REQUIREMENT
    from py2exe_gui.core.venv_manager import (
        delete_env,
        env_exists,
        find_uv,
        folder_size,
        plan_environment,
        quote_command,
        single_install_command,
        write_metadata,
    )
    from py2exe_gui.strings import S

    root = _envs_root()
    base = base_python or sys.executable
    if not os.path.isfile(base):
        raise CliExit(EXIT_TOOL, S.ERR_ENV_PYTHON_MISSING.format(path=base))
    from py2exe_gui.core.engines import engine_for

    tools = engine_for(project.build).requirements() or PYINSTALLER_REQUIREMENT
    plan = plan_environment(project.build.source, root, base, tools,
                            uv=find_uv(), recreate=recreate)
    commands = "\n\n".join(quote_command(c) for c in plan.all_commands())
    if not console.confirm(S.MSG_ENV_CONFIRM.format(commands=commands)):
        raise CliExit(EXIT_CONSENT, S.CLI_DECLINED)
    if recreate and env_exists(plan.env_dir):
        delete_env(plan.env_dir, root)
    os.makedirs(root, exist_ok=True)
    for command in plan.setup:
        console.print(S.LOG_ENV_STEP.format(cmd=quote_command(command)))
        if _run_streaming(command, console) != 0:
            raise CliExit(EXIT_FAILED, S.LOG_ENV_FAILED.format(error=command[0]))
    failed = []
    if plan.install:
        console.print(S.LOG_ENV_STEP.format(cmd=quote_command(plan.install)))
        if _run_streaming(plan.install, console) != 0:
            requirements = plan.requirements
            if requirements is None or requirements.origin != "scan":
                raise CliExit(EXIT_FAILED, S.LOG_ENV_FAILED.format(error="pip"))
            console.print(S.LOG_ENV_RETRY_SINGLE)
            for name in requirements.args:
                if _run_streaming(single_install_command(plan, name), console) != 0:
                    failed.append(name)
                    console.print(S.LOG_ENV_PACKAGE_FAILED.format(name=name))
    requirements = plan.requirements
    write_metadata(plan.env_dir, {
        "created": datetime.now().isoformat(timespec="seconds"),
        "base_python": base, "origin": requirements.origin if requirements else "",
        "requirements": list(requirements.args) if requirements else [],
        "failed": failed, "uv": bool(plan.uv), "size_bytes": folder_size(plan.env_dir),
    })
    if failed:
        console.print(S.LOG_ENV_DONE_PARTIAL.format(names=", ".join(failed)))
    else:
        console.print(S.LOG_ENV_DONE)


def cmd_env(args, console: Console) -> int:
    from py2exe_gui.core.size_analyzer import format_size
    from py2exe_gui.core.venv_manager import (
        delete_env,
        env_exists,
        env_python,
        env_status,
        find_uv,
        format_lock,
        freeze_command,
        lock_file_path,
    )
    from py2exe_gui.strings import S

    loaded = _load(args, console)
    project = loaded.project
    env_dir = _env_dir(project)
    if args.action == "create":
        _review_untrusted(project, console)
        _create_env(project, console, args.base_python, args.recreate)
        return EXIT_OK
    if not env_exists(env_dir):
        raise CliExit(EXIT_FAILED, S.CLI_ENV_NONE.format(path=env_dir))
    if args.action == "lock":
        result = subprocess.run(freeze_command(env_python(env_dir), find_uv()),
                                capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise CliExit(EXIT_FAILED, S.LOG_ENV_LOCK_FAILED.format(
                error=(result.stderr or "").strip()[:300]))
        path = lock_file_path(project.build.source)
        with open(path, "w", encoding="utf-8") as f:
            f.write(format_lock(result.stdout))
        console.print(S.LOG_ENV_LOCK_SAVED.format(path=path))
        return EXIT_OK
    status = env_status(env_dir)
    if not console.confirm(S.MSG_ENV_DELETE_CONFIRM.format(size=format_size(status.size_bytes))):
        raise CliExit(EXIT_CONSENT, S.CLI_DECLINED)
    if not delete_env(env_dir, _envs_root()):
        raise CliExit(EXIT_FAILED, S.CLI_ENV_NONE.format(path=env_dir))
    console.print(S.LOG_ENV_DELETED)
    return EXIT_OK


def _print_plan(results, console: Console) -> None:
    from py2exe_gui.core.release.pipeline import confirmation
    from py2exe_gui.strings import S
    from py2exe_gui.texts import step_line

    for result in results:
        console.print(step_line(result))
    summary = confirmation(results)
    sections = (
        (S.RELEASE_CONFIRM_CREATED, summary.created),
        (S.RELEASE_CONFIRM_COMMANDS, summary.commands),
        (S.RELEASE_CONFIRM_COMMITS, summary.commits),
        (S.RELEASE_CONFIRM_TAGS, summary.tags),
        (S.RELEASE_CONFIRM_PUSHES, summary.pushes),
        (S.RELEASE_CONFIRM_RELEASES, summary.releases),
        (S.RELEASE_CONFIRM_UPLOADS, summary.uploads),
    )
    for title, items in sections:
        if items:
            console.print("")
            console.print(title)
            for item in items:
                console.print(f"  • {item}")


def cmd_release(args, console: Console) -> int:
    from py2exe_gui.core.release.pipeline import (
        ReleaseContext,
        ReleaseOptions,
        has_blocking_problems,
        run_release,
    )
    from py2exe_gui.core.release.versioning import bump, is_semver
    from py2exe_gui.strings import S
    from py2exe_gui.texts import is_rtl, notes_titles, runtime_texts, step_line

    loaded = _load(args, console)
    project = loaded.project
    if args.bump:
        if not is_semver(project.version):
            raise CliExit(EXIT_USAGE, S.CLI_BAD_VERSION.format(version=project.version or "—"))
        version = bump(project.version, args.bump)
    else:
        version = args.set_version or project.version
    if not is_semver(version):
        raise CliExit(EXIT_USAGE, S.CLI_BAD_VERSION.format(version=version or "—"))
    notes = ""
    if args.notes:
        try:
            with open(args.notes, encoding="utf-8") as f:
                notes = f.read()
        except (OSError, UnicodeDecodeError) as e:
            raise CliExit(EXIT_USAGE, S.CLI_NOTES_UNREADABLE.format(error=str(e))) from None
    _review_untrusted(project, console)

    python = _build_python(project)
    if not python:
        raise CliExit(EXIT_TOOL, S.CLI_ENV_NEEDED_RELEASE)
    password = os.environ.get(SIGN_PASSWORD_ENV, "")
    signing = project.signing
    if (signing.enabled and not signing.use_cert_store and not password
            and not args.dry_run and sys.platform == "win32"):
        password = console.password(S.CLI_SIGN_PASSWORD_PROMPT)

    def options(dry_run: bool) -> ReleaseOptions:
        return ReleaseOptions(
            version=version, notes=notes, dry_run=dry_run,
            allow_doctor_errors=args.allow_doctor_errors, create_tag=not args.no_tag,
            push_tag=args.push_tag, publish=not args.no_publish, sign_password=password,
            signing_key_path=_signing_key_path(), api_url=args.api_url,
            allow_insecure_localhost=ALLOW_INSECURE_LOCALHOST, notes_titles=notes_titles(),
        )

    def context(dry_run: bool) -> ReleaseContext:
        from py2exe_gui.core.project_file import load_project

        fresh = load_project(loaded.path).project
        return ReleaseContext(fresh, options(dry_run), project_path=loaded.path, python=python,
                              log=console.print, texts=runtime_texts(), rtl=is_rtl())

    console.print(S.CLI_RELEASE_PLAN.format(version=version))
    plan = run_release(context(dry_run=True))
    _print_plan(plan, console)
    if has_blocking_problems(plan):
        raise CliExit(EXIT_FAILED, S.CLI_RELEASE_BLOCKED)
    if args.dry_run:
        console.print(S.CLI_RELEASE_DRY_RUN_DONE)
        return EXIT_OK
    if not console.confirm(S.CLI_RELEASE_CONFIRM.format(version=version)):
        raise CliExit(EXIT_CONSENT, S.CLI_DECLINED)

    def on_step(result) -> None:
        if result.status != "running":
            console.print(step_line(result))

    ctx = context(dry_run=False)
    results = run_release(ctx, on_step)
    if has_blocking_problems(results):
        raise CliExit(EXIT_FAILED, S.CLI_RELEASE_FAILED)
    console.print(S.CLI_RELEASE_DONE.format(version=version, path=ctx.out_dir,
                                            url=ctx.release_url or "—"))
    return EXIT_OK


HANDLERS = {
    "init": cmd_init, "doctor": cmd_doctor, "build": cmd_build, "size": cmd_size,
    "env": cmd_env, "release": cmd_release,
}


def main(argv: Optional[List[str]] = None, console: Optional[Console] = None) -> int:
    from py2exe_gui.strings import set_locale

    argv = list(sys.argv[1:] if argv is None else argv)
    set_locale(_requested_language(argv))
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:  # --help, --version, or a usage error
        return int(e.code or 0)
    if not args.command:
        parser.print_help()
        return EXIT_USAGE
    console = console or Console(yes=getattr(args, "yes", False))
    if getattr(args, "yes", False):
        console.yes = True
    try:
        return HANDLERS[args.command](args, console)
    except CliExit as e:
        if e.message:
            console.error(e.message)
        return e.code
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED


def is_cli_invocation(argv: List[str]) -> bool:
    """True when ``py2exe-gui`` was given a command (or --help/--version)."""
    if not argv:
        return False
    first = argv[0]
    return first in COMMANDS or first in ("-h", "--help", "--version") or \
        first.startswith("--lang")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
