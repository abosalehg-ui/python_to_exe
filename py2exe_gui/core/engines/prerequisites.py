"""What an engine needs on the build machine, checked before building.

PyInstaller needs nothing but itself. Nuitka compiles C, so it needs a C
compiler, a Python version it supports and, on Linux, ``patchelf`` and
``readelf`` (both found missing by real builds — see ``tests/data/nuitka``).

Everything here is cheap — ``which`` lookups, a file glob, ``pyvenv.cfg`` — so
the doctor can run it on every change. No compiler is ever run, nothing is
downloaded or installed.

Windows and macOS detection is written from the tools' documented locations
and could not be exercised in the Linux environment this was built in.
"""

import glob
import os
import shutil
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Mapping, Optional

from py2exe_gui.core.fixes import SEVERITY_ERROR, SEVERITY_WARNING, Finding


def _which(name: str, path: Optional[str] = None) -> Optional[str]:
    return shutil.which(name, path=path)


@dataclass
class Toolchain:
    """Facts about the machine a build runs on."""

    platform: str = field(default_factory=lambda: sys.platform)
    #: "3.12" — the *build* interpreter's version, '' when unknown.
    python_version: str = ""
    #: The build interpreter's folder: a pip-installed ``patchelf`` lives there.
    python_dir: str = ""
    which: Callable[[str], Optional[str]] = _which
    env: Mapping[str, str] = field(default_factory=lambda: dict(os.environ))
    #: Glob patterns of Visual Studio C++ tools (Windows).
    glob: Callable[[str], List[str]] = glob.glob

    @classmethod
    def for_python(cls, python: str = "") -> "Toolchain":
        """The toolchain for ``python`` (default: the interpreter running the app).

        Another interpreter's version is read from its ``pyvenv.cfg`` (the
        isolated environments are venvs), never by running it.
        """
        python = python or sys.executable
        if os.path.normcase(os.path.abspath(python)) == os.path.normcase(
                os.path.abspath(sys.executable)):
            version = "{}.{}".format(*sys.version_info[:2])
        else:
            version = _pyvenv_version(python)
        return cls(python_version=version, python_dir=os.path.dirname(python))

    def find(self, name: str) -> Optional[str]:
        """``name`` where a Nuitka build looks: PATH, after the interpreter's folder.

        Nuitka runs ``patchelf`` from PATH only; builds put the build
        interpreter's folder first on PATH (``Engine.build_env``), so a
        ``pip install patchelf`` into an isolated environment is found too.
        """
        if self.python_dir:
            found = self.which(name, self.python_dir)
            if found:
                return found
        return self.which(name)


def _pyvenv_version(python: str) -> str:
    from py2exe_gui.core.venv_manager import read_pyvenv_version

    env_dir = os.path.dirname(os.path.dirname(os.path.abspath(python)))
    full = read_pyvenv_version(env_dir)
    return ".".join(full.split(".")[:2]) if full else ""


def _version_key(version: str):
    try:
        return tuple(int(p) for p in version.split("."))
    except ValueError:
        return ()


# ── C compilers ────────────────────────────────────────────────────────────

#: Where Visual Studio (and the stand-alone Build Tools) put the C++ tools.
MSVC_GLOBS = (
    r"{pf}\Microsoft Visual Studio\*\*\VC\Tools\MSVC\*",
    r"{pf86}\Microsoft Visual Studio\*\*\VC\Tools\MSVC\*",
)


def find_c_compiler(tc: Toolchain) -> Dict[str, str]:
    """``{"kind": "msvc"|"mingw"|"gcc"|"clang"|"cc", "path": ...}`` or {}."""
    if tc.platform.startswith("win"):
        if tc.which("cl"):
            return {"kind": "msvc", "path": tc.which("cl") or ""}
        pf = tc.env.get("ProgramFiles", r"C:\Program Files")
        pf86 = tc.env.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        for pattern in MSVC_GLOBS:
            hits = tc.glob(pattern.format(pf=pf, pf86=pf86))
            if hits:
                return {"kind": "msvc", "path": sorted(hits)[-1]}
        gcc = tc.which("gcc")
        if gcc:
            return {"kind": "mingw", "path": gcc}
        return {}
    cc = tc.env.get("CC", "")
    if cc:
        path = cc if os.path.isabs(cc) and os.path.isfile(cc) else tc.which(cc)
        if path:
            return {"kind": "cc", "path": path}
    order = ("clang", "gcc", "cc") if tc.platform == "darwin" else ("gcc", "clang", "cc")
    for name in order:
        path = tc.which(name)
        if path:
            return {"kind": name, "path": path}
    return {}


# ── Nuitka ─────────────────────────────────────────────────────────────────


def nuitka_findings(tc: Toolchain, is_installed: Callable[[str], bool]) -> List[Finding]:
    """Everything Nuitka needs on this machine that is missing."""
    from py2exe_gui.core.engines.nuitka import (
        EXPERIMENTAL_PYTHONS,
        SUPPORTED_PYTHONS,
        VERIFIED_VERSION,
    )

    findings: List[Finding] = []
    if not is_installed("nuitka"):
        findings.append(Finding("nuitka_missing", SEVERITY_ERROR))

    version = tc.python_version
    if version and version not in SUPPORTED_PYTHONS:
        newest = max(SUPPORTED_PYTHONS + EXPERIMENTAL_PYTHONS, key=_version_key)
        if version in EXPERIMENTAL_PYTHONS:
            findings.append(Finding("nuitka_python_experimental", SEVERITY_WARNING,
                                    {"version": version, "nuitka": VERIFIED_VERSION}))
        elif _version_key(version) > _version_key(newest):
            findings.append(Finding("nuitka_python_unsupported", SEVERITY_ERROR,
                                    {"version": version, "nuitka": VERIFIED_VERSION}))

    compiler = find_c_compiler(tc)
    if not compiler:
        if tc.platform.startswith("win"):
            # Nuitka can download MinGW itself — only with the user's consent.
            findings.append(Finding("nuitka_no_compiler_windows", SEVERITY_WARNING))
        else:
            code = ("nuitka_no_compiler_macos" if tc.platform == "darwin"
                    else "nuitka_no_compiler")
            findings.append(Finding(code, SEVERITY_ERROR))

    if tc.platform.startswith("linux"):
        for tool in ("patchelf", "readelf"):
            if not tc.find(tool):
                findings.append(Finding("nuitka_tool_missing", SEVERITY_ERROR, {"tool": tool}))
    return findings
