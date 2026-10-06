"""Headless GUI tests for the Runtime Kit tab and its wiring."""

import json
import os
import stat
import sys

import pytest

pytest.importorskip("PyQt5", reason="PyQt5 not installed")

from PyQt5.QtWidgets import QFileDialog, QMessageBox  # noqa: E402

from py2exe_gui.core import BuildConfig  # noqa: E402
from py2exe_gui.core.config import RUNTIME_SERVICES, RuntimeKitConfig  # noqa: E402
from py2exe_gui.core.runtime_kit import kit_files  # noqa: E402
from py2exe_gui.core.update_signing import (  # noqa: E402
    new_signing_key,
    read_key_file,
    write_key_file,
)
from py2exe_gui.strings import Ar, En, S, set_locale  # noqa: E402
from py2exe_gui.ui.main_window import SIMPLE_MODE_TABS  # noqa: E402

pytestmark = pytest.mark.gui


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr("py2exe_gui.ui.main_window.SETTINGS_FILE", str(tmp_path / "s.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.HISTORY_FILE", str(tmp_path / "h.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.PRESETS_FILE", str(tmp_path / "p.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.ENVS_ROOT", str(tmp_path / "envs"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.SIGNING_KEY_FILE",
                        str(tmp_path / "config" / "signing" / "key.json"))
    from py2exe_gui.ui.main_window import MainWindow

    win = MainWindow()
    yield win
    win.close()


def key_file():
    from py2exe_gui.ui import main_window

    return main_window.SIGNING_KEY_FILE


def answer(monkeypatch, kind, reply, record=None):
    def fake(*args, **_kwargs):
        if record is not None:
            record.append(args[2] if len(args) > 2 else "")
        return reply

    monkeypatch.setattr(QMessageBox, kind, staticmethod(fake))


def make_source(tmp_path, code="print('hi')\n"):
    folder = tmp_path / "proj"
    folder.mkdir(exist_ok=True)
    path = folder / "app.py"
    path.write_text(code)
    return str(path)


def enable(window, *services):
    for name in services:
        window.runtime_tab.service_checks[name].setChecked(True)


def set_updater(window, key=None):
    tab = window.runtime_tab
    enable(window, "updater")
    tab.update_url.setText("https://example.com/u.json")
    tab.app_version.setText("1.0.0")
    tab.public_key.setText(key or "ab" * 32)


# ── The tab ────────────────────────────────────────────────────────────────


def test_tab_is_shown_and_everything_is_off(window):
    assert "runtime" in SIMPLE_MODE_TABS
    shown = [window.tabs.widget(i) for i in range(window.tabs.count())]
    assert window.runtime_tab in shown
    assert window._current_config().runtime_kit == RuntimeKitConfig()
    assert window.runtime_tab.preview_tabs.isHidden()
    assert not window.runtime_tab.update_url.isEnabled()


def test_titles_in_both_languages(window):
    titles = [window.tabs.tabText(i) for i in range(window.tabs.count())]
    assert Ar.TAB_RUNTIME in titles
    window.retranslate("en")
    titles = [window.tabs.tabText(i) for i in range(window.tabs.count())]
    assert En.TAB_RUNTIME in titles
    assert window.runtime_tab.service_checks["updater"].text() == En.KIT_NAME_UPDATER


def test_one_checkbox_per_service_with_an_explanation(window):
    set_locale("en")
    window.retranslate("en")
    checks = window.runtime_tab.service_checks
    assert list(checks) == list(RUNTIME_SERVICES)
    for name, check in checks.items():
        assert check.toolTip() == getattr(S, f"KIT_DESC_{name.upper()}")


def test_arabic_code_runs_keep_their_order(window):
    """print() must not turn into ()print inside right-to-left text."""
    from py2exe_gui.ui.tabs.runtime_tab import bidi

    set_locale("ar")
    text = bidi("يذهب print() إلى /SILENT و {app}")
    assert text.startswith("‏")
    assert "‎print()‎" in text and "‎/SILENT‎" in text
    assert "{app}" in text  # placeholders untouched
    set_locale("en")
    assert bidi("print() to /SILENT") == "print() to /SILENT"


def test_settings_round_trip_and_survive_a_language_switch(window, tmp_path):
    kit = RuntimeKitConfig(
        resource_path=True, crash_reporter=True, single_instance=True, updater=True,
        app_version="2.0", support_url="https://help.example", instance_message="Busy",
        update_url="https://e.com/u.json", update_public_key="cd" * 32,
        update_check_on_start=True, installer_args="/SILENT",
    )
    window._apply_config(BuildConfig(runtime_kit=kit))
    assert window._current_config().runtime_kit == kit
    window.runtime_tab.publish_version.setText("2.1")
    window.retranslate("en")
    assert window._current_config().runtime_kit == kit
    assert window.runtime_tab.publish_version.text() == "2.1"


def test_preview_shows_the_hook_and_the_config(window, tmp_path):
    window.main_tab.source_input.setText(make_source(tmp_path))
    window.main_tab.output_name.setText("Tool")
    enable(window, "crash_reporter")
    tab = window.runtime_tab
    assert not tab.preview_tabs.isHidden()
    assert "p2e_runtime.install()" in tab.preview_hook.toPlainText()
    data = json.loads(tab.preview_config.toPlainText())
    assert data["app"]["name"] == "Tool" and list(data["services"]) == ["crash_reporter"]
    assert data["services"]["crash_reporter"]["message"] == S.KIT_RT_CRASH_MESSAGE
    tab.service_checks["crash_reporter"].setChecked(False)
    assert tab.preview_tabs.isHidden()


def test_service_settings_follow_their_checkbox(window):
    tab = window.runtime_tab
    assert not tab.support_url.isEnabled()
    enable(window, "crash_reporter", "updater")
    assert tab.support_url.isEnabled() and tab.update_url.isEnabled()
    assert tab.key_generate_btn.isEnabled()  # keys are usable with the updater off too


def test_changing_the_kit_reexamines_the_project(window, monkeypatch):
    scheduled = []
    monkeypatch.setattr(window, "_schedule_doctor", lambda *a: scheduled.append(1))
    enable(window, "log_redirect")
    assert scheduled


# ── Keys ───────────────────────────────────────────────────────────────────


def test_generate_key(window):
    tab = window.runtime_tab
    assert not tab.publish_btn.isEnabled() and not tab.key_export_btn.isEnabled()
    enable(window, "updater")
    window.generate_signing_key()
    key = read_key_file(key_file())
    if sys.platform != "win32":
        assert stat.S_IMODE(os.stat(key_file()).st_mode) == 0o600
    assert tab.public_key.text() == key.public_hex
    assert key.public_hex[:4] in tab.key_status.text()
    assert tab.publish_btn.isEnabled() and tab.key_export_btn.isEnabled()
    # The private key never reaches the log, the settings or the config.
    secret = key.seed.hex()
    window.save_settings()
    assert secret not in window.main_tab.log_text()
    assert secret not in json.dumps(window.settings)
    assert secret not in json.dumps(window._current_config().to_dict())
    assert secret not in tab.key_status.text()


def test_replacing_a_key_needs_a_yes_and_keeps_the_old_one(window, monkeypatch):
    window.generate_signing_key()
    first = read_key_file(key_file())
    asked = []
    answer(monkeypatch, "question", QMessageBox.No, asked)
    window.generate_signing_key()
    assert read_key_file(key_file()) == first and asked
    answer(monkeypatch, "question", QMessageBox.Yes)
    window.generate_signing_key()
    assert read_key_file(key_file()) != first
    backups = [n for n in os.listdir(os.path.dirname(key_file())) if ".replaced-" in n]
    assert len(backups) == 1


def test_use_my_key(window):
    write_key_file(key_file(), new_signing_key())
    window.refresh_signing_key()
    enable(window, "updater")
    window.use_my_public_key()
    assert window.runtime_tab.public_key.text() == read_key_file(key_file()).public_hex


def test_export_warns_and_refuses_the_project_folder(window, tmp_path, monkeypatch):
    window.main_tab.source_input.setText(make_source(tmp_path))
    window.generate_signing_key()
    secret = read_key_file(key_file()).seed.hex()
    saved_to = []
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (saved_to[-1], "")))

    warnings = []
    answer(monkeypatch, "warning", QMessageBox.No, warnings)
    saved_to.append(str(tmp_path / "backup.json"))
    window.export_signing_key()
    assert warnings and not (tmp_path / "backup.json").exists()

    refused = []

    def warning(*args, **_kwargs):
        refused.append(args[2])
        return QMessageBox.Yes

    monkeypatch.setattr(QMessageBox, "warning", staticmethod(warning))
    saved_to.append(str(tmp_path / "proj" / "keys" / "backup.json"))
    window.export_signing_key()
    assert S.ERR_KIT_KEY_EXPORT_IN_PROJECT in refused
    assert not (tmp_path / "proj" / "keys").exists()

    saved_to.append(str(tmp_path / "safe" / "backup.json"))
    (tmp_path / "safe").mkdir()
    window.export_signing_key()
    assert read_key_file(str(tmp_path / "safe" / "backup.json")).seed.hex() == secret
    if sys.platform != "win32":
        assert stat.S_IMODE(os.stat(tmp_path / "safe" / "backup.json").st_mode) == 0o600
    assert secret not in window.main_tab.log_text()


def test_import_key(window, tmp_path, monkeypatch):
    other = new_signing_key()
    path = tmp_path / "imported.json"
    write_key_file(str(path), other)
    monkeypatch.setattr(QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (str(path), "")))
    window.import_signing_key()
    assert read_key_file(key_file()) == other
    # Importing a different key over it asks first.
    asked = []
    answer(monkeypatch, "question", QMessageBox.No, asked)
    third = new_signing_key()
    write_key_file(str(path), third, overwrite=True)
    window.import_signing_key()
    assert asked and read_key_file(key_file()) == other


def test_import_rejects_a_broken_file(window, tmp_path, monkeypatch):
    path = tmp_path / "bad.json"
    path.write_text("{}")
    monkeypatch.setattr(QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (str(path), "")))
    warned = []
    answer(monkeypatch, "warning", QMessageBox.Ok, warned)
    window.import_signing_key()
    assert warned and not os.path.exists(key_file())


