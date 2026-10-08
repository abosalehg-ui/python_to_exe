"""Running a build without a window: the command line and the release pipeline.

The GUI streams PyInstaller through a ``QThread``; this is the same sequence
for code that has no event loop — prepare the files a build needs (Version
Info, manifest, Runtime Kit), build the command, stream the output line by
line while ``BuildStageTracker`` follows the phases, then clean up.
"""

import os
import subprocess
import tempfile
from dataclasses import dataclass, field, replace
from typing import Callable, Dict, List, Optional

from py2exe_gui.core.build_stages import BuildStageTracker
from py2exe_gui.core.diagnostics import build_name, build_root
from py2exe_gui.core.engines import engine_for, get_engine
from py2exe_gui.core.fixes import SEVERITY_ERROR, Finding
from py2exe_gui.core.manifest_generator import generate_manifest
from py2exe_gui.core.runtime_kit import write_kit
from py2exe_gui.core.version_info import generate_version_file


@dataclass
class PreparedBuild:
    command: List[str] = field(default_factory=list)
    cwd: str = ""
    #: Temporary files to delete once the build is over.
    temp_files: List[str] = field(default_factory=list)
    #: A user-facing reason the build cannot start ('' when it can).
    error: str = ""
    #: Runtime Kit problems (findings) that stop the build.
    kit_errors: List[Finding] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    #: The engine the command runs (``core/engines``).
    engine: str = "pyinstaller"
    #: The environment to run it in (None: the app's own).
    env: Optional[Dict[str, str]] = None

    def cleanup(self) -> None:
        for path in self.temp_files:
            try:
                os.unlink(path)
            except OSError:
                pass
        self.temp_files = []


@dataclass
class BuildOutcome:
    ok: bool
    returncode: int = -1
    error: str = ""


def _write_temp(prefix: str, suffix: str, content: str) -> str:
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=suffix, text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def prepare_build(project, python: str, texts: Optional[Dict[str, str]] = None,
                  rtl: bool = False, platform: Optional[str] = None,
                  allow_downloads: bool = False) -> PreparedBuild:
    """Everything needed to run the build of ``project`` with ``python``.

    ``allow_downloads`` is the user's explicit consent to let the engine
    download tools (Nuitka's ``--assume-yes-for-downloads``); it is never
    implied, and no settings file can give it.
    """
    prepared = PreparedBuild()
    config = replace(project.build)
    engine = engine_for(config)
    if config.runtime_kit.enabled and not engine.supports("runtime_kit"):
        # The kit's hook needs PyInstaller's --runtime-hook: building without
        # it would ship an EXE whose code may import p2e_runtime and die.
        prepared.kit_errors = [kit_unsupported_finding(engine)]
        return prepared
    native: List[str] = []
    if engine.version_info_mode == "options":
        native += engine.metadata_options(project.version_info, platform)
    elif not project.version_info.is_empty():
        path = _write_temp("py2exe_version_", ".txt", generate_version_file(project.version_info))
        prepared.temp_files.append(path)
        config.version_file = path
    if project.manifest.enabled and engine.supports("manifest"):
        vi = project.version_info
        manifest = project.manifest.manifest_config(
            config.output_name or build_name(config),
            vi.product_version or vi.file_version, vi.file_description,
        )
        path = _write_temp("py2exe_manifest_", ".xml", generate_manifest(manifest))
        prepared.temp_files.append(path)
        config.manifest_file = path

    if allow_downloads:
        native += engine.consent_options()
    command, error = engine.build_command(config, python_executable=python,
                                          platform=platform, extra_options=native)
    if error:
        prepared.error = error
        prepared.cleanup()
        return prepared
    options, kit_errors = write_kit(config, texts, rtl=rtl, platform=platform)
    if kit_errors:
        prepared.kit_errors = kit_errors
        prepared.cleanup()
        return prepared
    if options:
        command, _ = engine.build_command(config, python_executable=python,
                                          platform=platform, extra_options=native + options)
        prepared.services = config.runtime_kit.enabled_services()
    prepared.command = command
    prepared.cwd = build_root(config)
    prepared.engine = engine.name
    prepared.env = engine.build_env(python)
    engine.prepare_output(config)
    return prepared


def kit_unsupported_finding(engine) -> Finding:
    """The finding that stops a Runtime Kit build with an engine that lacks it."""
    return Finding("engine_feature_unsupported", SEVERITY_ERROR,
                   {"engine": engine.display_name, "feature": "runtime_kit"})


def popen_options(engine: str = "pyinstaller", env: Optional[Dict[str, str]] = None) -> dict:
    """Extra ``Popen`` arguments for a build with ``engine``.

    An engine that may stop to ask a question (Nuitka's download prompt)
    gets a closed stdin, so its question is answered "no" by the engine
    itself instead of waiting forever on a pipe nobody writes to.
    """
    options: dict = {}
    if not get_engine(engine).interactive_stdin:
        options["stdin"] = subprocess.DEVNULL
    if env is not None:
        options["env"] = env
    return options


def stream_command(command: List[str], cwd: str, on_line: Callable[[str], None],
                   on_stage: Optional[Callable[[str, int], None]] = None,
                   popen=None, engine: str = "pyinstaller",
                   env: Optional[Dict[str, str]] = None) -> int:
    """Run ``command``, passing each output line on; returns the exit code.

    ``on_stage(stage_key, percent)`` is called whenever the engine enters a
    new phase, so a terminal can print a marker line for it.
    """
    tracker = BuildStageTracker(get_engine(engine).stages)
    last = tracker.stage
    process = (popen or subprocess.Popen)(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace", bufsize=1, cwd=cwd or None,
        **popen_options(engine, env),
    )
    try:
        for line in process.stdout:
            line = line.rstrip("\r\n")
            on_line(line)
            if tracker.feed(line) and tracker.stage != last:
                last = tracker.stage
                if on_stage is not None:
                    on_stage(last, tracker.percent)
        return process.wait()
    except BaseException:
        process.terminate()
        process.wait()
        raise


def run_build(prepared: PreparedBuild, on_line: Callable[[str], None],
              on_stage: Optional[Callable[[str, int], None]] = None,
              popen=None) -> BuildOutcome:
    """Run a prepared build and clean up its temporary files."""
    if prepared.error or prepared.kit_errors or not prepared.command:
        prepared.cleanup()
        return BuildOutcome(False, error=prepared.error or "cannot build")
    try:
        code = stream_command(prepared.command, prepared.cwd, on_line, on_stage, popen,
                              engine=prepared.engine, env=prepared.env)
    except OSError as e:
        return BuildOutcome(False, error=str(e))
    finally:
        prepared.cleanup()
    return BuildOutcome(code == 0, code)
