"""Tests for the project doctor's pre-build checks."""

import textwrap

import pytest

from py2exe_gui.core.config import BuildConfig
from py2exe_gui.core.icon_studio import PNG_SIGNATURE, pack_ico
from py2exe_gui.core.project_doctor import (
    examine,
    find_entry_candidates,
    has_entry_point,
    local_module_names,
)


def everything_installed(_module):
    return True


def nothing_installed(_module):
    return False


def write(path, code):
    path.write_text(textwrap.dedent(code), encoding="utf-8")
    return str(path)


def run(tmp_path, code, name="app.py", installed=everything_installed, **config):
    source = write(tmp_path / name, code)
    cfg = BuildConfig(source=source, **config)
    return examine(source, cfg, is_installed=installed)


def codes(report):
    return [f.code for f in report.findings]


def by_code(report, code):
    matches = [f for f in report.findings if f.code == code]
    assert matches, f"{code} not in {codes(report)}"
    return matches[0]


# ── Basics ─────────────────────────────────────────────────────────────────


def test_clean_script_scores_100(tmp_path):
    report = run(tmp_path, 'print("hello")\n')
    assert report.findings == []
    assert report.score == 100


def test_unreadable_source(tmp_path):
    source = str(tmp_path / "missing.py")
    report = examine(source, BuildConfig(source=source))
    assert codes(report) == ["source_unreadable"]


def test_syntax_error_reports_line(tmp_path):
    report = run(tmp_path, "x = 1\ndef broken(:\n")
    finding = by_code(report, "syntax_error")
    assert finding.params["line"] == "2"


# ── Missing packages ───────────────────────────────────────────────────────


def test_uninstalled_third_party_import_is_an_error(tmp_path):
    report = run(tmp_path, "import yaml\nprint(yaml)\n", installed=nothing_installed)
    finding = by_code(report, "missing_package")
    assert finding.severity == "error"
    assert finding.params == {"module": "yaml", "pip": "PyYAML"}


def test_stdlib_and_local_modules_are_not_reported(tmp_path):
    (tmp_path / "helpers.py").write_text("X = 1\n")
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    report = run(
        tmp_path,
        "import os, json\nimport helpers\nfrom pkg import x\nprint(1)\n",
        installed=nothing_installed,
    )
    assert "missing_package" not in codes(report)
    assert report.third_party == set()


# ── Knowledge base ─────────────────────────────────────────────────────────


def test_package_needing_collection_gets_fixes(tmp_path):
    report = run(tmp_path, "import docx\nprint(docx)\n")
    finding = by_code(report, "package_needs_collect")
    assert [f.value for f in finding.fixes] == ["--collect-data docx"]


def test_collection_already_configured_is_not_reported(tmp_path):
    report = run(tmp_path, "import docx\nprint(docx)\n", extra_args="--collect-data docx")
    assert "package_needs_collect" not in codes(report)


def test_flask_templates_folder_is_suggested(tmp_path):
    (tmp_path / "templates").mkdir()
    report = run(tmp_path, "import flask\nprint(flask)\n")
    finding = by_code(report, "package_data_dir")
    assert finding.params["folder"] == "templates"
    assert finding.fixes[0].value == str(tmp_path / "templates")


def test_console_stream_package_only_matters_when_windowed(tmp_path):
    code = "import tqdm\nprint(tqdm)\n"
    assert "package_console_streams" not in codes(run(tmp_path, code))
    report = run(tmp_path, code, windowed=True)
    finding = by_code(report, "package_console_streams")
    assert finding.severity == "error"
    assert finding.fixes[0].kind == "console"


def test_large_package_is_informational(tmp_path):
    report = run(tmp_path, "import pandas\nprint(pandas)\n")
    finding = by_code(report, "large_package")
    assert finding.severity == "info"
    assert report.score == 100


def test_two_qt_bindings_is_an_error(tmp_path):
    report = run(tmp_path, "import PyQt5\nimport PySide6\nprint(1)\n")
    assert by_code(report, "multiple_qt_bindings").severity == "error"


