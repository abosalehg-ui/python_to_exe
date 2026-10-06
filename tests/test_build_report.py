"""Tests for the HTML build report and Windows Sandbox configuration."""

import hashlib
import os
import xml.etree.ElementTree as ET

from py2exe_gui.core.build_report import (
    ReportData,
    options_from_command,
    parse_versions,
    render_html,
    report_path_for,
    sha256_file,
    write_report,
)
from py2exe_gui.core.config import BuildConfig
from py2exe_gui.core.sandbox import (
    SANDBOX_APP_DIR,
    generate_wsb,
    sandbox_available,
    wsb_for_output,
)

LOG = """74 INFO: PyInstaller: 6.22.3, contrib hooks: 2026.8
74 INFO: Python: 3.13.16
76 INFO: Platform: Windows-11-10.0.22631-SP0
"""


def test_parse_versions_from_a_real_log_header():
    assert parse_versions(LOG) == {
        "pyinstaller": "6.22.3", "python": "3.13.16", "platform": "Windows-11-10.0.22631-SP0",
    }
    assert parse_versions("") == {}


def test_sha256_file(tmp_path):
    path = tmp_path / "x.exe"
    path.write_bytes(b"hello")
    assert sha256_file(str(path)) == hashlib.sha256(b"hello").hexdigest()
    assert sha256_file(str(tmp_path)) == ""
    assert sha256_file("") == ""


def test_options_from_command_pairs_values():
    cmd = ["py", "-m", "PyInstaller", "--onefile", "--name", "My App",
           "--hidden-import", "x", "app.py"]
    assert options_from_command(cmd) == ["--onefile", "--name My App", "--hidden-import x"]
    assert options_from_command([]) == []


def test_report_path_sits_beside_dist(tmp_path):
    config = BuildConfig(source=str(tmp_path / "app.py"), output_name="Tool")
    assert report_path_for(config) == os.path.join(str(tmp_path), "Tool-build-report.html")


def sample(**overrides):
    data = ReportData(
        app_name="Tool",
        source="C:\\proj\\app.py",
        output_path="C:\\proj\\dist\\Tool.exe",
        timestamp="2026-10-06 12:00:00",
        output_bytes=30 * 1024 * 1024,
        content_bytes=80 * 1024 * 1024,
        previous_bytes=60 * 1024 * 1024,
        sha256="ab" * 32,
        python_version="3.12.1",
        pyinstaller_version="6.22.3",
        command=["py", "-m", "PyInstaller", "--onefile", "app.py"],
        groups=[("numpy", 40 * 1024 * 1024), ("Your code", 4096)],
        largest_files=[("numpy/core.pyd", 5 * 1024 * 1024)],
        findings=[("warning", "Title", "Detail")],
    )
    for key, value in overrides.items():
        setattr(data, key, value)
    return data


def test_render_contains_the_essentials():
    page = render_html(sample(), {"title": "Build report", "none": "None"})
    assert page.startswith("<!doctype html>")
    assert 'dir="ltr"' in page
    for text in ("Tool", "30.0 MB", "80.0 MB", "-50.0%", "ab" * 32, "6.22.3",
                 "numpy", "numpy/core.pyd", "Title", "--onefile"):
        assert text in page, text
    # Self-contained: no scripts, no external resources.
    assert "<script" not in page and "http" not in page.split("<style>")[0]


def test_render_rtl_and_language():
    page = render_html(sample(), {}, rtl=True, lang="ar")
    assert 'dir="rtl"' in page and 'lang="ar"' in page


def test_every_value_is_escaped():
    evil = '<img src=x onerror="alert(1)">'
    page = render_html(
        sample(app_name=evil, source=evil, groups=[(evil, 10)],
               findings=[("error", evil, evil)], command=["PyInstaller", evil]),
        {"title": evil},
    )
    assert "<img" not in page
    assert "&lt;img" in page


def test_empty_sections_say_none():
    page = render_html(sample(groups=[], largest_files=[], findings=[], command=[]),
                       {"none": "NOTHING"})
    # breakdown, largest files, findings, Runtime Kit, options
    assert page.count("NOTHING") == 5


def test_runtime_kit_services_are_listed_and_escaped():
    page = render_html(
        sample(runtime_services=["Crash reporter", "<b>x</b>"]),
        {"runtime_kit": "Runtime Kit", "none": "NOTHING"},
    )
    assert "<h2>Runtime Kit</h2>" in page
    assert "<li>Crash reporter</li>" in page
    assert "&lt;b&gt;x&lt;/b&gt;" in page and "<b>x</b>" not in page


def test_write_report(tmp_path):
    path = str(tmp_path / "r.html")
    assert write_report(path, "<html></html>") is None
    assert open(path, encoding="utf-8").read() == "<html></html>"
    assert write_report(str(tmp_path / "missing" / "r.html"), "x")


# ── Windows Sandbox ────────────────────────────────────────────────────────


def test_wsb_is_valid_xml_with_a_read_only_mapping():
    xml = generate_wsb("C:\\Users\\me\\proj & co\\dist", "Tool.exe")
    root = ET.fromstring(xml)
    folder = root.find("MappedFolders/MappedFolder")
    assert folder.find("HostFolder").text == "C:\\Users\\me\\proj & co\\dist"
    assert folder.find("SandboxFolder").text == SANDBOX_APP_DIR
    assert folder.find("ReadOnly").text == "true"
    assert root.find("LogonCommand/Command").text == f'"{SANDBOX_APP_DIR}\\Tool.exe"'
    assert root.find("Networking").text == "Default"
    assert ET.fromstring(generate_wsb("C:\\d", "a.exe", networking=False)).find(
        "Networking").text == "Disable"


def test_wsb_for_onefile_and_folder_builds():
    exe = os.path.join("p", "dist", "Tool.exe")
    assert wsb_for_output(exe, True) == (os.path.join("p", "dist"), "Tool.exe")
    host, exe = wsb_for_output(os.path.join("p", "dist", "Tool"), False)
    assert host.endswith("Tool") and exe == "Tool.exe"


def test_sandbox_availability(tmp_path):
    assert sandbox_available(platform="linux") is False
    system32 = tmp_path / "System32"
    system32.mkdir()
    env = {"SystemRoot": str(tmp_path)}
    assert sandbox_available(platform="win32", env=env) is False
    (system32 / "WindowsSandbox.exe").write_text("")
    assert sandbox_available(platform="win32", env=env) is True
