"""Headless GUI tests for the Platforms tab: the packaging and CI sections of
the project, the workflow preview dialog, and packaging from the window."""

import os
import shutil
import subprocess
import sys

import pytest

pytest.importorskip("py2exe_gui.qt", reason="no Qt binding (PySide6/PyQt5) installed")

from py2exe_gui.core import packagers  # noqa: E402
from py2exe_gui.core.ci_generator import DEFAULT_TOOL_REQUIREMENT, workflow_path  # noqa: E402
from py2exe_gui.core.packagers import AppImagePackager  # noqa: E402
from py2exe_gui.core.project_file import ProjectConfig, load_project, save_project  # noqa: E402
from py2exe_gui.qt import QDialog, QMessageBox  # noqa: E402
from py2exe_gui.strings import Ar, En, set_locale  # noqa: E402
from py2exe_gui.ui.dialogs import CiPreviewDialog  # noqa: E402
from tests.conftest import MemoryKeyring  # noqa: E402
from tests.test_ui_release import answer, plain  # noqa: E402

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
    if win.package_thread is not None:
        win.package_thread.wait(60000)
    win.close()


@pytest.fixture
def project_dir(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "app.py").write_text("print('hello')\n")
    project = ProjectConfig(name="Hello App", version="1.2.3")
    project.build.source = str(root / "app.py")
    project.build.output_name = "hello"
    project.packaging.deb = True
    project.packaging.maintainer = "Me <me@example.com>"
    project.ci.python_version = "3.11"
    project.ci.allow_doctor_errors = True
    save_project(project, str(root / "p2e.toml"))
    return root


def open_project(window, root, monkeypatch=None):
    if monkeypatch is not None:
        answer(monkeypatch, "question", QMessageBox.StandardButton.Yes)
    assert window.open_project_path(str(root / "p2e.toml"))


def wait_packages(qapp, window):
    thread = window.package_thread
    if thread is not None:
        assert thread.wait(120000)
    qapp.processEvents()


# ── The tab holds the two sections ────────────────────────────────────────


def test_tab_is_registered_in_the_distribute_section(window):
    assert window.section_of(window.platforms_tab) == "distribute"
    assert window.section_of(window.release_tab) == "distribute"
    assert window.platforms_tab in window._project_tabs


def test_sections_round_trip_through_the_tab(window, project_dir):
    open_project(window, project_dir)
    tab = window.platforms_tab
    assert tab.format_checks["deb"].isChecked() and not tab.format_checks["dmg"].isChecked()
    assert tab.maintainer.text() == "Me <me@example.com>"
    assert tab.ci_python.text() == "3.11" and tab.ci_allow_doctor_errors.isChecked()
    assert tab.ci_tool.text() == DEFAULT_TOOL_REQUIREMENT
    tab.format_checks["appimage"].setChecked(True)
    tab.homepage.setText("https://example.com")
    tab.identifier.setText("com.example.hello")
    tab.deb_depends.setText("libc6")
    tab.ci_sign_windows.setChecked(True)
    tab.ci_python.setText("3.12")
    project = window._current_project()
    assert project.packaging.enabled_formats() == ["appimage", "deb"]
    assert project.packaging.homepage == "https://example.com"
    assert project.packaging.identifier == "com.example.hello"
    assert project.packaging.deb_depends == "libc6"
    assert project.ci.sign_windows and project.ci.python_version == "3.12"
    window.save_project()
    reloaded = load_project(str(project_dir / "p2e.toml")).project
    assert reloaded.packaging == project.packaging and reloaded.ci == project.ci


def test_empty_fields_fall_back_to_defaults(window):
    tab = window.platforms_tab
    tab.categories.setText("")
    tab.deb_section.setText("  ")
    tab.ci_python.setText("")
    project = window._current_project()
    assert project.packaging.categories == "Utility" and project.packaging.deb_section == "utils"
    assert project.ci.python_version == "3.12"


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="banner text is per host")
def test_banner_names_the_macos_only_format_on_linux(window):
    from py2exe_gui.qt import QLabel

    texts = [w.text() for w in window.platforms_tab.findChildren(QLabel)
             if w.objectName() == "noticeWarning"]
    assert any(Ar.FEATURE_DMG in t and "macOS" in t for t in texts)
    assert not any(Ar.FEATURE_DEB in t for t in texts)


