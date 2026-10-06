"""Tests for the size lab: reading PyInstaller's TOC files and advising.

The fixtures write TOC files in the exact literal format PyInstaller 6 uses
(checked against real builds), pointing at files of known sizes.
"""

import os

import pytest

from py2exe_gui.core.build_history import BuildRecord
from py2exe_gui.core.config import BuildConfig
from py2exe_gui.core.size_analyzer import (
    GROUP_RUNTIME,
    GROUP_SCRIPT,
    GROUP_STDLIB,
    Entry,
    analyze_build,
    exclude_suggestions,
    format_size,
    group_for,
    indirect_packages,
    onefile_too_big,
    output_path_for,
    path_size,
    previous_size,
    read_toc,
    size_change,
)

MB = 1024 * 1024


def blob(path, size):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"\0" * size)
    return path


def make_build(tmp_path, onefile=True, name="app"):
    """A fake PyInstaller work folder + output, laid out as the real thing."""
    root = tmp_path / "proj"
    src = root / "app.py"
    root.mkdir(exist_ok=True)
    src.write_text("import numpy\nimport helpers\n")
    (root / "helpers.py").write_text("")
    work = root / "build" / name
    store = tmp_path / "site"

    numpy_so = blob(str(store / "numpy" / "core.so"), 3 * MB)
    numpy_lib = blob(str(store / "numpy.libs" / "openblas.so"), 2 * MB)
    tk = blob(str(store / "tk" / "tk.tcl"), MB)
    pyz = blob(str(work / "PYZ-00.pyz"), 300_000)
    libpython = blob(str(store / "libpython3.12.so.1.0"), 4 * MB)
    mod_numpy = blob(str(store / "src" / "numpy_init.py"), 400_000)
    mod_json = blob(str(store / "src" / "json.py"), 200_000)
    mod_helpers = blob(str(root / "helpers.py"), 0)
    blob(str(store / "src" / "pyimod.py"), 1000)

    pyz_toc = (
        f"({str(pyz)!r},\n"
        f" [('numpy', {mod_numpy!r}, 'PYMODULE'),\n"
        f"  ('json', {mod_json!r}, 'PYMODULE'),\n"
        f"  ('helpers', {mod_helpers!r}, 'PYMODULE')])\n"
    )
    entries = [
        ("PYZ-00.pyz", str(pyz), "PYZ"),
        ("app", str(src), "PYSOURCE"),
        ("pyi_rth_inspect", str(src), "PYSOURCE"),
        ("numpy/core.so", numpy_so, "EXTENSION"),
        ("numpy.libs/openblas.so", numpy_lib, "BINARY"),
        ("_tk_data/tk.tcl", tk, "DATA"),
        ("libpython3.12.so.1.0", libpython, "BINARY"),
        ("numpy.libs/link.so", numpy_lib, "SYMLINK"),
    ]
    bundle = "PKG-00.toc" if onefile else "COLLECT-00.toc"
    os.makedirs(work, exist_ok=True)
    (work / "PYZ-00.toc").write_text(pyz_toc)
    (work / bundle).write_text(
        f"({str(work / 'x.pkg')!r},\n {{'BINARY': True}},\n {entries!r},\n False)\n"
    )
    if onefile:
        blob(str(root / "dist" / name), 6 * MB)
    else:
        blob(str(root / "dist" / name / name), MB)
        blob(str(root / "dist" / name / "_internal" / "numpy" / "core.so"), 3 * MB)
    return BuildConfig(source=str(src), onefile=onefile)


# ── Reading ────────────────────────────────────────────────────────────────


def test_read_toc_finds_entries_at_any_depth(tmp_path):
    path = tmp_path / "x.toc"
    path.write_text("('a', {'k': 1}, [('m', '/p', 'PYMODULE'), [('d', '/q', 'DATA')]], 0)")
    assert [(e.name, e.typecode) for e in read_toc(str(path))] == [
        ("m", "PYMODULE"), ("d", "DATA"),
    ]


@pytest.mark.parametrize("content", ["not python", "__import__('os').system('x')", ""])
def test_read_toc_never_executes_and_tolerates_garbage(tmp_path, content):
    path = tmp_path / "bad.toc"
    path.write_text(content)
    assert read_toc(str(path)) == []


def test_read_toc_missing_file(tmp_path):
    assert read_toc(str(tmp_path / "none.toc")) == []