# ── Publishing ─────────────────────────────────────────────────────────────


def test_publish_without_a_key(window, monkeypatch):
    warned = []
    answer(monkeypatch, "warning", QMessageBox.Ok, warned)
    window.publish_update()
    assert warned == [S.ERR_KIT_NO_KEY]


def test_publish_writes_signed_files(window, tmp_path, monkeypatch):
    from p2e_runtime.updates import parse_manifest, verify_manifest

    window.generate_signing_key()
    build = tmp_path / "dist" / "Tool.exe"
    build.parent.mkdir()
    build.write_bytes(b"MZ" * 500)
    tab = window.runtime_tab
    tab.publish_file.setText(str(build))
    tab.publish_version.setText("1.1.0")
    tab.publish_url.setText("https://example.com/Tool.exe")
    tab.publish_notes.setPlainText("Notes")
    shown = []
    answer(monkeypatch, "information", QMessageBox.Ok, shown)
    window.publish_update()
    manifest = (tmp_path / "dist" / "update.json").read_bytes()
    signature = (tmp_path / "dist" / "update.json.sig").read_bytes()
    verify_manifest(manifest, signature, read_key_file(key_file()).public_hex)
    assert parse_manifest(manifest)["version"] == "1.1.0"
    assert shown and "update.json" in window.main_tab.log_text()

    tab.publish_url.setText("http://example.com/Tool.exe")
    warned = []
    answer(monkeypatch, "warning", QMessageBox.Ok, warned)
    window.publish_update()
    assert warned and "https://" in warned[0]


