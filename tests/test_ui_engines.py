"""Headless GUI tests for the engine choice (2.0): selector, build, consent."""

import os
import subprocess

import pytest

pytest.importorskip("PyQt5", reason="PyQt5 not installed")

from PyQt5.QtWidgets import QMessageBox  # noqa: E402

from py2exe_gui.core.config import BuildConfig  # noqa: E402
from py2exe_gui.strings import S, set_locale  # noqa: E402
from tests.test_ui_runtime import FakeThread, enable  # noqa: E402
from tests.test_ui_size import answer, make_source, window  # noqa: E402,F401

pytestmark = pytest.mark.gui

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "nuitka")


@pytest.fixture
def no_build(window, monkeypatch):  # noqa: F811
    monkeypatch.setattr("py2exe_gui.ui.main_window.ConversionThread", FakeThread)
    monkeypatch.setattr("py2exe_gui.ui.main_window.DiagnosticThread", FakeThread)
    monkeypatch.setattr(window, "_ensure_engine", lambda engine, python="": True)
    monkeypatch.setattr(window.tray, "show", lambda: None)
    FakeThread.last = None


def choose(window, name):  # noqa: F811
    window.main_tab.set_engine(name)
    window.run_doctor()


def test_the_selector_lists_every_engine_pyinstaller_first(window):  # noqa: F811
    combo = window.main_tab.engine_combo
    assert [combo.itemData(i) for i in range(combo.count())] == ["pyinstaller", "nuitka"]
    assert window.main_tab.engine_name() == "pyinstaller"
    assert window._current_config().engine == "pyinstaller"


def test_choosing_nuitka_explains_it_honestly(window):  # noqa: F811
    choose(window, "nuitka")
    assert window._current_config().engine == "nuitka"
    assert window.main_tab.engine_desc.text() == S.ENGINE_SHORT_NUITKA
    # The full, careful wording is one hover away — and promises nothing.
    assert S.ENGINE_DESC_NUITKA in window.main_tab.engine_desc.toolTip()
    from py2exe_gui.strings import Ar, En

    assert "not impossible" in En.ENGINE_DESC_NUITKA and "لا يمنعه" in Ar.ENGINE_DESC_NUITKA
    assert "not impossible" in En.ENGINE_SHORT_NUITKA


def test_unsupported_features_are_named_before_building(window, tmp_path):  # noqa: F811
    window.main_tab.source_input.setText(make_source(tmp_path, "print(1)\n"))
    enable(window, "log_redirect")
    choose(window, "nuitka")
    status = window.main_tab.engine_status.text()
    assert S.FEATURE_RUNTIME_KIT in status
    assert not window.main_tab.engine_status.isHidden()
    choose(window, "pyinstaller")
    assert window.main_tab.engine_status.isHidden()


def test_the_engine_survives_a_language_switch(window):  # noqa: F811
    choose(window, "nuitka")
    window.retranslate("en")
    assert window.main_tab.engine_name() == "nuitka"
    assert window.main_tab.engine_desc.text() == S.ENGINE_SHORT_NUITKA


def test_the_engine_round_trips_through_the_project(window):  # noqa: F811
    project = window._current_project()
    project.build.engine = "nuitka"
    window._apply_project(project)
    assert window.main_tab.engine_name() == "nuitka"
    assert window._current_project().build.engine == "nuitka"


def test_a_nuitka_build_runs_nuitka(window, tmp_path, no_build):  # noqa: F811
    window.main_tab.source_input.setText(make_source(tmp_path, "print(1)\n"))
    window.version_info_tab.vi_company_name.setText("Me")
    choose(window, "nuitka")
    window.start_conversion()
    cmd = FakeThread.last.args[0]
    assert cmd[1:3] == ["-m", "nuitka"]
    # Version Info reaches Nuitka as options on Windows, never as a file.
    assert "--version-file" not in " ".join(cmd)
    assert "--assume-yes-for-downloads" not in cmd
    kwargs = FakeThread.last.kwargs
    assert kwargs["popen_kwargs"]["stdin"] == subprocess.DEVNULL
    assert kwargs["stages"][1].key == "nuitka_python"
    assert S.LOG_ENGINE_BUILD.format(engine="Nuitka") in window.main_tab.log_text()


def test_a_runtime_kit_build_is_refused_with_nuitka(window, tmp_path, no_build,  # noqa: F811
                                                   monkeypatch):
    window.main_tab.source_input.setText(make_source(tmp_path, "print(1)\n"))
    enable(window, "crash_reporter")
    choose(window, "nuitka")
    warned = []
    answer(monkeypatch, "warning", QMessageBox.Ok, warned)
    window.start_conversion()
    assert FakeThread.last is None
    assert warned and "--runtime-hook" in warned[0]


def test_download_consent_is_asked_then_given_for_one_build(window, tmp_path, no_build,  # noqa: F811
                                                           monkeypatch):
    window.main_tab.source_input.setText(make_source(tmp_path, "print(1)\n"))
    choose(window, "nuitka")
    window.start_conversion()
    with open(os.path.join(DATA, "download_declined.log"), encoding="utf-8") as f:
        window._build_output = f.read().splitlines()
    asked = []
    answer(monkeypatch, "question", QMessageBox.Yes, asked)
    answer(monkeypatch, "critical", QMessageBox.Ok)
    window.on_conversion_finished(False, S.CONV_FAILED_MSG)
    assert asked and "appimagetool" in asked[-1]
    # The rebuild carries the consent; the one after it does not.
    assert "--assume-yes-for-downloads" in FakeThread.last.args[0]
    window.start_conversion()
    assert "--assume-yes-for-downloads" not in FakeThread.last.args[0]


def test_declining_the_download_builds_nothing(window, tmp_path, no_build,  # noqa: F811
                                               monkeypatch):
    window.main_tab.source_input.setText(make_source(tmp_path, "print(1)\n"))
    choose(window, "nuitka")
    window.start_conversion()
    first = FakeThread.last
    with open(os.path.join(DATA, "download_declined.log"), encoding="utf-8") as f:
        window._build_output = f.read().splitlines()
    answer(monkeypatch, "question", QMessageBox.No)
    window.on_conversion_finished(False, S.CONV_FAILED_MSG)
    assert FakeThread.last is first
    assert not window._allow_downloads_once


def test_the_preview_shows_the_nuitka_command(window, tmp_path, monkeypatch):  # noqa: F811
    window.main_tab.source_input.setText(make_source(tmp_path, "print(1)\n"))
    choose(window, "nuitka")
    shown = []
    monkeypatch.setattr("py2exe_gui.ui.main_window.CommandPreviewDialog",
                        lambda cmd, parent=None: shown.append(cmd) or type(
                            "D", (), {"exec_": lambda self: 0})())
    window.preview_command()
    assert shown and shown[0][1:3] == ["-m", "nuitka"]


def test_doctor_lists_nuitka_findings_in_both_languages(window, tmp_path):  # noqa: F811
    window.main_tab.source_input.setText(make_source(tmp_path, "import tkinter\n"))
    choose(window, "nuitka")
    codes = {f.code for f in window._doctor_findings}
    assert "nuitka_plugin_for_package" in codes
    from py2exe_gui.ui.finding_text import finding_title

    for locale in ("ar", "en"):
        set_locale(locale)
        titles = [finding_title(f) for f in window._doctor_findings]
        assert all("{" not in t for t in titles)


def test_config_from_settings_keeps_the_engine(window):  # noqa: F811
    choose(window, "nuitka")
    data = window._current_project().to_settings_dict()
    assert BuildConfig.from_dict(data).engine == "nuitka"
