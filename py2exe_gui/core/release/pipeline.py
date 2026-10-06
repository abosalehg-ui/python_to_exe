"""One release, step by step: version → notes → doctor → build → sign →
installer → portable ZIP → checksums → update manifest → git tag → GitHub
release → winget manifest.

Every step is a function of the ``ReleaseContext`` that returns a
``StepResult``: a status, a reason *code* (the UI translates it) and the
``Action`` list of what it did — or, in a dry run, what it would do. A dry run
has no side effects at all: it reads the project, git's log and the doctor's
findings, and predicts the file names; it writes nothing, runs no build,
creates no tag and contacts no server. The same action lists feed the final
confirmation, so the user sees exactly what will be created, uploaded and
tagged before anything is.

Steps can run again: the version bump is a no-op at the same version, a tag
already on HEAD is accepted, an existing release and already-uploaded assets
are reused.
"""

import copy
import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from py2exe_gui.core.build_runner import BuildOutcome, prepare_build, run_build
from py2exe_gui.core.builder import build_pyinstaller_command
from py2exe_gui.core.code_signer import build_signtool_command, redact_password
from py2exe_gui.core.diagnostics import build_name
from py2exe_gui.core.installer import (
    build_iscc_command,
    find_iscc,
    generate_iss_script,
    installer_output_path,
)
from py2exe_gui.core.release import artifacts, git, winget
from py2exe_gui.core.release.changelog import draft_notes
from py2exe_gui.core.release.credentials import Token, find_token, redact
from py2exe_gui.core.release.github import API_URL, GitHubClient, GitHubError, publish_release
from py2exe_gui.core.release.versioning import apply_version, normalize, parse_semver, tag_for
from py2exe_gui.core.runtime_kit import preview_options

STEPS = (
    "version", "notes", "doctor", "build", "sign", "installer", "portable_zip",
    "checksums", "update_manifest", "tag", "publish", "winget",
)

PENDING, RUNNING, PLANNED, DONE, SKIPPED, FAILED = (
    "pending", "running", "planned", "done", "skipped", "failed",
)

#: Action kinds, as listed in the confirmation.
WRITE, RUN, COMMIT, TAG, PUSH, CREATE_RELEASE, UPLOAD = (
    "write", "run", "commit", "tag", "push", "create_release", "upload",
)


@dataclass(frozen=True)
class Action:
    kind: str
    target: str


@dataclass
class StepResult:
    key: str
    status: str
    reason: str = ""
    params: Dict[str, str] = field(default_factory=dict)
    actions: List[Action] = field(default_factory=list)


@dataclass
class ReleaseOptions:
    version: str
    notes: str = ""
    dry_run: bool = False
    allow_doctor_errors: bool = False
    #: Commit the project file the version step changed, before tagging.
    commit_version: bool = True
    create_tag: bool = True
    push_tag: bool = False
    publish: bool = True
    sign_password: str = field(default="", repr=False)
    signtool_path: str = "signtool"
    iscc_path: str = ""
    #: The Runtime Kit's private update key (per-user config folder).
    signing_key_path: str = ""
    api_url: str = API_URL
    #: Tests only (a local fake API). Never set from a project file or the UI.
    allow_insecure_localhost: bool = False
    notes_titles: Optional[Dict[str, str]] = None
    platform: str = sys.platform


