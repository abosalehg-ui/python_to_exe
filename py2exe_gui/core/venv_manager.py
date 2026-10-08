"""Isolated, per-project build environments.

PyInstaller bundles whatever its hooks find importable, so building from a
Python that has every library on the machine installed drags in packages the
project never uses (a matplotlib pulls a Qt binding, pandas pulls scipy...).
A fresh virtual environment holding only what the project imports is the most
effective size reduction there is, and it makes builds reproducible.

This module only *plans* and *inspects*: it returns the commands to run and
reads an environment's state. Running them is the UI's job, after the user has
seen the exact commands and agreed — installing packages reaches the network.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence

from py2exe_gui.core.knowledge import pip_name_for
from py2exe_gui.core.project_scan import third_party_imports

LOCK_FILE_NAME = "p2e-build.lock"
REQUIREMENTS_FILE_NAME = "requirements.txt"
METADATA_FILE_NAME = "p2e-env.json"

# Import names that never come from PyPI under any name.
_NOT_ON_PYPI = frozenset({"__main__", "__future__"})


# ── Locations ──────────────────────────────────────────────────────────────


def env_dir_for(source: str, root: str) -> str:
    """The environment folder for the project containing ``source``.

    Keyed by the project folder, not the script, so every entry point of one
    project shares an environment. The readable prefix is for humans browsing
    the folder; the hash keeps two projects with the same name apart.
    """
    project = os.path.normcase(os.path.abspath(os.path.dirname(os.path.abspath(source))))
    digest = hashlib.sha1(project.encode("utf-8")).hexdigest()[:10]
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", os.path.basename(project)).strip("_") or "project"
    return os.path.join(root, f"{name[:40]}-{digest}")


def env_python(env_dir: str, platform: Optional[str] = None) -> str:
    """The interpreter inside a virtual environment."""
    plat = platform if platform is not None else sys.platform
    if plat == "win32":
        return os.path.join(env_dir, "Scripts", "python.exe")
    return os.path.join(env_dir, "bin", "python")


def env_exists(env_dir: str, platform: Optional[str] = None) -> bool:
    return os.path.isfile(os.path.join(env_dir, "pyvenv.cfg")) and os.path.isfile(
        env_python(env_dir, platform)
    )


# ── Requirements ───────────────────────────────────────────────────────────


@dataclass
class Requirements:
    """What an environment for this project should contain."""

    #: "lock" (exact pins from p2e-build.lock), "file" (requirements.txt) or
    #: "scan" (inferred from the imports).
    origin: str
    #: Pip arguments: either ["-r", path] or a list of distribution names.
    args: List[str] = field(default_factory=list)
    #: For "scan": the import names the distributions were derived from.
    imports: List[str] = field(default_factory=list)

    def describe(self) -> str:
        if self.origin in ("lock", "file"):
            return os.path.basename(self.args[-1])
        return ", ".join(self.args) or "—"


def project_requirements(source: str, knowledge_path: Optional[str] = None) -> Requirements:
    """Decide what to install, preferring what the user pinned themselves.

    A lock file written by this tool wins (exact reproduction), then the
    project's own requirements.txt, then names derived from the imports.
    """
    project_dir = os.path.dirname(os.path.abspath(source))
    lock = os.path.join(project_dir, LOCK_FILE_NAME)
    if os.path.isfile(lock):
        return Requirements("lock", ["-r", lock])
    requirements = os.path.join(project_dir, REQUIREMENTS_FILE_NAME)
    if os.path.isfile(requirements):
        return Requirements("file", ["-r", requirements])

    imports = sorted(m for m in third_party_imports(source) if m not in _NOT_ON_PYPI)
    names: List[str] = []
    for module in imports:
        dist = pip_name_for(module, knowledge_path)
        if dist not in names:
            names.append(dist)
    return Requirements("scan", names, imports)


# ── Plan ───────────────────────────────────────────────────────────────────


@dataclass
class EnvPlan:
    """The commands that create (or refresh) an environment, in order."""

    env_dir: str
    python: str
    #: Create the venv and install PyInstaller. Each must succeed.
    setup: List[List[str]] = field(default_factory=list)
    #: Install the project's packages. On failure the runner retries the
    #: names one at a time (see ``single_install_command``), so one wrong
    #: guess does not block everything else.
    install: List[str] = field(default_factory=list)
    requirements: Optional[Requirements] = None
    uv: str = ""

    def all_commands(self) -> List[List[str]]:
        commands = list(self.setup)
        if self.install:
            commands.append(self.install)
        return commands


def find_uv() -> str:
    """Path of the ``uv`` tool if installed: it builds environments far faster."""
    return shutil.which("uv") or ""


def _pip(plan_python: str, uv: str) -> List[str]:
    if uv:
        return [uv, "pip", "install", "--python", plan_python]
    return [plan_python, "-m", "pip", "install", "--disable-pip-version-check"]


def plan_environment(
    source: str,
    root: str,
    base_python: str,
    pyinstaller_requirement,
    uv: str = "",
    recreate: bool = False,
    knowledge_path: Optional[str] = None,
    platform: Optional[str] = None,
) -> EnvPlan:
    """Commands to build the project's environment from ``base_python``.

    ``pyinstaller_requirement`` is the build engine's requirement — one string,
    or several (Nuitka on Linux also needs ``patchelf``: ``Engine.requirements``).
    """
    env_dir = env_dir_for(source, root)
    python = env_python(env_dir, platform)
    plan = EnvPlan(env_dir=env_dir, python=python, uv=uv)

    if recreate or not env_exists(env_dir, platform):
        if uv:
            plan.setup.append([uv, "venv", "--python", base_python, env_dir])
        else:
            plan.setup.append([base_python, "-m", "venv", env_dir])
    tools = ([pyinstaller_requirement] if isinstance(pyinstaller_requirement, str)
             else list(pyinstaller_requirement))
    plan.setup.append(_pip(python, uv) + tools)

    requirements = project_requirements(source, knowledge_path)
    plan.requirements = requirements
    if requirements.args:
        plan.install = _pip(python, uv) + list(requirements.args)
    return plan


def single_install_command(plan: EnvPlan, name: str) -> List[str]:
    """Install one distribution — the fallback when the batch install fails."""
    return _pip(plan.python, plan.uv) + [name]


def freeze_command(python: str, uv: str = "") -> List[str]:
    """Command printing the environment's exact package versions."""
    if uv:
        return [uv, "pip", "freeze", "--python", python]
    return [python, "-m", "pip", "freeze", "--disable-pip-version-check"]