def test_other_installed_qt_bindings_get_excluded(tmp_path):
    installed = {"PyQt5", "PySide6"}
    report = run(
        tmp_path, "import PyQt5\nprint(1)\n", installed=lambda m: m in installed
    )
    finding = by_code(report, "other_qt_bindings_installed")
    assert [f.value for f in finding.fixes] == ["--exclude-module PySide6"]


# ── Data files and paths ───────────────────────────────────────────────────


def test_existing_relative_file_is_suggested_for_bundling(tmp_path):
    (tmp_path / "config.json").write_text("{}")
    report = run(tmp_path, 'data = open("config.json").read()\n')
    finding = by_code(report, "data_not_bundled")
    assert finding.fixes[0].value == str(tmp_path / "config.json")
    assert "relative_paths" in codes(report)


def test_nested_file_bundles_its_top_folder(tmp_path):
    (tmp_path / "assets" / "img").mkdir(parents=True)
    (tmp_path / "assets" / "img" / "logo.png").write_bytes(b"x")
    report = run(tmp_path, 'path = "assets/img/logo.png"\nprint(path)\n')
    finding = by_code(report, "data_not_bundled")
    assert finding.fixes[0].value == str(tmp_path / "assets")


def test_strings_that_are_not_files_are_ignored(tmp_path):
    report = run(tmp_path, 'msg = "hello.world"\nurl = "https://x.y/z.json"\nprint(msg, url)\n')
    assert "data_not_bundled" not in codes(report)


def test_python_packages_named_in_strings_are_not_data(tmp_path):
    (tmp_path / "plugins").mkdir()
    (tmp_path / "plugins" / "__init__.py").write_text("")
    report = run(tmp_path, 'import importlib\nimportlib.import_module("plugins")\n')
    assert "data_not_bundled" not in codes(report)


def test_already_bundled_folder_is_not_reported(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "a.csv").write_text("1")
    report = run(
        tmp_path, 'f = open("data/a.csv")\n', extra_files=[str(tmp_path / "data")]
    )
    assert "data_not_bundled" not in codes(report)


def test_resource_path_usage_silences_the_relative_path_warning(tmp_path):
    (tmp_path / "a.json").write_text("{}")
    report = run(
        tmp_path,
        "import os, sys\n"
        "base = getattr(sys, '_MEIPASS', '.')\n"
        "f = open(os.path.join(base, 'a.json'))\n",
    )
    assert "relative_paths" not in codes(report)


# ── multiprocessing ────────────────────────────────────────────────────────


def test_multiprocessing_without_freeze_support(tmp_path):
    report = run(tmp_path, "import multiprocessing\nmultiprocessing.Pool(2)\n")
    finding = by_code(report, "missing_freeze_support")
    assert finding.snippet == "freeze_support"


def test_process_pool_executor_counts_too(tmp_path):
    report = run(
        tmp_path,
        "from concurrent.futures import ProcessPoolExecutor\nProcessPoolExecutor()\n",
    )
    assert "missing_freeze_support" in codes(report)


def test_freeze_support_present_is_fine(tmp_path):
    report = run(
        tmp_path,
        """
        import multiprocessing
        if __name__ == "__main__":
            multiprocessing.freeze_support()
        """,
    )
    assert "missing_freeze_support" not in codes(report)


# ── Windowed mode ──────────────────────────────────────────────────────────


def test_input_in_windowed_app(tmp_path):
    code = 'name = input("?")\n'
    assert "input_in_windowed" not in codes(run(tmp_path, code))
    assert "input_in_windowed" in codes(run(tmp_path, code, noconsole=True))


def test_direct_stream_use_in_windowed_app(tmp_path):
    report = run(tmp_path, 'import sys\nsys.stdout.write("x")\n', windowed=True)
    finding = by_code(report, "stream_in_windowed")
    assert finding.params["stream"] == "sys.stdout"