class ReleaseContext:
    """The state one release run shares between its steps."""

    def __init__(self, project, options: ReleaseOptions, project_path: str = "",
                 python: str = "", log: Callable[[str], None] = lambda _m: None,
                 runner=None, build=None, doctor=None, github_factory=None,
                 token_provider: Optional[Callable[[], Token]] = None,
                 texts: Optional[Dict[str, str]] = None, rtl: bool = False):
        self.project = project
        self.options = options
        self.project_path = os.path.abspath(project_path) if project_path else ""
        self.project_dir = (os.path.dirname(self.project_path) if self.project_path
                            else os.path.dirname(os.path.abspath(project.build.source or ".")))
        self.python = python or sys.executable
        self._log = log
        self.runner = runner or subprocess.run
        self.build = build or default_build
        self.doctor = doctor or default_doctor
        self.github_factory = github_factory or GitHubClient
        self.token_provider = token_provider or find_token
        self.texts = texts
        self.rtl = rtl
        self.secrets: List[str] = [options.sign_password] if options.sign_password else []

        self.version = normalize(options.version)
        self.tag = tag_for(self.version, project.release.tag_prefix or "v")
        self.notes = options.notes
        self.out_dir = artifacts.release_dir(project.build, self.version)
        self.files: Dict[str, str] = {}
        self.project_changed = False
        self.target_commitish = ""
        self.download_urls: Dict[str, str] = {}
        self.release_url = ""
        self.version_actions: List[Action] = []

    def log(self, message: str) -> None:
        self._log(redact(message, self.secrets))

    @property
    def dry_run(self) -> bool:
        return self.options.dry_run

    @property
    def repository(self) -> str:
        return self.project.release.repository.strip()

    # Predicted names, valid in a dry run too.
    def exe_target(self, built: str = "") -> str:
        # Before the build (a dry run), predict the extension: PyInstaller
        # writes "app.exe" on Windows and plain "app" elsewhere.
        ext = ".exe" if self.options.platform == "win32" else ""
        return os.path.join(self.out_dir, artifacts.exe_asset_name(
            self.project.build, self.version, built, ext))

    def zip_target(self) -> str:
        return os.path.join(self.out_dir, artifacts.zip_asset_name(self.project.build, self.version))

    def installer_config(self):
        inst = copy.deepcopy(self.project.installer)
        inst.app_name = inst.app_name or self.project.display_name() or "app"
        inst.app_version = self.version
        inst.publisher = inst.publisher or self.project.version_info.company_name
        inst.setup_icon_file = inst.setup_icon_file or self.project.build.icon
        inst.output_dir = self.out_dir
        inst.output_base_filename = artifacts.installer_basename(self.project.build, self.version)
        return inst


def _result(key, status, reason="", actions=None, **params) -> StepResult:
    return StepResult(key, status, reason, {k: str(v) for k, v in params.items()}, actions or [])


# ── Defaults for the injectable parts ────────────────────────────────────


def default_build(ctx: ReleaseContext) -> BuildOutcome:
    prepared = prepare_build(ctx.project, ctx.python, ctx.texts, ctx.rtl,
                             platform=ctx.options.platform)
    if prepared.kit_errors:
        codes = ", ".join(f.code for f in prepared.kit_errors)
        return BuildOutcome(False, error=f"Runtime Kit: {codes}")
    if prepared.command:
        ctx.log("$ " + " ".join(prepared.command))
    return run_build(prepared, ctx.log, lambda stage, pct: ctx.log(f"==> [{stage}] {pct}%"))


def default_doctor(ctx: ReleaseContext):
    from py2exe_gui.core.knowledge import default_is_installed
    from py2exe_gui.core.project_doctor import examine
    from py2exe_gui.core.venv_manager import InstalledChecker

    checker = (default_is_installed if ctx.python == sys.executable
               else InstalledChecker(ctx.python))
    return examine(ctx.project.build.source, ctx.project.build, is_installed=checker)


# ── Steps ─────────────────────────────────────────────────────────────────


def step_version(ctx: ReleaseContext) -> StepResult:
    try:
        parse_semver(ctx.version)
    except ValueError:
        return _result("version", FAILED, "version_invalid", version=ctx.version)
    if ctx.project.build.runtime_kit.updater:
        from p2e_runtime.updates import parse_version

        try:
            parse_version(ctx.version)
        except ValueError:
            return _result("version", FAILED, "version_runtime", version=ctx.version)
    target = ctx.project if not ctx.dry_run else copy.deepcopy(ctx.project)
    changes = apply_version(target, ctx.version)
    actions = [Action(WRITE, f"{c.field}: {c.old or '—'} → {c.new}") for c in changes]
    if changes and ctx.project_path:
        actions.append(Action(WRITE, ctx.project_path))
        if not ctx.dry_run:
            from py2exe_gui.core.project_file import save_project

            save_project(ctx.project, ctx.project_path)
            ctx.project_changed = True
    if ctx.dry_run:
        return _result("version", PLANNED, "version_changed" if changes else "version_unchanged",
                       actions, count=len(changes), version=ctx.version)
    return _result("version", DONE, "version_changed" if changes else "version_unchanged",
                   actions, count=len(changes), version=ctx.version)


