"""AST-aware dependency analyzer tests (Phase 4)."""

from py2exe_gui.core.dependency_analyzer import (
    detect_imports,
    parse_requirements,
)


def test_handles_multiline_import():
    code = "from os import (\n    path,\n    sep,\n)\n"
    assert "os" in detect_imports(code)


def test_falls_back_on_syntax_error():
    code = "import numpy\nthis is not valid python ::: %%%\n"
    # Line-based fallback still grabs the first import.
    assert "numpy" in detect_imports(code)


def test_skips_relative_imports():
    code = "from . import sibling\nfrom .. import parent\n"
    # Relative imports have no resolvable top-level name.
    result = detect_imports(code)
    assert "sibling" not in result
    assert "parent" not in result


def test_detects_dynamic_double_underscore_import():
    code = "mod = __import__('requests')\n"
    assert "requests" in detect_imports(code)


def test_detects_importlib_import_module():
    code = "import importlib\nm = importlib.import_module('django.urls')\n"
    result = detect_imports(code)
    assert "importlib" in result
    assert "django" in result


def test_ignores_non_string_dynamic_imports():
    code = "name = 'requests'\nmod = __import__(name)\n"
    # We don't follow variables — just literal strings.
    assert "requests" not in detect_imports(code)


def test_indented_import_inside_function():
    code = "def setup():\n    import psycopg2\n    return psycopg2\n"
    assert "psycopg2" in detect_imports(code)


def test_dotted_import_returns_top_level_via_ast():
    code = "import google.cloud.storage\n"
    result = detect_imports(code)
    assert "google" in result
    assert "cloud" not in result


def test_conditional_import():
    code = """
try:
    import lxml
except ImportError:
    import xml.etree.ElementTree as ET
"""
    result = detect_imports(code)
    assert "lxml" in result
    assert "xml" in result


# requirements.txt parsing


def test_parses_basic_requirements():
    content = "flask\nrequests==2.31.0\npandas>=1.0\n"
    result = parse_requirements(content)
    assert result == {"flask", "requests", "pandas"}


def test_skips_comments_and_blanks():
    content = "# A comment\n\nflask\n\n# Another\nrequests\n"
    assert parse_requirements(content) == {"flask", "requests"}


def test_skips_pip_options():
    content = "-r other.txt\n--index-url https://example.com\nflask\n"
    assert parse_requirements(content) == {"flask"}


def test_skips_vcs_urls():
    content = "git+https://github.com/user/repo.git\nflask\n"
    assert parse_requirements(content) == {"flask"}


def test_handles_extras_and_markers():
    content = 'requests[security]>=2.0; python_version>="3.8"\n'
    assert "requests" in parse_requirements(content)


def test_normalizes_dashes_to_underscores():
    content = "python-dateutil\nscikit-learn\n"
    result = parse_requirements(content)
    assert "python_dateutil" in result
    assert "scikit_learn" in result


def test_handles_direct_reference_skipped():
    content = "flask\nrequests @ https://example.com/req.tar.gz\n"
    # Direct references are skipped as the package name is unreliable.
    assert parse_requirements(content) == {"flask"}