def test_tab_texts_follow_the_locale(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr("py2exe_gui.ui.main_window.SETTINGS_FILE", str(tmp_path / "s.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.HISTORY_FILE", str(tmp_path / "h.json"))
    from py2exe_gui.ui.main_window import MainWindow

    for code, strings in (("en", En), ("ar", Ar)):
        set_locale(code)
        win = MainWindow()
        assert win.platforms_tab.build_packages_btn.text() == strings.BTN_BUILD_PACKAGES
        assert win.platforms_tab.generate_ci_btn.text() == strings.BTN_GENERATE_CI
        titles = {k: t for k, _w, t in win._all_tabs}
        assert titles["platforms"] == strings.TAB_PLATFORMS
        win.close()


# ── The workflow preview ──────────────────────────────────────────────────


def test_preview_dialog_shows_the_file_and_the_secrets(qapp, window):
    dialog = CiPreviewDialog("name: x\njobs: {}\n", "/repo/.github/workflows/p2e-release.yml",
                             exists=True, secrets=["WINDOWS_CERT_BASE64"], parent=window)
    assert dialog.text_view.toPlainText() == "name: x\njobs: {}\n"
    assert dialog.windowTitle() == Ar.CI_DIALOG_TITLE
    from py2exe_gui.qt import QLabel

    texts = " ".join(plain(w.text()) for w in dialog.findChildren(QLabel))
    assert "p2e-release.yml" in texts and Ar.CI_DIALOG_OVERWRITE_NOTE in texts
    assert "WINDOWS_CERT_BASE64" in texts
    dialog._copy_to_clipboard()
    assert qapp.clipboard().text() == "name: x\njobs: {}\n"


def test_generate_needs_a_saved_project(window, monkeypatch):
    shown = []
    answer(monkeypatch, "warning", QMessageBox.StandardButton.Ok, shown)
    window.generate_ci_workflow()
    assert shown == [Ar.MSG_CI_NEEDS_PROJECT]


def test_cancelling_the_preview_writes_nothing(window, project_dir, monkeypatch):
    open_project(window, project_dir)
    monkeypatch.setattr(CiPreviewDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
    window.generate_ci_workflow()
    assert not os.path.exists(workflow_path(str(project_dir)))
    assert Ar.LOG_CI_CANCELLED in window.main_tab.log_output.toPlainText()


def test_accepting_the_preview_writes_the_workflow(window, project_dir, monkeypatch):
    open_project(window, project_dir)
    seen = {}

    def accept(self):
        seen["text"] = self.text_view.toPlainText()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(CiPreviewDialog, "exec", accept)
    window.platforms_tab.ci_python.setText("3.10")
    window.generate_ci_workflow()
    path = workflow_path(str(project_dir))
    assert os.path.isfile(path)
    text = open(path, encoding="utf-8").read()
    assert text == seen["text"]
    assert 'python-version: "3.10"' in text and "--allow-doctor-errors" in text
    assert "ci_not_git" in window.main_tab.log_output.toPlainText()  # tmp_path is no repo
    # The window never reads a secret, so none can be in the file.
    assert "ghp_" not in text and "secrets." not in text.replace("${{ secrets.", "")


def test_output_outside_the_repository_blocks_generation(window, project_dir, tmp_path,
                                                         monkeypatch):
    open_project(window, project_dir)
    window.main_tab.output_dir.setText(str(tmp_path / "elsewhere"))
    shown = []
    answer(monkeypatch, "warning", QMessageBox.StandardButton.Ok, shown)
    window.generate_ci_workflow()
    assert len(shown) == 1 and Ar.FINDING_CI_OUTPUT_OUTSIDE_REPO_TITLE in shown[0]
    assert not os.path.exists(workflow_path(str(project_dir)))


# ── Packaging from the window ─────────────────────────────────────────────


def test_build_packages_refuses_without_formats_or_build(window, project_dir, monkeypatch):
    open_project(window, project_dir)
    shown = []
    answer(monkeypatch, "warning", QMessageBox.StandardButton.Ok, shown)
    window.platforms_tab.format_checks["deb"].setChecked(False)
    window.build_packages()
    assert shown == [Ar.MSG_PACKAGES_NONE_SELECTED]
    window.platforms_tab.format_checks["deb"].setChecked(True)
    monkeypatch.setattr("py2exe_gui.core.platform_support.sys.platform", "win32")
    window.build_packages()
    assert Ar.MSG_PACKAGES_NONE_HERE.split("{")[0] in shown[1]
    monkeypatch.setattr("py2exe_gui.core.platform_support.sys.platform", "linux")
    window.build_packages()
    assert shown[2] == Ar.MSG_PACKAGES_NO_BUILD
    assert window.package_thread is None


def fake_dist(project_dir):
    dist = project_dir / "dist"
    dist.mkdir()
    built = dist / "hello"
    built.write_text("#!/bin/sh\necho hello\n")
    built.chmod(0o755)
    return built


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux packagers")
def test_declining_the_appimagetool_download_skips_the_appimage(qapp, window, project_dir,
                                                                 tmp_path, monkeypatch):
    open_project(window, project_dir)
    fake_dist(project_dir)
    monkeypatch.setitem(packagers._PACKAGERS, "appimage",
                        AppImagePackager(tools_dir=str(tmp_path / "tools")))
    monkeypatch.delenv("APPIMAGETOOL", raising=False)
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    window.platforms_tab.format_checks["deb"].setChecked(False)
    window.platforms_tab.format_checks["appimage"].setChecked(True)
    asked = []
    answer(monkeypatch, "question", QMessageBox.StandardButton.No, asked)
    window.build_packages()
    assert len(asked) == 1 and "appimagetool" in asked[0] and str(tmp_path / "tools") in asked[0]
    assert window.package_thread is None
    assert not (tmp_path / "tools").exists()
    assert Ar.LOG_APPIMAGETOOL_DECLINED in window.main_tab.log_output.toPlainText()


@pytest.mark.skipif(not sys.platform.startswith("linux") or shutil.which("dpkg-deb") is None,
                    reason="needs Linux and dpkg-deb")
def test_build_packages_makes_a_real_deb(qapp, window, project_dir, monkeypatch):
    open_project(window, project_dir)
    fake_dist(project_dir)
    window.build_packages()
    wait_packages(qapp, window)
    deb = project_dir / "release" / "1.2.3" / "hello-app_1.2.3_amd64.deb"
    assert deb.is_file()
    log = window.main_tab.log_output.toPlainText()
    assert "hello-app_1.2.3_amd64.deb" in log and "package_icon_placeholder" in log
    result = plain(window.platforms_tab.packages_result.text())
    assert str(deb.parent) in result and "1" in result
    assert window.platforms_tab.open_packages_btn.isEnabled()
    assert window.platforms_tab.build_packages_btn.isEnabled()
    assert window._last_packages_dir == str(deb.parent)
    info = subprocess.run(["dpkg-deb", "-I", str(deb)], capture_output=True, text=True)
    assert "Maintainer: Me <me@example.com>" in info.stdout


def test_failed_package_is_reported(qapp, window, project_dir, monkeypatch):
    from py2exe_gui.core.packagers import PackageResult

    open_project(window, project_dir)
    fake_dist(project_dir)
    monkeypatch.setattr(shutil, "which", lambda _name: "/usr/bin/dpkg-deb")

    def failing(spec, formats, log=None, download_consent=None, **_kwargs):
        log("dpkg-deb: error: nope")
        return [PackageResult("deb", False, error_code="package_failed", error="nope")]

    monkeypatch.setattr("py2exe_gui.ui.package_thread.run_packaging", failing)
    monkeypatch.setattr("py2exe_gui.core.platform_support.sys.platform", "linux")
    window.build_packages()
    wait_packages(qapp, window)
    assert plain(window.platforms_tab.packages_result.text()) == Ar.PACKAGES_RESULT_FAILED
    assert "dpkg-deb: error: nope" in window.main_tab.log_output.toPlainText()