# ── Settings someone else wrote ────────────────────────────────────────────


def test_foreign_update_key_asks_before_applying(window, monkeypatch):
    config = BuildConfig(runtime_kit=RuntimeKitConfig(
        updater=True, update_url="https://attacker.example/u.json", update_public_key="ee" * 32,
    ))
    asked = []
    answer(monkeypatch, "question", QMessageBox.No, asked)
    assert window._confirm_untrusted_config(config) is False
    assert "attacker.example" in asked[0] and "eeee eeee" in asked[0]


def test_own_key_and_generated_hook_do_not_ask(window, monkeypatch):
    window.generate_signing_key()
    own = read_key_file(key_file()).public_hex
    config = BuildConfig(runtime_kit=RuntimeKitConfig(
        resource_path=True, crash_reporter=True, updater=True,
        update_url="https://e.com/u.json", update_public_key=own,
    ))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: pytest.fail("asked")))
    assert window._confirm_untrusted_config(config) is True


def test_runtime_hook_in_extra_args_still_asks(window, monkeypatch):
    config = BuildConfig(extra_args="--runtime-hook evil.py",
                         runtime_kit=RuntimeKitConfig(log_redirect=True))
    asked = []
    answer(monkeypatch, "question", QMessageBox.No, asked)
    assert window._confirm_untrusted_config(config) is False
    assert "--runtime-hook" in asked[0]


