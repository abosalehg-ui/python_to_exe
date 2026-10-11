"""The core and the command line never touch Qt, whichever binding is installed.

These tests need no Qt binding: they run in the core CI job, and they are the
guard behind the rule in CONTRIBUTING.md. Two layers:

- a static scan of ``py2exe_gui/core/`` (and the modules the command line
  shares with the GUI) for any import of PySide6, PyQt5 or ``py2exe_gui.qt``;
- a subprocess that blocks both bindings (``sys.modules[name] = None``) and
  imports every core module, the command line and the Runtime Kit.
"""

import os
import pkgutil
import re
import subprocess
import sys

import p2e_runtime
import py2exe_gui.core

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE = os.path.join(ROOT, "py2exe_gui")

#: Modules outside core/ that the command line imports, so they must be Qt-free too.
SHARED_MODULES = ("cli.py", "constants.py", "paths.py", "strings.py", "templates.py", "texts.py")

QT_IMPORT = re.compile(r"^\s*(?:from|import)\s+(?:PySide6|PyQt5|PySide2|PyQt6|py2exe_gui\.qt)\b", re.M)


def python_files(folder):
    for dirpath, _dirs, files in os.walk(folder):
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def test_core_never_imports_qt_statically():
    offenders = []
    for path in python_files(os.path.join(PACKAGE, "core")):
        with open(path, encoding="utf-8") as f:
            if QT_IMPORT.search(f.read()):
                offenders.append(os.path.relpath(path, ROOT))
    assert offenders == []


def test_cli_shared_modules_never_import_qt_statically():
    offenders = []
    for name in SHARED_MODULES:
        with open(os.path.join(PACKAGE, name), encoding="utf-8") as f:
            if QT_IMPORT.search(f.read()):
                offenders.append(name)
    assert offenders == []


def test_runtime_kit_never_imports_qt_statically():
    offenders = [os.path.relpath(p, ROOT) for p in python_files(os.path.join(ROOT, "p2e_runtime"))
                 if QT_IMPORT.search(open(p, encoding="utf-8").read())]
    assert offenders == []


def test_only_the_compat_layer_imports_a_binding_directly():
    """Everything else (UI, app, tests) goes through ``py2exe_gui.qt``."""
    direct = re.compile(r"^\s*(?:from|import)\s+(?:PySide6|PyQt5)\b", re.M)
    offenders = []
    for path in python_files(PACKAGE):
        if os.path.basename(path) == "qt.py":
            continue
        with open(path, encoding="utf-8") as f:
            if direct.search(f.read()):
                offenders.append(os.path.relpath(path, ROOT))
    assert offenders == []


def all_modules(package):
    names = [package.__name__]
    for info in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        names.append(info.name)
    return names


def test_core_cli_and_runtime_import_with_both_bindings_blocked(tmp_path):
    modules = all_modules(py2exe_gui.core) + all_modules(p2e_runtime) + ["py2exe_gui.cli"]
    assert len(modules) > 40
    code = (
        "import importlib, sys\n"
        "for name in ('PySide6', 'PyQt5', 'PySide2', 'PyQt6'):\n"
        "    sys.modules[name] = None\n"
        f"for name in {modules!r}:\n"
        "    importlib.import_module(name)\n"
        "loaded = sorted(m for m in sys.modules if sys.modules[m] is not None and "
        "m.split('.')[0] in ('PySide6', 'PyQt5') or m == 'py2exe_gui.qt')\n"
        "assert loaded == [], loaded\n"
        "print(len(sys.modules))\n"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=str(tmp_path), capture_output=True,
                            text=True, timeout=300, env={**os.environ, "PYTHONPATH": ROOT})
    assert result.returncode == 0, result.stderr


def test_the_compat_layer_fails_clearly_without_a_binding(tmp_path):
    """``py2exe_gui.qt`` raises ModuleNotFoundError naming both bindings."""
    code = (
        "import sys\n"
        "sys.modules['PySide6'] = sys.modules['PyQt5'] = None\n"
        "try:\n"
        "    import py2exe_gui.qt\n"
        "except ModuleNotFoundError as e:\n"
        "    assert 'PySide6' in str(e) and 'PyQt5' in str(e), e\n"
        "else:\n"
        "    raise SystemExit('imported without a binding')\n"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=str(tmp_path), capture_output=True,
                            text=True, timeout=120, env={**os.environ, "PYTHONPATH": ROOT})
    assert result.returncode == 0, result.stderr + result.stdout
