"""The converter's own Qt binding never leaks into the user's build.

The converter runs on PySide6 (or PyQt5). A user who builds a Tkinter or
console program must not get a copy of Qt in their EXE: that is 100+ MB,
and under PySide6 it would also drag the LGPL into a program that never
asked for it. This test builds a non-Qt sample the way the application does
when "isolated environment" is on, from a process that *has* the converter's
binding loaded, and inspects everything PyInstaller produced.

A real build: marked ``slow``; CI runs it in its own job under PySide6.
"""

import os
import re
import subprocess
import sys

import pytest

from py2exe_gui.constants import PYINSTALLER_REQUIREMENT
from py2exe_gui.core import BuildConfig
from py2exe_gui.core.build_runner import prepare_build, run_build
from py2exe_gui.core.diagnostics import warn_file_for
from py2exe_gui.core.project_file import ProjectConfig
from py2exe_gui.core.smoke_test import locate_built_executable
from py2exe_gui.core.venv_manager import find_uv, plan_environment

pytestmark = pytest.mark.slow

#: Anything of Qt that could show up in a bundle, whichever binding.
QT_MARKERS = re.compile(r"PySide6|PyQt5|PySide2|PyQt6|shiboken|libQt[56]|Qt[56]Core|QtCore", re.I)

SAMPLE = '''
import json
import pathlib
import sqlite3
import sys

con = sqlite3.connect(":memory:")
rows = con.execute("select 1 + 1").fetchall()
print(json.dumps({"hello": "world", "rows": rows, "argv": len(sys.argv),
                  "cwd": str(pathlib.Path.cwd())}))
'''


@pytest.fixture(scope="module")
def converter_binding():
    """The converter's binding, loaded in this process as the GUI would have it."""
    qt = pytest.importorskip("py2exe_gui.qt", reason="no Qt binding (PySide6/PyQt5) installed")
    assert qt.API in sys.modules
    return qt.API


@pytest.fixture(scope="module")
def isolated_env(tmp_path_factory):
    """A fresh environment with PyInstaller only, built by the app's own planner."""
    root = tmp_path_factory.mktemp("qt_leak")
    project = root / "proj"
    project.mkdir()
    source = project / "noqt.py"
    source.write_text(SAMPLE, encoding="utf-8")
    plan = plan_environment(str(source), str(root / "envs"), sys.executable,
                            PYINSTALLER_REQUIREMENT, uv=find_uv())
    for command in plan.setup:
        result = subprocess.run(command, capture_output=True, text=True, timeout=900)
        assert result.returncode == 0, f"{command}\n{result.stdout}\n{result.stderr}"
    assert plan.install == [], plan.install  # standard library only: nothing to install
    return {"root": root, "source": source, "python": plan.python}


def python_can_import(python, module):
    return subprocess.run([python, "-c", f"import {module}"], capture_output=True,
                          timeout=120).returncode == 0


def test_isolated_environment_has_no_qt(isolated_env, converter_binding):
    assert python_can_import(isolated_env["python"], "PyInstaller")
    assert python_can_import(sys.executable, converter_binding)
    for binding in ("PySide6", "PyQt5"):
        assert not python_can_import(isolated_env["python"], binding), binding


@pytest.fixture(scope="module")
def built(isolated_env, converter_binding):
    """The sample, built through ``prepare_build``/``run_build`` as the GUI does."""
    out = isolated_env["root"] / "out"
    config = BuildConfig(source=str(isolated_env["source"]), output_name="NoQtApp",
                         output_dir=str(out), onefile=False, windowed=False,
                         isolated_env=True, clean=True, noconfirm=True)
    prepared = prepare_build(ProjectConfig(name="NoQtApp", build=config),
                             python=isolated_env["python"])
    assert not prepared.error and prepared.kit_errors == [], prepared
    assert prepared.command[0] == isolated_env["python"], prepared.command
    lines = []
    outcome = run_build(prepared, lines.append)
    assert outcome.ok, outcome.error + "\n" + "\n".join(lines)
    exe = locate_built_executable(str(out), "NoQtApp", onefile=False)
    assert exe, "\n".join(lines)
    return {"config": config, "exe": exe, "dist": os.path.dirname(exe), "out": out,
            "log": "\n".join(lines)}


def test_no_qt_file_in_the_distribution(built):
    files = []
    for dirpath, _dirs, names in os.walk(built["dist"]):
        files += [os.path.relpath(os.path.join(dirpath, n), built["dist"]) for n in names]
    assert len(files) > 10, files
    assert [f for f in files if QT_MARKERS.search(f)] == []
    # The isolated interpreter's own site-packages is where Qt would have come from.
    assert not any("site-packages" in f and QT_MARKERS.search(f) for f in files)


def test_no_qt_module_in_pyinstallers_analysis(built):
    """PyInstaller's own records: the collected modules, and its warnings."""
    work = built["out"] / "build" / "NoQtApp"
    tocs = sorted(str(p) for p in work.glob("*.toc"))
    assert tocs, list(work.iterdir())
    for path in tocs + [warn_file_for(built["config"])]:
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as f:
            hits = [line.strip() for line in f if QT_MARKERS.search(line)]
        assert hits == [], (path, hits[:5])
    assert not QT_MARKERS.search(built["log"].replace("qt_leak", "")), built["log"]


def test_the_built_program_runs_without_qt(built, tmp_path):
    result = subprocess.run([built["exe"]], cwd=str(tmp_path), capture_output=True, text=True,
                            timeout=120, env={k: v for k, v in os.environ.items()
                                              if not k.startswith("PYTHON")})
    assert result.returncode == 0, result.stderr
    assert '"hello": "world"' in result.stdout