def step_notes(ctx: ReleaseContext) -> StepResult:
    reason = "notes_given"
    if not ctx.notes.strip():
        try:
            ctx.notes = draft_notes(ctx.project_dir, ctx.project.release.tag_prefix or "v",
                                    ctx.options.notes_titles, ctx.runner)
        except git.GitError:
            ctx.notes = ""
        reason = "notes_generated" if ctx.notes else "notes_no_git"
    target = os.path.join(ctx.out_dir, artifacts.NOTES_NAME)
    actions = [Action(WRITE, target)]
    if ctx.dry_run:
        return _result("notes", PLANNED, reason, actions)
    artifacts.write_notes(ctx.notes, target)
    ctx.files["notes"] = target
    return _result("notes", DONE, reason, actions)


def step_doctor(ctx: ReleaseContext) -> StepResult:
    report = ctx.doctor(ctx)
    errors = [f.code for f in report.findings if f.severity == "error"]
    if errors and not ctx.options.allow_doctor_errors:
        return _result("doctor", FAILED, "doctor_errors", count=len(errors),
                       codes=", ".join(errors))
    status = PLANNED if ctx.dry_run else DONE
    if errors:
        return _result("doctor", status, "doctor_overridden", count=len(errors),
                       codes=", ".join(errors))
    return _result("doctor", status, "doctor_ok", score=report.score)


def step_build(ctx: ReleaseContext) -> StepResult:
    if ctx.dry_run:
        command, error = build_pyinstaller_command(
            ctx.project.build, python_executable=ctx.python, platform=ctx.options.platform,
            extra_options=preview_options(ctx.project.build, ctx.options.platform),
        )
        if error:
            return _result("build", FAILED, "build_failed", error=error)
        return _result("build", PLANNED, "build_ok", [Action(RUN, " ".join(command))])
    outcome = ctx.build(ctx)
    if not outcome.ok:
        return _result("build", FAILED, "build_failed",
                       error=outcome.error or f"exit code {outcome.returncode}")
    built = artifacts.built_output(ctx.project.build)
    if not built:
        return _result("build", FAILED, "build_no_output")
    ctx.files["built"] = built
    return _result("build", DONE, "build_ok", [Action(WRITE, built)])


def _main_exe(ctx: ReleaseContext) -> str:
    built = ctx.files.get("built", "")
    if not built or ctx.project.build.onefile:
        return built
    for ext in (".exe", ""):
        candidate = os.path.join(built, build_name(ctx.project.build) + ext)
        if os.path.isfile(candidate):
            return candidate
    return ""


def step_sign(ctx: ReleaseContext) -> StepResult:
    settings = ctx.project.signing
    if not settings.enabled:
        return _result("sign", SKIPPED, "sign_off")
    if ctx.options.platform != "win32":
        return _result("sign", SKIPPED, "windows_only")
    config = settings.signing_config(ctx.options.sign_password, ctx.options.signtool_path)
    exe = _main_exe(ctx) or ctx.exe_target()
    command, error = build_signtool_command(exe, config)
    if error:
        return _result("sign", FAILED, "sign_failed", error=error)
    shown = " ".join(redact_password(command))
    if ctx.dry_run:
        return _result("sign", PLANNED, "sign_ok", [Action(RUN, shown)])
    ctx.log(shown)
    try:
        result = ctx.runner(command, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as e:
        return _result("sign", FAILED, "sign_failed", error=redact(str(e), ctx.secrets))
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "").strip()[:300]
        return _result("sign", FAILED, "sign_failed", error=redact(message, ctx.secrets))
    return _result("sign", DONE, "sign_ok", [Action(RUN, shown)])


