"""Headless GUI tests for projects (p2e.toml) in the window."""

import json
import os

import pytest

pytest.importorskip("PyQt5", reason="PyQt5 not installed")

from PyQt5.QtCore import QMimeData, QPointF, Qt, QUrl  # noqa: E402
from PyQt5.QtGui import QDropEvent  # noqa: E402
from PyQt5.QtWidgets import QFileDialog, QMessageBox  # noqa: E402

from py2exe_gui.core.project_file import (  # noqa: E402
    ProjectConfig,
    load_project,
    save_project,
)
from py2exe_gui.strings import Ar, En, set_locale  # noqa: E402
from tests.conftest import MemoryKeyring  # noqa: E402

pytestmark = pytest.mark.gui


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr("py2exe_gui.ui.main_window.SETTINGS_FILE", str(tmp_path / "s.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.HISTORY_FILE", str(tmp_path / "h.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.PRESETS_FILE", str(tmp_path / "p.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.ENVS_ROOT", str(tmp_path / "envs"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.SIGNING_KEY_FILE",
                        str(tmp_path / "signing" / "k.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.KEYRING", MemoryKeyring())
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


@pytest.fixture
def script(tmp_path):
    folder = tmp_path / "proj"
    folder.mkdir()
    path = folder / "tool.py"
    path.write_text("print('hi')\n")
    return path


def full_project(script) -> ProjectConfig:
    folder = os.path.dirname(str(script))
    p = ProjectConfig(name="أداتي", version="2.1.0")
    p.build.source = str(script)
    p.build.output_name = "Tool"
    p.build.onefile = False
    p.build.hidden_imports = ["yaml"]
    p.build.extra_files = [os.path.join(folder, "data")]
    p.build.isolated_env = True
    p.build.runtime_kit.crash_reporter = True
    p.version_info.company_name = "شركة"
    p.version_info.product_version = "2.1.0.0"
    p.manifest.enabled = True
    p.manifest.supported_os = ["10", "11"]
    p.installer.enabled = True
    p.installer.app_name = "Tool"
    p.installer.app_version = "2.1.0"
    p.installer.languages = ["ar", "en"]
    p.installer.architecture = "x86"
    p.signing.enabled = True
    p.signing.cert_path = os.path.join(folder, "me.pfx")
    p.release.repository = "me/tool"
    p.release.prerelease = True
    p.release.assets.portable_zip = False
    p.release.winget.enabled = True
    p.release.winget.identifier = "Me.Tool"
    return p


def settle(window):
    window._update_modified()


# ── Menu, tab, title ──────────────────────────────────────────────────────


def test_project_menu_and_release_tab(window):
    menus = [a.text() for a in window.menuBar().actions()]
    assert Ar.MENU_PROJECT in menus
    texts = [a.text().split("\t")[0] for a in window.menuBar().actions()[0].menu().actions()
             if a.text()]
    for key in ("MENU_NEW_PROJECT", "MENU_OPEN_PROJECT", "MENU_SAVE_PROJECT",
                "MENU_SAVE_PROJECT_AS", "MENU_INIT_PROJECT"):
        assert getattr(Ar, key) in texts
    shown = [window.tabs.tabText(i) for i in range(window.tabs.count())]
    assert Ar.TAB_RELEASE in shown
    window.retranslate("en")
    assert En.MENU_PROJECT in [a.text() for a in window.menuBar().actions()]
    assert En.TAB_RELEASE in [window.tabs.tabText(i) for i in range(window.tabs.count())]


def test_title_shows_project_and_unsaved_marker(window, script, tmp_path, monkeypatch):
    assert "[*]" not in window.windowTitle() and "Python to EXE" in window.windowTitle()
    path = str(script.parent / "p2e.toml")
    save_project(full_project(script), path)
    answer(monkeypatch, "question", QMessageBox.Yes)
    assert window.open_project_path(path)
    assert window.windowTitle().startswith("أداتي[*]")
    assert not window.isWindowModified()
    window.main_tab.output_name.setText("Changed")
    settle(window)
    assert window.isWindowModified() and window.is_project_modified()
    assert window.save_project()
    assert not window.isWindowModified()
    assert load_project(path).project.build.output_name == "Changed"


# ── Save / open / new ─────────────────────────────────────────────────────


def test_save_as_then_open_round_trips_every_tab(window, script, monkeypatch):
    project = full_project(script)
    window._apply_project(project)
    window.deploy_tab.signing_password.setText("pfx-secret-1")
    target = str(script.parent / "p2e.toml")
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (target, "")))
    assert window.save_project_as()
    text = open(target, encoding="utf-8").read()
    assert "pfx-secret-1" not in text and 'source = "tool.py"' in text
    assert window.project_path == target

    window.new_project()
    assert window.main_tab.source_input.text() == ""
    assert window.project_path == ""
    answer(monkeypatch, "question", QMessageBox.Yes)  # the dangerous-settings check
    assert window.open_project_path(target)
    restored = window._current_project()
    expected = load_project(target).project
    assert restored == expected
    assert restored.installer.languages == ["ar", "en"]
    assert restored.installer.architecture == "x86"
    assert restored.manifest.supported_os == ["10", "11"]
    assert window.size_tab.isolated_radio.isChecked()
    # The password stays in memory only.
    assert window.deploy_tab.signing_password.text() == "pfx-secret-1"


def test_ctrl_s_saves_the_open_project(window, script, monkeypatch):
    path = str(script.parent / "p2e.toml")
    save_project(full_project(script), path)
    answer(monkeypatch, "question", QMessageBox.Yes)
    window.open_project_path(path)
    window.advanced_tab.hidden_imports_list.addItem("requests")
    window.save_shortcut()
    assert "requests" in load_project(path).project.build.hidden_imports


def test_ctrl_s_without_a_project_saves_a_settings_file(window, tmp_path, monkeypatch):
    target = str(tmp_path / "settings.json")
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (target, "")))
    answer(monkeypatch, "information", QMessageBox.Ok)
    window.save_shortcut()
    data = json.load(open(target, encoding="utf-8"))
    assert "source" in data and "installer" in data and "signing" in data


# ── Untrusted content ─────────────────────────────────────────────────────


def test_opening_a_project_with_dangerous_flags_asks_first(window, script, monkeypatch):
    project = full_project(script)
    project.build.extra_args = "--runtime-hook evil.py"
    path = str(script.parent / "p2e.toml")
    save_project(project, path)
    asked = []
    answer(monkeypatch, "question", QMessageBox.No, asked)
    assert not window.open_project_path(path)
    assert "--runtime-hook" in asked[0]
    assert window.project_path == "" and window.main_tab.source_input.text() == ""
    answer(monkeypatch, "question", QMessageBox.Yes)
    assert window.open_project_path(path)
    assert window.advanced_tab.extra_args.text() == "--runtime-hook evil.py"


def test_upx_dir_from_a_shared_file_asks_first(window, script, monkeypatch):
    project = full_project(script)
    project.build.upx = True
    project.build.upx_dir = "/tmp/someone-elses-upx"
    path = str(script.parent / "p2e.toml")
    save_project(project, path)
    asked = []
    answer(monkeypatch, "question", QMessageBox.No, asked)
    assert not window.open_project_path(path)
    assert "--upx-dir" in asked[0] and "/tmp/someone-elses-upx" in asked[0]


@pytest.mark.parametrize("snippet,word", [
    ('[signing]\ncert_password = "hunter2"\n', "signing.cert_password"),
    ('[build]\npython = "/evil/python"\n', "build.python"),
    ('[release]\nrepository = "ghp_' + "a" * 36 + '"\n', "release.repository"),
])
def test_projects_with_secrets_or_interpreters_are_refused(window, tmp_path, monkeypatch,
                                                           snippet, word):
    path = tmp_path / "p2e.toml"
    path.write_text("schema = 1\n" + snippet)
    shown = []
    answer(monkeypatch, "critical", QMessageBox.Ok, shown)
    assert not window.open_project_path(str(path))
    assert shown and word in shown[0]
    assert "hunter2" not in shown[0] and "ghp_" not in shown[0]
    assert window.project_path == ""


def test_newer_schema_is_explained(window, tmp_path, monkeypatch):
    path = tmp_path / "p2e.toml"
    path.write_text("schema = 99\n")
    shown = []
    answer(monkeypatch, "critical", QMessageBox.Ok, shown)
    assert not window.open_project_path(str(path))
    assert "99" in shown[0]


# ── Recent projects, drop, init ───────────────────────────────────────────


def test_recent_projects_live_in_the_settings(window, script, tmp_path, monkeypatch):
    path = str(script.parent / "p2e.toml")
    save_project(full_project(script), path)
    answer(monkeypatch, "question", QMessageBox.Yes)
    window.open_project_path(path)
    assert window.recent_projects()[0] == path
    data = json.load(open(tmp_path / "s.json", encoding="utf-8"))
    assert data["recent_projects"] == [path]
    assert [a.text() for a in window.recent_menu.actions()] == [path]
    os.remove(path)
    answer(monkeypatch, "critical", QMessageBox.Ok)
    assert not window.open_project_path(path)
    assert window.recent_projects() == []
    assert not window.recent_menu.actions()[0].isEnabled()  # "no recent projects"


def test_recent_list_is_bounded_and_deduplicated(window, tmp_path):
    for i in range(12):
        window._remember_project(str(tmp_path / f"p{i}" / "p2e.toml"))
    window._remember_project(str(tmp_path / "p3" / "p2e.toml"))
    recent = window.recent_projects()
    assert len(recent) == 8 and recent[0].endswith(os.path.join("p3", "p2e.toml"))
    assert len(set(recent)) == 8


def test_dropping_a_project_file_opens_it(window, script, monkeypatch):
    path = str(script.parent / "p2e.toml")
    save_project(full_project(script), path)
    answer(monkeypatch, "question", QMessageBox.Yes)
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(path)])
    event = QDropEvent(QPointF(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    window.dropEvent(event)
    assert window.project_path == path
    assert window.main_tab.output_name.text() == "Tool"


def test_init_project_from_this_script(window, script, monkeypatch):
    window.main_tab.source_input.setText(str(script))
    window.advanced_tab.hidden_imports_list.addItem("yaml")
    window.release_tab.version_input.setText("0.4.0")
    window.init_project_from_script()
    path = script.parent / "p2e.toml"
    assert path.is_file() and window.project_path == str(path)
    project = load_project(str(path)).project
    assert project.build.hidden_imports == ["yaml"]
    assert project.version == "0.4.0" and project.installer.app_version == "0.4.0"
    assert project.version_info.file_version == "0.4.0.0"
    assert window.version_info_tab.vi_product_version.text() == "0.4.0.0"
    # A second init asks before replacing the file.
    asked = []
    answer(monkeypatch, "question", QMessageBox.No, asked)
    window.init_project_from_script()
    assert asked


def test_init_without_a_script_warns(window, monkeypatch):
    shown = []
    answer(monkeypatch, "warning", QMessageBox.Ok, shown)
    window.init_project_from_script()
    assert shown


# ── Single model: presets, history, JSON, language switch ─────────────────


def test_a_legacy_preset_leaves_the_other_tabs_alone(window, monkeypatch):
    window.installer_tab.inst_app_name.setText("Keep me")
    window.presets.put("old", {"source": "/x/app.py", "output_name": "Legacy"})
    window._refresh_presets_list()
    combo = window.templates_tab.presets_combo
    combo.setCurrentIndex(combo.findData("old"))
    window.apply_selected_preset()
    assert window.main_tab.output_name.text() == "Legacy"
    assert window.installer_tab.inst_app_name.text() == "Keep me"


def test_a_new_preset_carries_every_section(window, script):
    window._apply_project(full_project(script))
    window.presets.put("full", window._current_project().to_settings_dict())
    window.new_project()
    window._refresh_presets_list()
    combo = window.templates_tab.presets_combo
    combo.setCurrentIndex(combo.findData("full"))
    window.apply_selected_preset()
    assert window.installer_tab.inst_app_name.text() == "Tool"
    assert window.release_tab.repository.text() == "me/tool"
    assert window.release_tab.version_input.text() == "2.1.0"


def test_language_switch_keeps_installer_signing_and_release(window, script):
    window._apply_project(full_project(script))
    window.deploy_tab.signing_password.setText("in-memory")
    window.release_tab.notes_edit.setPlainText("ملاحظات")
    before = window._current_project()
    window.retranslate("en")
    assert window._current_project() == before
    assert window.deploy_tab.signing_password.text() == "in-memory"
    assert window.release_tab.notes_edit.toPlainText() == "ملاحظات"
    set_locale("ar")


def test_unsaved_changes_prompt(window, script, monkeypatch):
    path = str(script.parent / "p2e.toml")
    save_project(full_project(script), path)
    answer(monkeypatch, "question", QMessageBox.Yes)
    window.open_project_path(path)
    window.show()
    window.main_tab.output_name.setText("Edited")
    answer(monkeypatch, "question", QMessageBox.Cancel)
    window.new_project()
    assert window.project_path == path  # cancelled
    answer(monkeypatch, "question", QMessageBox.Discard)
    window.new_project()
    assert window.project_path == ""
    assert load_project(path).project.build.output_name == "Tool"  # not saved