def test_print_is_safe_in_windowed_app(tmp_path):
    report = run(tmp_path, 'print("x")\n', windowed=True)
    assert report.findings == []


def test_reassigned_stream_is_safe(tmp_path):
    report = run(
        tmp_path,
        """
        import os, sys
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w")
        sys.stdout.write("x")
        """,
        windowed=True,
    )
    assert "stream_in_windowed" not in codes(report)


# ── Entry point ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "code, expected",
    [
        ("def main():\n    pass\n", False),
        ('"""doc"""\nimport os\nX = 1\nclass A: pass\n', False),
        ("def main():\n    pass\nmain()\n", True),
        ('if __name__ == "__main__":\n    pass\n', True),
        ('if "__main__" == __name__:\n    pass\n', True),
        ("print(1)\n", True),
    ],
)
def test_has_entry_point(code, expected):
    import ast

    assert has_entry_point(ast.parse(code)) is expected


def test_library_module_suggests_the_real_entry_point(tmp_path):
    write(tmp_path / "main.py", 'if __name__ == "__main__":\n    print(1)\n')
    report = run(tmp_path, "def helper():\n    return 1\n", name="utils.py")
    finding = by_code(report, "no_entry_point")
    assert finding.params["candidate"] == "main.py"
    assert finding.fixes[0].value == str(tmp_path / "main.py")


def test_library_module_alone(tmp_path):
    report = run(tmp_path, "def helper():\n    return 1\n")
    assert "no_entry_point_alone" in codes(report)


def test_entry_candidates_prefer_conventional_names(tmp_path):
    guard = 'if __name__ == "__main__":\n    pass\n'
    write(tmp_path / "zeta.py", guard)
    write(tmp_path / "app.py", guard)
    write(tmp_path / "broken.py", "def (:\n")
    found = find_entry_candidates(str(tmp_path))
    assert [p.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] for p in found] == ["app.py", "zeta.py"]


def test_local_module_names(tmp_path):
    (tmp_path / "a.py").write_text("")
    (tmp_path / "b.pyw").write_text("")
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "data").mkdir()
    assert local_module_names(str(tmp_path)) == {"a", "b", "pkg"}


# ── Icon ───────────────────────────────────────────────────────────────────


def test_png_renamed_to_ico(tmp_path):
    icon = tmp_path / "icon.ico"
    icon.write_bytes(PNG_SIGNATURE + b"\x00" * 20)
    report = run(tmp_path, "print(1)\n", icon=str(icon))
    assert by_code(report, "icon_not_ico").params["icon"] == "icon.ico"


def test_single_size_icon_is_informational(tmp_path):
    icon = tmp_path / "icon.ico"
    icon.write_bytes(pack_ico({32: PNG_SIGNATURE + b"\x00" * 8}))
    report = run(tmp_path, "print(1)\n", icon=str(icon))
    assert by_code(report, "icon_single_size").params["size"] == "32"


def test_multi_size_icon_is_fine(tmp_path):
    icon = tmp_path / "icon.ico"
    icon.write_bytes(pack_ico({16: PNG_SIGNATURE, 32: PNG_SIGNATURE}))
    report = run(tmp_path, "print(1)\n", icon=str(icon))
    assert report.findings == []


# ── 1.4: imports of local helper modules ──────────────────────────────────


def test_missing_package_imported_only_by_a_helper(tmp_path):
    (tmp_path / "helpers.py").write_text("import yaml\n")
    report = run(tmp_path, "import helpers\nprint(helpers)\n",
                 installed=lambda m: m != "yaml")
    assert by_code(report, "missing_package").params["module"] == "yaml"


def test_a_prefetching_checker_is_asked_once(tmp_path):
    asked = []

    class Checker:
        def prefetch(self, modules):
            asked.append(set(modules))

        def __call__(self, module):
            return True

    run(tmp_path, "import yaml\nimport requests\n", installed=Checker())
    assert len(asked) == 1
    assert {"yaml", "requests"} <= asked[0]
