"""Tests for following imports through a project's own modules."""

from py2exe_gui.core.project_scan import project_imports, third_party_imports


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_imports_of_local_helpers_are_included(tmp_path):
    main = write(tmp_path / "main.py", "import helpers\nimport os\n")
    write(tmp_path / "helpers.py", "import yaml\nimport json\n")
    assert project_imports(main) == {"os", "yaml", "json"}
    assert third_party_imports(main) == {"yaml"}


def test_local_packages_are_walked_entirely(tmp_path):
    main = write(tmp_path / "app.py", "from pkg import thing\n")
    write(tmp_path / "pkg" / "__init__.py", "from .sub import x\n")
    write(tmp_path / "pkg" / "sub.py", "import requests\n")
    write(tmp_path / "pkg" / "deep" / "more.py", "import numpy\n")
    # Relative imports name package members, never third-party modules.
    assert third_party_imports(main) == {"requests", "numpy"}


def test_local_names_never_appear_as_imports(tmp_path):
    main = write(tmp_path / "app.py", "import helpers\n")
    write(tmp_path / "helpers.py", "import app\n")  # a cycle, too
    assert project_imports(main) == set()


def test_ignored_folders_are_skipped(tmp_path):
    main = write(tmp_path / "app.py", "import pkg\n")
    write(tmp_path / "pkg" / "__init__.py", "")
    write(tmp_path / "pkg" / "build" / "junk.py", "import should_not_be_seen\n")
    assert project_imports(main) == set()


def test_file_cap_bounds_the_scan(tmp_path):
    main = write(tmp_path / "app.py", "import pkg\n")
    write(tmp_path / "pkg" / "__init__.py", "")
    for i in range(10):
        write(tmp_path / "pkg" / f"m{i:02d}.py", f"import lib{i:02d}\n")
    assert len(project_imports(main, max_files=4)) < 10


def test_unreadable_files_are_tolerated(tmp_path):
    main = write(tmp_path / "app.py", "import helpers\nimport yaml\n")
    (tmp_path / "helpers.py").write_bytes(b"\xff\xfe\x00 not utf-8")
    assert third_party_imports(main) == {"yaml"}