def lock_file_path(source: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(source)), LOCK_FILE_NAME)


def format_lock(freeze_output: str) -> str:
    """A lock file from ``pip freeze`` output, minus the build tooling itself.

    PyInstaller and its own dependencies are installed separately by the
    plan, so pinning them here would fight the version range the app expects.
    """
    tooling = {"pyinstaller", "pyinstaller-hooks-contrib", "altgraph", "pefile",
               "pywin32-ctypes", "macholib", "packaging", "setuptools", "pip", "wheel"}
    lines = ["# Exact package versions for a reproducible build.",
             "# Written by Python to EXE Converter; used instead of requirements.txt."]
    for raw in freeze_output.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name = re.split(r"[=<>!~ @\[]", line, maxsplit=1)[0].lower().replace("_", "-")
        if name in tooling:
            continue
        lines.append(line)
    return "\n".join(lines) + "\n"


# ── Inspection ─────────────────────────────────────────────────────────────


@dataclass
class EnvStatus:
    exists: bool
    env_dir: str
    python_version: str = ""
    size_bytes: int = 0
    metadata: Dict[str, object] = field(default_factory=dict)


def read_pyvenv_version(env_dir: str) -> str:
    """Python version recorded in ``pyvenv.cfg`` (venv and uv spell it differently)."""
    try:
        with open(os.path.join(env_dir, "pyvenv.cfg"), encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return ""
    values = {}
    for line in content.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            values[key.strip().lower()] = value.strip()
    return values.get("version_info") or values.get("version") or ""


def folder_size(path: str) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def env_status(env_dir: str, platform: Optional[str] = None, with_size: bool = True) -> EnvStatus:
    if not env_exists(env_dir, platform):
        return EnvStatus(False, env_dir)
    metadata: Dict[str, object] = {}
    try:
        with open(os.path.join(env_dir, METADATA_FILE_NAME), encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            metadata = loaded
    except (OSError, ValueError):
        pass
    return EnvStatus(
        True,
        env_dir,
        python_version=read_pyvenv_version(env_dir),
        size_bytes=folder_size(env_dir) if with_size else 0,
        metadata=metadata,
    )


def write_metadata(env_dir: str, data: Dict[str, object]) -> bool:
    try:
        with open(os.path.join(env_dir, METADATA_FILE_NAME), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def delete_env(env_dir: str, root: str) -> bool:
    """Remove an environment — only one this tool created, inside ``root``.

    The checks guard against a corrupted setting turning "delete environment"
    into "delete some other folder".
    """
    target = os.path.normcase(os.path.realpath(env_dir))
    base = os.path.normcase(os.path.realpath(root))
    if not target.startswith(base.rstrip("\\/") + os.sep) or target == base:
        return False
    if not os.path.isfile(os.path.join(env_dir, "pyvenv.cfg")):
        return False
    shutil.rmtree(env_dir, ignore_errors=True)
    return not os.path.exists(env_dir)


# ── Asking another interpreter what it can import ─────────────────────────

_PROBE = (
    "import importlib.util, json, sys\n"
    "def ok(m):\n"
    "    try:\n"
    "        return importlib.util.find_spec(m) is not None\n"
    "    except Exception:\n"
    "        return False\n"
    "print(json.dumps({m: ok(m) for m in sys.argv[1:]}))\n"
)


class InstalledChecker:
    """``is_installed`` for an interpreter other than the one running the app.

    The doctor asks module by module; spawning a process for each would make
    it sluggish, so callers ``prefetch`` the whole set in one subprocess and
    later lookups are served from the cache.
    """

    def __init__(self, python: str, runner: Optional[Callable[..., object]] = None,
                 timeout: float = 20.0):
        self.python = python
        self.timeout = timeout
        self._run = runner or subprocess.run
        self._cache: Dict[str, bool] = {}

    def prefetch(self, modules: Iterable[str]) -> None:
        missing = sorted({m.split(".")[0] for m in modules} - set(self._cache))
        if not missing:
            return
        try:
            result = self._run(
                [self.python, "-c", _PROBE, *missing],
                capture_output=True, text=True, timeout=self.timeout,
            )
            answers = json.loads(result.stdout or "{}")
        except (OSError, ValueError, subprocess.SubprocessError):
            answers = {}
        for module in missing:
            self._cache[module] = bool(answers.get(module, False))

    def __call__(self, module: str) -> bool:
        top = module.split(".")[0]
        if top not in self._cache:
            self.prefetch([top])
        return self._cache[top]

    def invalidate(self) -> None:
        self._cache.clear()


def python_version(python: str, runner: Optional[Callable[..., object]] = None) -> str:
    """``3.12.1`` for an interpreter path, or '' when it cannot be run."""
    run = runner or subprocess.run
    try:
        result = run(
            [python, "-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])"],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return (getattr(result, "stdout", "") or "").strip()


_SHELL_SPECIAL = re.compile(r"""[\s<>|&;()$`'"*?!^%]""")


def quote_command(command: Sequence[str]) -> str:
    """A command as the user would type it, for the consent dialog.

    Arguments with shell metacharacters are quoted: copied unquoted,
    ``pyinstaller>=6.0,<7`` would redirect a file instead of naming a version.
    """
    parts = []
    for part in command:
        if not part or _SHELL_SPECIAL.search(part):
            parts.append('"' + part.replace('"', '\\"') + '"')
        else:
            parts.append(part)
    return " ".join(parts)
