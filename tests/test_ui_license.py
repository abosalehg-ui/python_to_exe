"""Headless GUI tests for offline licensing: the Runtime Kit tab's licence
group, the key handlers and the generator dialog."""

import json
import os
import stat
import sys

import pytest

pytest.importorskip("py2exe_gui.qt", reason="no Qt binding (PySide6/PyQt5) installed")

from p2e_runtime import license as rlic  # noqa: E402
from py2exe_gui.core.licensing import LicenseRequest  # noqa: E402
from py2exe_gui.core.update_signing import (  # noqa: E402
    new_signing_key,
    read_key_file,
    write_key_file,
)
from py2exe_gui.qt import QApplication, QFileDialog, QMessageBox  # noqa: E402
from py2exe_gui.strings import Ar, En, S, set_locale  # noqa: E402
from py2exe_gui.ui.license_dialog import LicenseGeneratorDialog, problem_text  # noqa: E402
from tests.conftest import MemoryKeyring  # noqa: E402

pytestmark = pytest.mark.gui


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr("py2exe_gui.ui.main_window.SETTINGS_FILE", str(tmp_path / "s.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.HISTORY_FILE", str(tmp_path / "h.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.PRESETS_FILE", str(tmp_path / "p.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.KEYRING", MemoryKeyring())
    monkeypatch.setattr("py2exe_gui.ui.main_window.ENVS_ROOT", str(tmp_path / "envs"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.SIGNING_KEY_FILE",
                        str(tmp_path / "config" / "signing" / "update_signing_key.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.LICENSE_KEY_FILE",
                        str(tmp_path / "config" / "signing" / "license_signing_key.json"))
    from py2exe_gui.ui.main_window import MainWindow

    win = MainWindow()
    yield win
    win.close()


def key_file():
    from py2exe_gui.ui import main_window

    return main_window.LICENSE_KEY_FILE


def answer(monkeypatch, kind, reply, record=None):
    def fake(*args, **_kwargs):
        if record is not None:
            record.append(args[2] if len(args) > 2 else "")
        return reply

    monkeypatch.setattr(QMessageBox, kind, staticmethod(fake))


def make_source(tmp_path):
    folder = tmp_path / "proj"
    folder.mkdir(exist_ok=True)
    path = folder / "app.py"
    path.write_text("print('hi')\n")
    return str(path)


@pytest.fixture
def no_exec(monkeypatch):
    """The dialog opens without blocking; the test drives it through the window."""
    monkeypatch.setattr(LicenseGeneratorDialog, "exec", lambda self: 0)


# ── The tab ────────────────────────────────────────────────────────────────


def test_licensing_is_a_service_with_its_own_group(window):
    tab = window.runtime_tab
    assert "licensing" in tab.service_checks
    assert tab.license_group.title() == S.GROUP_KIT_LICENSE
    # Off by default: the fields are greyed out, key management stays usable.
    assert not tab.license_product.isEnabled() and not tab.license_public_key.isEnabled()
    assert not tab.license_use_key_btn.isEnabled()
    assert tab.license_key_create_btn.isEnabled() and tab.license_issue_btn.isEnabled()
    assert not tab.license_key_export_btn.isEnabled()  # no key yet
    assert S.KIT_LICENSE_KEY_STATUS_NONE.split()[0] in tab.license_key_status.text()


def test_honesty_note_is_shown_in_both_locales(window):
    for code, locale in (("ar", Ar), ("en", En)):
        set_locale(code)
        window.retranslate(code)
        labels = [w.text() for w in window.runtime_tab.license_group.findChildren(
            type(window.runtime_tab.license_key_status))]
        assert any(locale.KIT_LICENSE_HONESTY[:12] in text for text in labels), code
        assert "patch" in En.KIT_LICENSE_HONESTY and "إزالة" in Ar.KIT_LICENSE_HONESTY


def test_kit_config_round_trips_the_licence_fields(window):
    tab = window.runtime_tab
    tab.service_checks["licensing"].setChecked(True)
    tab.license_product.setText("My Product")
    tab.license_public_key.setText("ab" * 32)
    kit = tab.kit_config()
    assert kit.licensing and kit.license_product == "My Product"
    assert kit.license_public_key == "ab" * 32
    window.retranslate("en")
    again = window.runtime_tab.kit_config()
    assert again == kit


def test_preview_embeds_the_public_key_only(window, tmp_path):
    window.main_tab.source_input.setText(make_source(tmp_path))
    window.create_license_key()
    key = read_key_file(key_file())
    tab = window.runtime_tab
    tab.service_checks["licensing"].setChecked(True)
    window.use_my_license_key()
    assert tab.license_public_key.text() == key.public_hex
    config = json.loads(tab.preview_config.toPlainText())
    assert config["services"]["licensing"] == {"product": "app", "public_key": key.public_hex}
    assert key.seed.hex() not in tab.preview_config.toPlainText()
    assert "p2e_runtime.license" in window._runtime_kit_options(window._current_config())[0]


# ── The key ────────────────────────────────────────────────────────────────


def test_create_license_key(window):
    tab = window.runtime_tab
    tab.service_checks["licensing"].setChecked(True)
    window.create_license_key()
    key = read_key_file(key_file())
    if sys.platform != "win32":
        assert stat.S_IMODE(os.stat(key_file()).st_mode) == 0o600
    assert tab.license_public_key.text() == key.public_hex
    assert key.public_hex[:4] in tab.license_key_status.text()
    assert tab.license_key_export_btn.isEnabled() and tab.license_use_key_btn.isEnabled()
    # Separate from the update key, which still does not exist.
    from py2exe_gui.ui import main_window

    assert not os.path.exists(main_window.SIGNING_KEY_FILE)
    assert not tab.key_export_btn.isEnabled()
    # The private key never reaches the log, the settings or the config.
    secret = key.seed.hex()
    window.save_settings()
    assert secret not in window.main_tab.log_text()
    assert secret not in json.dumps(window.settings)
    assert secret not in json.dumps(window._current_config().to_dict())
    assert secret not in tab.license_key_status.text()
    assert S.LOG_KIT_LICENSE_KEY_CREATED.split()[0] in window.main_tab.log_text()


def test_replacing_the_license_key_needs_a_yes_and_keeps_the_old_one(window, monkeypatch):
    window.create_license_key()
    first = read_key_file(key_file())
    asked = []
    answer(monkeypatch, "question", QMessageBox.StandardButton.No, asked)
    window.create_license_key()
    assert read_key_file(key_file()) == first and asked
    assert first.public_hex[:4] in asked[0]
    answer(monkeypatch, "question", QMessageBox.StandardButton.Yes)
    window.create_license_key()
    assert read_key_file(key_file()) != first
    backups = [n for n in os.listdir(os.path.dirname(key_file())) if ".replaced-" in n]
    assert len(backups) == 1
    assert read_key_file(os.path.join(os.path.dirname(key_file()), backups[0])) == first


def test_export_license_key(window, tmp_path, monkeypatch):
    window.create_license_key()
    warned = []
    answer(monkeypatch, "warning", QMessageBox.StandardButton.Yes, warned)
    target = tmp_path / "backup" / "license_signing_key.json"
    target.parent.mkdir()
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(target), "")))
    window.export_license_key()
    assert warned and S.MSG_KIT_LICENSE_KEY_EXPORT_WARNING[:10] in warned[0]
    assert read_key_file(str(target)) == read_key_file(key_file())
    assert str(target) in window.main_tab.log_text()


def test_export_refused_inside_the_project(window, tmp_path, monkeypatch):
    source = make_source(tmp_path)
    window.main_tab.source_input.setText(source)
    window.create_license_key()
    answer(monkeypatch, "warning", QMessageBox.StandardButton.Yes)
    inside = os.path.join(os.path.dirname(source), "key.json")
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (inside, "")))
    window.export_license_key()
    assert not os.path.exists(inside)