def step_installer(ctx: ReleaseContext) -> StepResult:
    project = ctx.project
    if not (project.installer.enabled and project.release.assets.installer):
        return _result("installer", SKIPPED, "installer_off")
    if ctx.options.platform != "win32":
        return _result("installer", SKIPPED, "windows_only")
    iscc = ctx.options.iscc_path or find_iscc()
    if not iscc:
        return _result("installer", FAILED, "iscc_missing")
    inst = ctx.installer_config()
    target = installer_output_path(inst)
    iss_path = os.path.join(ctx.out_dir, f"{artifacts.safe_name(inst.app_name)}.iss")
    sign_command = None
    if inst.sign_installer and project.signing.enabled:
        config = project.signing.signing_config(ctx.options.sign_password,
                                                ctx.options.signtool_path)
        candidate, error = build_signtool_command("$f", config)
        if not error and candidate:
            sign_command = candidate[:-1]
    command, error = build_iscc_command(iss_path, iscc_path=iscc, sign_command=sign_command)
    if error:
        return _result("installer", FAILED, "installer_failed", error=error)
    actions = [Action(WRITE, iss_path), Action(RUN, " ".join(redact_password(command))),
               Action(WRITE, target)]
    if ctx.dry_run:
        return _result("installer", PLANNED, "installer_ok", actions)
    built = ctx.files.get("built", "")
    exe_name = "" if project.build.onefile else os.path.basename(_main_exe(ctx))
    script = generate_iss_script(inst, built, onefile=project.build.onefile, exe_name=exe_name)
    os.makedirs(ctx.out_dir, exist_ok=True)
    with open(iss_path, "w", encoding="utf-8") as f:
        f.write(script)
    ctx.log(" ".join(redact_password(command)))
    try:
        result = ctx.runner(command, capture_output=True, text=True, timeout=1800,
                            cwd=ctx.out_dir)
    except (OSError, subprocess.SubprocessError) as e:
        return _result("installer", FAILED, "installer_failed", error=redact(str(e), ctx.secrets))
    if result.returncode != 0 or not os.path.isfile(target):
        message = (result.stdout or result.stderr or "").strip()[-300:]
        return _result("installer", FAILED, "installer_failed",
                       error=redact(message, ctx.secrets) or "ISCC")
    ctx.files["installer"] = target
    return _result("installer", DONE, "installer_ok", actions)


def step_portable_zip(ctx: ReleaseContext) -> StepResult:
    if not ctx.project.release.assets.portable_zip:
        return _result("portable_zip", SKIPPED, "zip_off")
    target = ctx.zip_target()
    if ctx.dry_run:
        return _result("portable_zip", PLANNED, "zip_ok", [Action(WRITE, target)])
    artifacts.make_portable_zip(ctx.files["built"], target)
    ctx.files["portable_zip"] = target
    return _result("portable_zip", DONE, "zip_ok", [Action(WRITE, target)])


def _collect_exe(ctx: ReleaseContext) -> None:
    """Copy the (signed) one-file EXE into the release folder, once."""
    if ("exe" in ctx.files or ctx.dry_run or not ctx.project.build.onefile
            or not ctx.project.release.assets.exe or not ctx.files.get("built")):
        return
    ctx.files["exe"] = artifacts.copy_file(ctx.files["built"], ctx.exe_target(ctx.files["built"]))


def _exe_planned(ctx: ReleaseContext) -> bool:
    return ctx.project.build.onefile and ctx.project.release.assets.exe


def _binary_files(ctx: ReleaseContext, results: Dict[str, StepResult]) -> List[str]:
    """The release's binaries — real paths, or predicted ones in a dry run."""
    if not ctx.dry_run:
        return artifacts.existing([ctx.files.get(k) for k in ("exe", "installer",
                                                               "portable_zip")])
    paths = []
    if _exe_planned(ctx):
        paths.append(ctx.exe_target())
    installer = results.get("installer")
    if installer and installer.status == PLANNED:
        paths.append(installer_output_path(ctx.installer_config()))
    if ctx.project.release.assets.portable_zip:
        paths.append(ctx.zip_target())
    return paths


def step_checksums(ctx: ReleaseContext, results: Dict[str, StepResult]) -> StepResult:
    _collect_exe(ctx)
    actions = []
    if _exe_planned(ctx):
        actions.append(Action(WRITE, ctx.files.get("exe") or ctx.exe_target()))
    if not ctx.project.release.assets.checksums:
        return _result("checksums", SKIPPED, "checksums_off", actions)
    target = os.path.join(ctx.out_dir, artifacts.CHECKSUMS_NAME)
    files = _binary_files(ctx, results)
    actions.append(Action(WRITE, target))
    if ctx.dry_run:
        return _result("checksums", PLANNED, "checksums_ok", actions, count=len(files))
    artifacts.write_checksums(files, target)
    ctx.files["checksums"] = target
    return _result("checksums", DONE, "checksums_ok", actions, count=len(files))