# ── Building ───────────────────────────────────────────────────────────────


class FakeThread:
    """Captures the command a thread would run."""

    last = None

    def __init__(self, *args, **kwargs):
        self.args, self.kwargs = args, kwargs
        self.log_signal = self.finished_signal = self.progress_signal = self
        self.stage_signal = self.job_signal = self
        FakeThread.last = self

    def connect(self, _slot):
        pass

    def start(self):
        pass

    def isRunning(self):
        return False


@pytest.fixture
def no_build(window, monkeypatch):
    monkeypatch.setattr("py2exe_gui.ui.main_window.ConversionThread", FakeThread)
    monkeypatch.setattr("py2exe_gui.ui.main_window.DiagnosticThread", FakeThread)
    monkeypatch.setattr("py2exe_gui.ui.main_window.BatchThread", FakeThread)
    monkeypatch.setattr(window, "_ensure_pyinstaller", lambda python="": True)
    monkeypatch.setattr(window.tray, "show", lambda: None)
    FakeThread.last = None


def test_build_embeds_the_kit(window, tmp_path, no_build):
    window.main_tab.source_input.setText(make_source(tmp_path))
    window.main_tab.output_name.setText("Tool")
    enable(window, "log_redirect", "crash_reporter")
    window.start_conversion()
    cmd = FakeThread.last.args[0]
    files = kit_files(window._current_config())
    assert cmd[cmd.index("--runtime-hook") + 1] == files.hook_path
    assert os.path.isfile(files.hook_path) and os.path.isfile(files.config_path)
    assert "p2e_runtime.crash" in cmd and "p2e_runtime.updates" not in cmd
    log = window.main_tab.log_text()
    assert S.KIT_NAME_CRASH_REPORTER in log


def test_build_without_the_kit_adds_nothing(window, tmp_path, no_build):
    window.main_tab.source_input.setText(make_source(tmp_path))
    window.start_conversion()
    assert "--runtime-hook" not in FakeThread.last.args[0]
    assert not os.path.exists(tmp_path / "proj" / "build" / "p2e_runtime_kit")


def test_invalid_kit_blocks_the_build(window, tmp_path, no_build, monkeypatch):
    window.main_tab.source_input.setText(make_source(tmp_path))
    enable(window, "updater")
    window.runtime_tab.update_url.setText("http://insecure.example/u.json")
    warned = []
    answer(monkeypatch, "warning", QMessageBox.Ok, warned)
    window.start_conversion()
    assert FakeThread.last is None
    assert S.FINDING_KIT_UPDATE_URL_INSECURE_TITLE in warned[0]