def test_import_license_key(window, tmp_path, monkeypatch):
    other = new_signing_key()
    path = tmp_path / "imported.json"
    write_key_file(str(path), other)
    monkeypatch.setattr(QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (str(path), "")))
    window.import_license_key()
    assert read_key_file(key_file()) == other
    assert other.public_hex[:4] in window.runtime_tab.license_key_status.text()
    asked = []
    answer(monkeypatch, "question", QMessageBox.StandardButton.No, asked)
    write_key_file(str(path), new_signing_key(), overwrite=True)
    window.import_license_key()
    assert asked and read_key_file(key_file()) == other


# ── The generator dialog ───────────────────────────────────────────────────


def test_generator_refuses_to_open_without_a_key(window, monkeypatch, no_exec):
    warned = []
    answer(monkeypatch, "warning", QMessageBox.StandardButton.Ok, warned)
    window.open_license_generator()
    assert warned == [S.ERR_KIT_LICENSE_NO_KEY]
    assert not hasattr(window, "_license_dialog")


def test_generator_issues_a_key_the_runtime_accepts(window, tmp_path, no_exec):
    window.main_tab.source_input.setText(make_source(tmp_path))
    window.main_tab.output_name.setText("MyApp")
    window.create_license_key()
    key = read_key_file(key_file())
    window.open_license_generator()
    dialog = window._license_dialog
    assert dialog.product_edit.text() == "MyApp"  # from the build name
    assert dialog.no_expiry.isChecked() and not dialog.expiry_edit.isEnabled()
    assert not dialog.copy_btn.isEnabled()

    dialog.name_edit.setText("Sara")
    dialog.email_edit.setText("sara@example.com")
    dialog.features_edit.setText("pro, export")
    dialog.issue()
    text = dialog.key_view.toPlainText()
    assert text and text == dialog.key_text and dialog.problems.isHidden()
    info = rlic.verify(text, key.public_hex, "MyApp")
    assert info.name == "Sara" and info.features == ("pro", "export") and not info.expires
    assert rlic.verify(text, new_signing_key().public_hex, "MyApp") is None
    assert dialog.copy_btn.isEnabled()
    dialog.copy_key()
    assert QApplication.clipboard().text() == text
    # The log says who got a key, never the key itself nor the private half.
    log = window.main_tab.log_text()
    assert "Sara" in log and "MyApp" in log
    assert text[:20] not in log and key.seed.hex() not in log