def step_update_manifest(ctx: ReleaseContext, results: Dict[str, StepResult]) -> StepResult:
    project = ctx.project
    if not project.build.runtime_kit.updater:
        return _result("update_manifest", SKIPPED, "updater_off")
    if not project.release.assets.update_manifest:
        return _result("update_manifest", SKIPPED, "update_asset_off")
    if not ctx.repository:
        return _result("update_manifest", FAILED, "no_repository")
    # A one-file app replaces itself with the new EXE; a folder app runs the installer.
    if project.build.onefile:
        update_file = ctx.files.get("exe") or (ctx.exe_target() if ctx.dry_run
                                                and _exe_planned(ctx) else "")
    else:
        update_file = ctx.files.get("installer") or (
            installer_output_path(ctx.installer_config())
            if ctx.dry_run and results.get("installer", StepResult("", "")).status == PLANNED
            else "")
    if not update_file:
        return _result("update_manifest", FAILED, "update_needs_file")
    from py2exe_gui.core.update_signing import publish_update, read_key_file

    try:
        key = read_key_file(ctx.options.signing_key_path)
    except (OSError, ValueError):
        return _result("update_manifest", FAILED, "no_signing_key")
    url = artifacts.download_url(ctx.repository, ctx.tag, os.path.basename(update_file))
    manifest = os.path.join(ctx.out_dir, "update.json")
    actions = [Action(WRITE, manifest), Action(WRITE, manifest + ".sig")]
    if ctx.dry_run:
        return _result("update_manifest", PLANNED, "update_ok", actions, url=url)
    try:
        published = publish_update(update_file, ctx.version, url, key, notes=ctx.notes,
                                   app_name=build_name(project.build), output_dir=ctx.out_dir)
    except (OSError, ValueError) as e:
        return _result("update_manifest", FAILED, "update_failed", error=str(e))
    ctx.files["update_json"] = published.manifest_path
    ctx.files["update_sig"] = published.signature_path
    return _result("update_manifest", DONE, "update_ok", actions, url=url)


def step_tag(ctx: ReleaseContext) -> StepResult:
    if not ctx.options.create_tag:
        return _result("tag", SKIPPED, "tag_off")
    cwd = ctx.project_dir
    if not git.is_repo(cwd, ctx.runner):
        return _result("tag", SKIPPED, "not_git")
    try:
        head = git.head_sha(cwd, ctx.runner)
        existing = git.tag_commit(cwd, ctx.tag, ctx.runner)
        commit_project = False
        if ctx.project_path and ctx.options.commit_version:
            rel = os.path.relpath(ctx.project_path, cwd).replace(os.sep, "/")
            # In a dry run the bump has not been written yet: it will be.
            will_change = ctx.dry_run and any(a.target == ctx.project_path
                                              for a in ctx.version_actions)
            commit_project = git.is_tracked(cwd, rel, ctx.runner) and (
                will_change or rel in git.changed_files(cwd, ctx.runner))
    except git.GitError as e:
        return _result("tag", FAILED, "tag_failed", error=str(e))

    if existing and not commit_project:
        if existing == head:
            return _result("tag", DONE if not ctx.dry_run else PLANNED, "tag_exists",
                           commit=head[:10])
        return _result("tag", FAILED, "tag_conflict", tag=ctx.tag, commit=existing[:10])
    if existing:
        return _result("tag", FAILED, "tag_conflict", tag=ctx.tag, commit=existing[:10])

    actions = []
    if commit_project:
        actions.append(Action(COMMIT, ctx.project_path))
    actions.append(Action(TAG, ctx.tag))
    if ctx.options.push_tag:
        actions.append(Action(PUSH, ctx.tag))
    if ctx.dry_run:
        ctx.target_commitish = head
        return _result("tag", PLANNED, "tag_ok", actions, tag=ctx.tag, commit=head[:10])
    try:
        if commit_project:
            git.commit_paths(cwd, [ctx.project_path], f"Release {ctx.tag}", ctx.runner)
        commit = git.create_tag(cwd, ctx.tag, f"Release {ctx.tag}", ctx.runner)
        if ctx.options.push_tag:
            git.push_tag(cwd, ctx.tag, runner=ctx.runner)
    except git.GitError as e:
        return _result("tag", FAILED, "tag_failed", error=str(e))
    ctx.target_commitish = commit
    return _result("tag", DONE, "tag_ok", actions, tag=ctx.tag, commit=commit[:10])