@pytest.mark.parametrize(
    "entry, local, expected",
    [
        (Entry("app", "", "PYSOURCE"), (), GROUP_SCRIPT),
        (Entry("pyi_rth_pkgutil", "", "PYSOURCE"), (), GROUP_RUNTIME),
        (Entry("json.decoder", "", "PYMODULE"), (), GROUP_STDLIB),
        (Entry("pyimod02_importers", "", "PYMODULE"), (), GROUP_RUNTIME),
        (Entry("_sysconfigdata__linux", "", "PYMODULE"), (), GROUP_RUNTIME),
        (Entry("helpers.sub", "", "PYMODULE"), ("helpers",), GROUP_SCRIPT),
        (Entry("numpy.core", "", "PYMODULE"), (), "numpy"),
        (Entry("numpy.libs/x.so", "", "BINARY"), (), "numpy"),
        (Entry("pillow.libs/x.so", "", "BINARY"), (), "PIL"),
        (Entry("PyQt5/Qt5/lib/x.so", "", "BINARY"), (), "PyQt5"),
        (Entry("_tcl_data/init.tcl", "", "DATA"), (), "tkinter"),
        (Entry("python312.dll", "", "BINARY"), (), GROUP_RUNTIME),
        (Entry("_ssl.pyd", "", "EXTENSION"), (), GROUP_RUNTIME),
        (Entry("python3.12/lib-dynload/_ctypes.so", "", "EXTENSION"), (), GROUP_RUNTIME),
        (Entry("certifi/cacert.pem", "", "DATA"), (), "certifi"),
        (Entry("requests-2.32.0.dist-info/METADATA", "", "DATA"), (), "requests"),
    ],
)
def test_group_for(entry, local, expected):
    assert group_for(entry, local) == expected


# ── Analysis ───────────────────────────────────────────────────────────────


def test_onefile_build_inventory(tmp_path):
    config = make_build(tmp_path, onefile=True)
    report = analyze_build(config)
    assert report.ok
    assert report.output_bytes == 6 * MB
    groups = report.groups
    assert groups["numpy"] > 5 * MB          # extension + .libs + its share of PYZ
    assert groups["tkinter"] == MB
    assert GROUP_RUNTIME in groups and GROUP_STDLIB in groups
    # The archive's real size is spread over its modules, not their source size.
    pyz_share = groups["numpy"] - 5 * MB + groups[GROUP_STDLIB]
    assert abs(pyz_share - 300_000) <= 2
    # Symlinks are not counted twice.
    assert "numpy.libs/link.so" not in [name for name, _ in report.largest_files]


def test_folder_build_inventory(tmp_path):
    config = make_build(tmp_path, onefile=False)
    report = analyze_build(config)
    assert report.ok
    assert report.output_bytes == 4 * MB
    assert report.ranked(1)[0][0] == "numpy"


def test_no_build_yields_empty_report(tmp_path):
    (tmp_path / "a.py").write_text("")
    report = analyze_build(BuildConfig(source=str(tmp_path / "a.py")))
    assert not report.ok and report.groups == {}


def test_output_path_and_size(tmp_path):
    config = make_build(tmp_path, onefile=True)
    assert output_path_for(config).endswith(os.path.join("dist", "app"))
    assert output_path_for(BuildConfig(source=config.source, onefile=False)) == ""


def test_path_size_skips_symlinks(tmp_path):
    real = blob(str(tmp_path / "d" / "real.bin"), 1000)
    try:
        os.symlink(real, str(tmp_path / "d" / "link.bin"))
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not available")
    assert path_size(str(tmp_path / "d")) == 1000


# ── Advice ─────────────────────────────────────────────────────────────────


def test_exclude_suggestions_skip_what_the_code_imports(tmp_path):
    config = make_build(tmp_path)
    report = analyze_build(config)
    found = exclude_suggestions(report, {"numpy"}, config, min_bytes=1)
    assert [f.params["package"] for f in found] == ["tkinter"]
    assert found[0].fixes[0].value == "--exclude-module tkinter"
    assert exclude_suggestions(report, {"tkinter"}, config, min_bytes=1) == []


def test_exclude_suggestions_skip_already_excluded(tmp_path):
    config = make_build(tmp_path)
    config.extra_args = "--exclude-module tkinter"
    report = analyze_build(config)
    assert exclude_suggestions(report, set(), config, min_bytes=1) == []


def test_indirect_packages(tmp_path):
    report = analyze_build(make_build(tmp_path))
    assert [name for name, _ in indirect_packages(report, set(), min_bytes=1)][:2] == [
        "numpy", "tkinter",
    ]
    assert "numpy" not in [n for n, _ in indirect_packages(report, {"numpy"}, min_bytes=1)]


def test_onefile_too_big(tmp_path):
    config = make_build(tmp_path)
    report = analyze_build(config)
    assert not onefile_too_big(report, config)
    report.output_bytes = 500 * MB
    assert onefile_too_big(report, config)
    assert not onefile_too_big(report, BuildConfig(onefile=False))


@pytest.mark.parametrize(
    "size, text",
    [(0, "0 B"), (900, "900 B"), (2048, "2 KB"), (5 * MB + MB // 2, "5.5 MB"),
     (3 * 1024 * MB, "3.00 GB")],
)
def test_format_size(size, text):
    assert format_size(size) == text


def test_size_change():
    assert size_change(0, 10) is None
    assert size_change(100, 50) == -50.0


def test_previous_size_finds_the_last_successful_build():
    records = [
        BuildRecord(source="a.py", output_name="A", success=True, size_bytes=300),
        BuildRecord(source="a.py", output_name="A", success=False, size_bytes=0),
        BuildRecord(source="b.py", output_name="B", success=True, size_bytes=999),
        BuildRecord(source="a.py", output_name="A", success=True, size_bytes=200),
    ]
    assert previous_size(records, "a.py", "A") == 300
    assert previous_size(records, "a.py", "A", skip=1) == 200
    assert previous_size(records, "c.py", "C") == 0
