"""Headless GUI tests for the Size & Environment tab and its wiring."""

import os
import subprocess
import sys

import pytest

pytest.importorskip("PyQt5", reason="PyQt5 not installed")

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtWidgets import QMessageBox  # noqa: E402

from py2exe_gui.core import BuildConfig  # noqa: E402
from py2exe_gui.core.venv_manager import env_dir_for, env_python  # noqa: E402
from py2exe_gui.strings import En, S, set_locale  # noqa: E402
from py2exe_gui.ui.main_window import SIMPLE_MODE_TABS  # noqa: E402
from tests.test_size_analyzer import make_build  # noqa: E402

pytestmark = pytest.mark.gui


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr("py2exe_gui.ui.main_window.SETTINGS_FILE", str(tmp_path / "s.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.HISTORY_FILE", str(tmp_path / "h.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.PRESETS_FILE", str(tmp_path / "p.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.ENVS_ROOT", str(tmp_path / "envs"))
    from py2exe_gui.ui.main_window import MainWindow

    win = MainWindow()
    yield win
    win.close()


def answer(monkeypatch, kind, reply, record=None):
    def fake(*args, **_kwargs):
        if record is not None:
            record.append(args[2] if len(args) > 2 else "")
        return reply

    monkeypatch.setattr(QMessageBox, kind, staticmethod(fake))


def make_source(tmp_path, code="import yaml\n"):
    folder = tmp_path / "proj"
    folder.mkdir(exist_ok=True)
    path = folder / "app.py"
    path.write_text(code)
    return str(path)


def fake_env(window, source, real_python=False):
    """An environment folder for ``source``; its python may be the real one."""
    from py2exe_gui.ui import main_window

    env = env_dir_for(source, main_window.ENVS_ROOT)
    python = env_python(env)
    os.makedirs(os.path.dirname(python), exist_ok=True)
    with open(os.path.join(env, "pyvenv.cfg"), "w") as f:
        f.write("version = 3.12.1\n")
    if real_python:
        os.symlink(sys.executable, python)
    else:
        open(python, "w").close()
    return env


def doctor_codes(window):
    return [f.code for f in window._doctor_findings]


# ── Tab and settings ───────────────────────────────────────────────────────


def test_size_tab_is_in_simple_mode(window):
    assert "size" in SIMPLE_MODE_TABS
    shown = [window.tabs.widget(i) for i in range(window.tabs.count())]
    assert window.size_tab in shown


def test_english_tab_title_shows_a_real_ampersand(window):
    window.retranslate("en")
    titles = [window.tabs.tabText(i) for i in range(window.tabs.count())]
    assert En.TAB_SIZE in titles  # "&&" renders as one "&", not a mnemonic


def test_isolated_choice_round_trips_through_the_config(window):
    window.size_tab.isolated_radio.setChecked(True)
    assert window._current_config().isolated_env is True
    window._apply_config(BuildConfig(isolated_env=False))
    assert window.size_tab.current_radio.isChecked()
    window._apply_config(BuildConfig(isolated_env=True))
    assert window.size_tab.isolated_radio.isChecked()


def test_base_python_and_report_choice_live_in_settings(window):
    window.size_tab.base_python.setText("/opt/py/bin/python3 ")
    window.size_tab.report_auto.setChecked(False)
    assert window.settings["base_python"] == "/opt/py/bin/python3"
    assert window.settings["report_auto"] is False


# ── Build interpreter and the doctor ───────────────────────────────────────


def test_build_python_follows_the_choice(window, tmp_path):
    source = make_source(tmp_path)
    assert window.build_python(BuildConfig(source=source)) == sys.executable
    isolated = window.build_python(BuildConfig(source=source, isolated_env=True))
    assert isolated == env_python(window._env_dir(source))


def test_missing_env_is_one_finding_not_every_package(window, tmp_path):
    source = make_source(tmp_path, "import not_installed_anywhere_zz\n")
    window.main_tab.source_input.setText(source)
    window.size_tab.isolated_radio.setChecked(True)
    window.run_doctor()
    codes = doctor_codes(window)
    assert "env_not_created" in codes
    assert "missing_package" not in codes


@pytest.mark.skipif(sys.platform == "win32", reason="symlinked interpreter")
def test_doctor_asks_the_environment_what_it_has(window, tmp_path):
    source = make_source(tmp_path, "import json\nimport not_installed_anywhere_zz\n")
    fake_env(window, source, real_python=True)
    window.main_tab.source_input.setText(source)
    window.size_tab.isolated_radio.setChecked(True)
    window.run_doctor()
    missing = [f.params["module"] for f in window._doctor_findings if f.code == "missing_package"]
    assert missing == ["not_installed_anywhere_zz"]
    assert "env_not_created" not in doctor_codes(window)


def test_env_section_reflects_state(window, tmp_path):
    set_locale("en")
    window.retranslate("en")
    source = make_source(tmp_path)
    window.main_tab.source_input.setText(source)
    window.run_doctor()
    tab = window.size_tab
    assert tab.env_status.text() == En.ENV_STATUS_NONE
    assert "PyYAML" in tab.env_requirements.text()
    assert tab.env_create_btn.isEnabled() and not tab.env_delete_btn.isEnabled()

    fake_env(window, source)
    window.refresh_env_view()
    assert "3.12.1" in tab.env_status.text()
    assert tab.env_delete_btn.isEnabled()


# ── Creating, deleting, locking ────────────────────────────────────────────


class FakeEnvThread:
    instances = []

    def __init__(self, plan, base_python=""):
        self.plan = plan
        self.started = False
        self.log_signal = self.finished_signal = self
        FakeEnvThread.instances.append(self)

    def connect(self, _slot):
        pass

    def start(self):
        self.started = True

    def isRunning(self):
        return False


def test_create_env_asks_first_and_shows_the_commands(window, tmp_path, monkeypatch):
    monkeypatch.setattr("py2exe_gui.ui.main_window.EnvThread", FakeEnvThread)
    monkeypatch.setattr("py2exe_gui.ui.main_window.find_uv", lambda: "")
    window.main_tab.source_input.setText(make_source(tmp_path))
    asked = []
    answer(monkeypatch, "question", QMessageBox.No, asked)
    window.create_build_env()
    assert window.env_thread is None
    assert "venv" in asked[0] and "PyYAML" in asked[0]

    answer(monkeypatch, "question", QMessageBox.Yes)
    window.create_build_env()
    assert window.env_thread.started
    assert window.env_thread.plan.install[-1] == "PyYAML"


def test_create_env_rejects_a_missing_base_python(window, tmp_path, monkeypatch):
    window.main_tab.source_input.setText(make_source(tmp_path))
    window.size_tab.base_python.setText(str(tmp_path / "no-python"))
    warned = []
    answer(monkeypatch, "warning", QMessageBox.Ok, warned)
    window.create_build_env()
    assert warned and window.env_thread is None


def test_env_finished_then_builds(window, tmp_path, monkeypatch):
    window.main_tab.source_input.setText(make_source(tmp_path))
    started = []
    monkeypatch.setattr(window, "start_conversion", lambda: started.append(True))
    plan = type("P", (), {"python": "x"})()
    window._on_env_finished(plan, True, [], "", then_build=True)
    assert started == [True]
    assert window.convert_btn.isEnabled()


def test_env_failure_is_reported(window, tmp_path, monkeypatch):
    window.main_tab.source_input.setText(make_source(tmp_path))
    shown = []
    answer(monkeypatch, "critical", QMessageBox.Ok, shown)
    started = []
    monkeypatch.setattr(window, "start_conversion", lambda: started.append(True))
    window._on_env_finished(type("P", (), {"python": "x"})(), False, [], "boom", True)
    assert "boom" in shown[0]
    assert started == []


def test_partial_install_names_the_failures(window, tmp_path):
    window.main_tab.source_input.setText(make_source(tmp_path))
    window._on_env_finished(type("P", (), {"python": "x"})(), True, ["badname"], "", False)
    assert "badname" in window.main_tab.log_text()


def test_delete_env(window, tmp_path, monkeypatch):
    source = make_source(tmp_path)
    env = fake_env(window, source)
    window.main_tab.source_input.setText(source)
    answer(monkeypatch, "question", QMessageBox.Yes)
    window.delete_build_env()
    assert not os.path.exists(env)


def test_save_lock(window, tmp_path, monkeypatch):
    source = make_source(tmp_path)
    fake_env(window, source)
    window.main_tab.source_input.setText(source)
    freeze = "PyYAML==6.0.1\npyinstaller==6.22.3\n"
    monkeypatch.setattr(
        "py2exe_gui.ui.main_window.subprocess.run",
        lambda cmd, **_k: subprocess.CompletedProcess(cmd, 0, stdout=freeze, stderr=""),
    )
    window.save_env_lock()
    lock = os.path.join(os.path.dirname(source), "p2e-build.lock")
    content = open(lock).read()
    assert "PyYAML==6.0.1" in content and "pyinstaller" not in content


def test_start_with_missing_env_offers_to_create_it(window, tmp_path, monkeypatch):
    window.main_tab.source_input.setText(make_source(tmp_path))
    window.size_tab.isolated_radio.setChecked(True)
    calls = []
    monkeypatch.setattr(window, "create_build_env", lambda **kw: calls.append(kw))
    answer(monkeypatch, "question", QMessageBox.Yes)
    window.start_conversion()
    assert calls == [{"then_build": True}]
    assert window.conversion_thread is None


# ── Size lab ───────────────────────────────────────────────────────────────


def point_at_build(window, config):
    window.main_tab.source_input.setText(config.source)
    window.main_tab.onefile_check.setChecked(config.onefile)


def test_analyze_shows_breakdown_and_suggestions(window, tmp_path):
    config = make_build(tmp_path)
    point_at_build(window, config)
    window.analyze_last_build()
    tab = window.size_tab
    names = [tab.breakdown.topLevelItem(i).text(0) for i in range(tab.breakdown.topLevelItemCount())]
    assert names[0] == "numpy"
    assert S.SIZE_GROUP_RUNTIME in names
    suggestion = tab.suggestions.item(0).data(Qt.UserRole)
    assert suggestion.params["package"] == "tkinter"


def test_applying_a_suggestion_excludes_it(window, tmp_path):
    point_at_build(window, make_build(tmp_path))
    window.analyze_last_build()
    window.size_tab._apply(rebuild=False)
    assert "--exclude-module tkinter" in window.advanced_tab.extra_args.text()
    assert window.size_tab.suggestions.item(0).data(Qt.UserRole) is None  # list emptied


def test_size_hints_follow_the_language(window, tmp_path):
    point_at_build(window, make_build(tmp_path))
    window.analyze_last_build()
    window.retranslate("en")
    assert "isolated environment" in window.size_tab.size_hints.text()


def test_no_build_clears_the_lab(window, tmp_path):
    window.main_tab.source_input.setText(make_source(tmp_path))
    window.analyze_last_build()
    assert window.size_tab.size_summary.text() == S.SIZE_NONE


def test_successful_build_records_size_and_writes_report(window, tmp_path):
    config = make_build(tmp_path)
    point_at_build(window, config)
    window._build_output = ["74 INFO: PyInstaller: 6.22.3, contrib hooks: x",
                            "74 INFO: Python: 3.12.1"]
    from py2exe_gui.core.size_analyzer import analyze_build

    report = analyze_build(config)
    window._show_size(config, report, 0)
    window._write_build_report(config, report, 0, 12.5, True)
    path = window._last_report_path
    assert os.path.isfile(path)
    page = open(path, encoding="utf-8").read()
    assert "6.22.3" in page and "numpy" in page
    assert window.size_tab.report_open_btn.isEnabled()


def test_finished_build_stores_size_in_history(window, tmp_path, monkeypatch):
    config = make_build(tmp_path)
    point_at_build(window, config)
    window._build_config_snapshot = config.to_dict()
    answer(monkeypatch, "information", QMessageBox.Ok)
    monkeypatch.setattr(window, "_run_post_build_actions", lambda _c: None)
    window.on_conversion_finished(True, "ok")
    assert window.history.records[0].size_bytes == 6 * 1024 * 1024
    assert os.path.isfile(window._last_report_path)


def test_report_can_be_turned_off(window, tmp_path, monkeypatch):
    config = make_build(tmp_path)
    point_at_build(window, config)
    window.size_tab.report_auto.setChecked(False)
    window._build_config_snapshot = config.to_dict()
    answer(monkeypatch, "information", QMessageBox.Ok)
    monkeypatch.setattr(window, "_run_post_build_actions", lambda _c: None)
    window.on_conversion_finished(True, "ok")
    assert window._last_report_path == ""


# ── Windows Sandbox ────────────────────────────────────────────────────────


def test_sandbox_needs_a_build(window, tmp_path, monkeypatch):
    window.main_tab.source_input.setText(make_source(tmp_path))
    shown = []
    answer(monkeypatch, "information", QMessageBox.Ok, shown)
    window.open_in_sandbox()
    assert shown == [S.MSG_SANDBOX_NO_BUILD]


def test_sandbox_unavailable_explains_the_alternative(window, tmp_path, monkeypatch):
    point_at_build(window, make_build(tmp_path))
    monkeypatch.setattr("py2exe_gui.ui.main_window.sandbox_available", lambda: False)
    shown = []
    answer(monkeypatch, "information", QMessageBox.Ok, shown)
    window.open_in_sandbox()
    assert os.path.join("dist", "app") in shown[0]


def test_sandbox_writes_and_opens_a_wsb(window, tmp_path, monkeypatch):
    config = make_build(tmp_path)
    point_at_build(window, config)
    opened = []
    monkeypatch.setattr("py2exe_gui.ui.main_window.sandbox_available", lambda: True)
    monkeypatch.setattr("py2exe_gui.ui.main_window.os.startfile", opened.append, raising=False)
    window.open_in_sandbox()
    assert opened and opened[0].endswith("app.wsb")
    assert "<ReadOnly>true</ReadOnly>" in open(opened[0]).read()