def _upload_files(ctx: ReleaseContext, results: Dict[str, StepResult]) -> List[str]:
    if ctx.dry_run:
        paths = _binary_files(ctx, results)
        for key in ("checksums", "update_manifest"):
            result = results.get(key)
            if result and result.status == PLANNED:
                paths += [a.target for a in result.actions
                          if a.kind == WRITE and a.target.startswith(ctx.out_dir)
                          and a.target not in paths]
        return paths
    keys = ("exe", "installer", "portable_zip", "checksums", "update_json", "update_sig")
    return [ctx.files[k] for k in keys if ctx.files.get(k)]


def step_publish(ctx: ReleaseContext, results: Dict[str, StepResult]) -> StepResult:
    if not ctx.options.publish:
        return _result("publish", SKIPPED, "publish_off")
    if not ctx.repository:
        return _result("publish", FAILED, "no_repository")
    files = _upload_files(ctx, results)
    actions = [Action(CREATE_RELEASE, f"{ctx.repository}@{ctx.tag}")]
    actions += [Action(UPLOAD, os.path.basename(p)) for p in files]
    token = ctx.token_provider()
    if ctx.dry_run:
        reason = "publish_ok" if token else "no_token"
        status = PLANNED if token else FAILED
        return _result("publish", status, reason, actions, repository=ctx.repository)
    if not token:
        return _result("publish", FAILED, "no_token")
    ctx.secrets.append(token.value)
    release = ctx.project.release
    try:
        client = ctx.github_factory(
            token.value, ctx.repository, api_url=ctx.options.api_url,
            allow_insecure_localhost=ctx.options.allow_insecure_localhost,
        )
        published = publish_release(
            client, ctx.tag, f"{ctx.project.display_name() or ctx.tag} {ctx.version}".strip(),
            ctx.notes, files, draft=release.draft, prerelease=release.prerelease,
            target_commitish=ctx.target_commitish, log=ctx.log,
        )
    except (GitHubError, OSError) as e:
        return _result("publish", FAILED, "publish_failed", error=redact(str(e), ctx.secrets))
    ctx.download_urls = dict(published.assets)
    ctx.release_url = published.html_url
    return _result("publish", DONE, "publish_ok", actions, url=published.html_url,
                   repository=ctx.repository)


def step_winget(ctx: ReleaseContext, results: Dict[str, StepResult]) -> StepResult:
    project = ctx.project
    settings = project.release.winget
    if not settings.enabled:
        return _result("winget", SKIPPED, "winget_off")
    if not ctx.repository:
        return _result("winget", FAILED, "no_repository")
    if ctx.dry_run:
        installer = results.get("installer")
        path, kind = winget.choose_installer(
            installer_output_path(ctx.installer_config())
            if installer and installer.status == PLANNED else "",
            ctx.exe_target() if _exe_planned(ctx) else "",
            ctx.zip_target() if project.release.assets.portable_zip else "",
        )
    else:
        path, kind = winget.choose_installer(ctx.files.get("installer", ""),
                                             ctx.files.get("exe", ""),
                                             ctx.files.get("portable_zip", ""))
    if not path:
        return _result("winget", FAILED, "winget_no_file")
    folder = os.path.join(ctx.out_dir, "winget")
    identifier = settings.identifier.strip()
    names = winget.file_names(identifier or "Publisher.App", settings.locale or "en-US")
    actions = [Action(WRITE, os.path.join(folder, n)) for n in names.values()]
    name = os.path.basename(path)
    url = ctx.download_urls.get(name) or artifacts.download_url(ctx.repository, ctx.tag, name)
    sha = artifacts.sha256_of(path) if not ctx.dry_run else "0" * 64
    nested = ""
    if kind == "zip":
        # The file as it is inside the ZIP (see artifacts.make_portable_zip).
        main = _main_exe(ctx)
        inner = os.path.basename(main) if main else build_name(project.build) + ".exe"
        nested = inner if project.build.onefile else f"{build_name(project.build)}/{inner}"
    docs = winget.build_manifests(
        identifier=identifier,
        version=ctx.version,
        publisher=settings.publisher or project.installer.publisher
        or project.version_info.company_name,
        name=project.display_name(),
        license_text=settings.license,
        short_description=settings.short_description or project.version_info.file_description,
        installer_url=url,
        sha256=sha,
        installer_type=kind,
        architecture=winget.architecture_for(project.installer.architecture),
        locale=settings.locale or "en-US",
        publisher_url=project.installer.publisher_url,
        nested_path=nested,
    )
    problems = winget.validate_manifests(docs)
    if problems:
        return _result("winget", FAILED, "winget_invalid", problems="; ".join(problems))
    if ctx.dry_run:
        return _result("winget", PLANNED, "winget_ok", actions, kind=kind)
    for written in winget.write_manifests(docs, folder):
        ctx.files.setdefault("winget", written)
    return _result("winget", DONE, "winget_ok", actions, kind=kind)