def test_preview_command_lists_the_kit_options(window, tmp_path, monkeypatch):
    window.main_tab.source_input.setText(make_source(tmp_path))
    enable(window, "single_instance")
    seen = []

    class Dialog:
        def __init__(self, cmd, parent=None):
            seen.append(cmd)

        def exec_(self):
            pass

    monkeypatch.setattr("py2exe_gui.ui.main_window.CommandPreviewDialog", Dialog)
    window.preview_command()
    assert "--runtime-hook" in seen[0] and "p2e_runtime.single_instance" in seen[0]


def test_diagnostic_run_embeds_a_quiet_kit(window, tmp_path, no_build):
    window.main_tab.source_input.setText(make_source(tmp_path))
    window.main_tab.windowed_check.setChecked(True)
    enable(window, "crash_reporter", "updater")
    set_updater(window)
    window.runtime_tab.check_on_start.setChecked(True)
    window.start_diagnostic_run()
    cmd, diag = FakeThread.last.args[0], FakeThread.last.args[1]
    files = kit_files(diag)
    assert "p2e_diagnostic" in files.kit_dir  # never the real build's kit
    assert cmd[cmd.index("--runtime-hook") + 1] == files.hook_path
    data = json.load(open(files.config_path, encoding="utf-8"))
    assert data["services"]["crash_reporter"]["dialog"] is False
    assert data["services"]["updater"]["check_on_start"] is False


def test_batch_jobs_get_their_own_kit(window, tmp_path, no_build):
    source = make_source(tmp_path)
    window.batch_tab.set_sources([source])
    enable(window, "resource_path")
    window.start_batch_conversion()
    options_for = FakeThread.last.kwargs["options_for"]
    options, error = options_for(BuildConfig(source=source, output_name="Job",
                                             runtime_kit=RuntimeKitConfig(resource_path=True)))
    assert error is None and "--runtime-hook" in options
    assert "Job" in options[options.index("--runtime-hook") + 1]


def test_build_report_lists_the_services(window, tmp_path):
    from py2exe_gui.core.size_analyzer import SizeReport

    window.main_tab.source_input.setText(make_source(tmp_path))
    enable(window, "crash_reporter", "single_instance")
    config = window._current_config()
    window._write_build_report(config, SizeReport(), 0, 1.0, True)
    html = open(window._last_report_path, encoding="utf-8").read()
    assert S.REPORT_RUNTIME_KIT in html
    assert S.KIT_NAME_CRASH_REPORTER in html and S.KIT_NAME_SINGLE_INSTANCE in html


# ── Doctor ─────────────────────────────────────────────────────────────────


def test_doctor_offers_log_redirection_instead(window, tmp_path):
    set_locale("en")
    window.retranslate("en")
    window.main_tab.source_input.setText(make_source(tmp_path, "import sys\nsys.stdout.write('x')\n"))
    window.main_tab.windowed_check.setChecked(True)
    window.run_doctor()
    doctor = window.doctor_tab
    row = [i for i in range(doctor.findings_list.count())
           if doctor.findings_list.item(i).data(0x0100).code == "stream_in_windowed"][0]
    doctor.findings_list.setCurrentRow(row)
    assert not doctor.alt_btn.isHidden()
    assert En.KIT_NAME_LOG_REDIRECT in doctor.alt_btn.text()
    assert En.DOCTOR_ALT_HEADER in doctor.detail_view.toPlainText()
    doctor.alt_btn.click()
    assert window.runtime_tab.service_checks["log_redirect"].isChecked()
    assert window.main_tab.windowed_check.isChecked()  # the console stays off
    assert "stream_in_windowed" not in [f.code for f in window._doctor_findings]


def test_resource_path_snippet_switches_with_the_kit(window, tmp_path):
    source = make_source(tmp_path, "open('settings.json')\n")
    (tmp_path / "proj" / "settings.json").write_text("{}")
    window.main_tab.source_input.setText(source)
    window.run_doctor()
    finding = [f for f in window._doctor_findings if f.code == "relative_paths"][0]
    assert finding.snippet == "resource_path"
    enable(window, "resource_path")
    window.run_doctor()
    finding = [f for f in window._doctor_findings if f.code == "relative_paths"][0]
    assert finding.snippet == "runtime_resource_path"