def test_generator_with_an_expiry(window, tmp_path, no_exec):
    window.create_license_key()
    window.open_license_generator()
    dialog = window._license_dialog
    dialog.name_edit.setText("Sara")
    dialog.product_edit.setText("Tool")
    dialog.no_expiry.setChecked(False)
    assert dialog.expiry_edit.isEnabled()
    expiry = dialog.expiry_edit.date().toString("yyyy-MM-dd")  # a year ahead by default
    dialog.issue()
    info = rlic.verify(dialog.key_text, read_key_file(key_file()).public_hex, "Tool")
    assert info.expiry == expiry and info.expires
    assert expiry in dialog.result.text()


def test_generator_shows_each_problem_and_issues_nothing(window, no_exec):
    window.create_license_key()
    window.open_license_generator()
    dialog = window._license_dialog
    dialog.product_edit.setText("")
    dialog.email_edit.setText("not-an-email")
    dialog.features_edit.setText("ok, fe@ture")
    dialog.issue()
    assert not dialog.problems.isHidden() and dialog.key_text == ""
    shown = dialog.problems.text()
    assert S.LICENSE_ERR_NAME_MISSING in shown
    assert S.LICENSE_ERR_PRODUCT_MISSING in shown
    assert "not-an-email" in shown and "fe@ture" in shown
    assert not dialog.copy_btn.isEnabled()
    # A problem the window reports (no key any more) is shown, not raised.
    os.remove(key_file())
    dialog.name_edit.setText("Sara")
    dialog.product_edit.setText("Tool")
    dialog.email_edit.setText("")
    dialog.features_edit.setText("")
    dialog.issue()
    assert not dialog.problems.isHidden() and dialog.key_text == ""


def test_problem_texts_exist_in_both_locales():
    from py2exe_gui.core import licensing

    codes = [getattr(licensing, n) for n in dir(licensing) if n.startswith("ERR_")]
    assert len(codes) == 6
    for code_name in ("ar", "en"):
        set_locale(code_name)
        for code in codes:
            text = problem_text(code, "x")
            assert text != code and "{" not in text


def test_dialog_standalone_uses_the_given_product(qapp):
    issued = []

    def issue(request: LicenseRequest) -> str:
        issued.append(request)
        return "ABCDE-FGHIJ"

    dialog = LicenseGeneratorDialog(issue, "Tool")
    dialog.name_edit.setText("Sara")
    dialog.issue()
    assert issued[0].product == "Tool" and issued[0].name == "Sara"
    assert dialog.key_view.toPlainText() == "ABCDE-FGHIJ"
    dialog.close()
