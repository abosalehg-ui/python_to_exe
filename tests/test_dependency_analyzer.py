"""Tests for dependency_analyzer."""

from py2exe_gui.core.dependency_analyzer import detect_imports, filter_non_stdlib


def test_detects_simple_import():
    assert "numpy" in detect_imports("import numpy")


def test_detects_dotted_import_returns_top_level():
    result = detect_imports("import PyQt5.QtWidgets")
    assert "PyQt5" in result
    assert "QtWidgets" not in result


def test_detects_aliased_import():
    result = detect_imports("import numpy as np")
    assert "numpy" in result
    assert "np" not in result


def test_detects_multiple_comma_separated_imports():
    result = detect_imports("import os, sys, json")
    assert {"os", "sys", "json"}.issubset(result)


def test_detects_from_import():
    result = detect_imports("from flask import Flask")
    assert "flask" in result
    assert "Flask" not in result


def test_detects_from_dotted_import():
    result = detect_imports("from PyQt5.QtWidgets import QPushButton")
    assert "PyQt5" in result


def test_ignores_non_import_lines():
    code = """
print('hello')
x = 42
# import this
"""
    result = detect_imports(code)
    assert "this" not in result


def test_empty_source_returns_empty_set():
    assert detect_imports("") == set()


def test_combined_imports():
    code = """
import os
import sys
from pathlib import Path
import numpy as np
from PyQt5.QtCore import Qt
"""
    result = detect_imports(code)
    assert {"os", "sys", "pathlib", "numpy", "PyQt5"}.issubset(result)


def test_filter_non_stdlib_removes_stdlib():
    result = filter_non_stdlib({"os", "sys", "numpy", "pandas"})
    assert "os" not in result
    assert "sys" not in result
    assert "numpy" in result
    assert "pandas" in result


def test_filter_non_stdlib_removes_existing():
    result = filter_non_stdlib({"numpy", "pandas"}, existing=["pandas"])
    assert "numpy" in result
    assert "pandas" not in result


def test_filter_non_stdlib_custom_stdlib():
    result = filter_non_stdlib({"foo", "bar"}, stdlib={"foo"})
    assert result == {"bar"}