_STEP_FUNCS = {
    "version": step_version,
    "notes": step_notes,
    "doctor": step_doctor,
    "build": step_build,
    "sign": step_sign,
    "installer": step_installer,
    "portable_zip": step_portable_zip,
    "checksums": step_checksums,
    "update_manifest": step_update_manifest,
    "tag": step_tag,
    "publish": step_publish,
    "winget": step_winget,
}
_NEEDS_RESULTS = frozenset({"checksums", "update_manifest", "publish", "winget"})


def run_release(ctx: ReleaseContext,
                on_step: Callable[[StepResult], None] = lambda _r: None) -> List[StepResult]:
    """Run every step in order (or plan it, in a dry run).

    A real run stops at the first failure; the steps after it are reported as
    ``pending`` with reason ``not_run``. A dry run never stops: it shows every
    problem at once.
    """
    results: Dict[str, StepResult] = {}
    ordered: List[StepResult] = []
    stopped = False
    for key in STEPS:
        if stopped:
            result = StepResult(key, PENDING, "not_run")
        else:
            on_step(StepResult(key, RUNNING))
            func = _STEP_FUNCS[key]
            try:
                result = func(ctx, results) if key in _NEEDS_RESULTS else func(ctx)
            except Exception as e:  # noqa: BLE001 - one step's bug must not hide the others
                result = _result(key, FAILED, "unexpected", error=redact(
                    f"{type(e).__name__}: {e}", ctx.secrets))
            if key == "version":
                ctx.version_actions = result.actions
            if result.status == FAILED and not ctx.dry_run:
                stopped = True
        results[key] = result
        ordered.append(result)
        on_step(result)
    return ordered


def plan_release(ctx: ReleaseContext) -> List[StepResult]:
    """The dry run of ``ctx``, which must have been created with ``dry_run=True``."""
    if not ctx.dry_run:
        raise ValueError("plan_release needs a context created with dry_run=True")
    return run_release(ctx)


@dataclass
class Confirmation:
    """What a release will do, grouped for the final confirmation."""

    created: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    commits: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    pushes: List[str] = field(default_factory=list)
    releases: List[str] = field(default_factory=list)
    uploads: List[str] = field(default_factory=list)
    problems: List[StepResult] = field(default_factory=list)


def confirmation(results: List[StepResult]) -> Confirmation:
    summary = Confirmation()
    buckets = {WRITE: summary.created, RUN: summary.commands, COMMIT: summary.commits,
               TAG: summary.tags, PUSH: summary.pushes, CREATE_RELEASE: summary.releases,
               UPLOAD: summary.uploads}
    for result in results:
        if result.status == FAILED:
            summary.problems.append(result)
        if result.status not in (PLANNED, DONE):
            continue
        for action in result.actions:
            bucket = buckets[action.kind]
            if action.target not in bucket:
                bucket.append(action.target)
    return summary


def has_blocking_problems(results: List[StepResult]) -> bool:
    return any(r.status == FAILED for r in results)
