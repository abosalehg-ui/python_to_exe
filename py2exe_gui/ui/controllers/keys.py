"""KeysController: Runtime Kit signing keys and offline licensing.

A mixin of MainWindow (py2exe_gui/ui/main_window.py). The window module's
constants and worker classes are read through ``_mw`` at call time so a test
that patches ``py2exe_gui.ui.main_window.X`` reaches this code too.
"""

import os

from py2exe_gui.core import (
    BuildConfig,
    licensing,
)
from py2exe_gui.core.diagnostics import build_name
from py2exe_gui.core.engines import engine_for
from py2exe_gui.core.runtime_kit import (
    render_hook,
    render_runtime_config,
    write_kit,
)
from py2exe_gui.core.update_signing import (
    backup_existing,
    fingerprint,
    is_inside,
    new_signing_key,
    publish_update,
    read_key_file,
    read_public_key,
    write_key_file,
)
from py2exe_gui.qt import (
    QMessageBox,
)
from py2exe_gui.strings import (
    LOCALE_LAYOUT,
    S,
    current_locale,
)
from py2exe_gui.texts import runtime_texts

# The side navigation (2.1): six sections, in the order the work happens.
# Each holds one or more of the former tabs; "build" is one composed page.
from py2exe_gui.ui import main_window as _mw  # noqa: E402 - late, see docstring
from py2exe_gui.ui.finding_text import finding_title, service_label
from py2exe_gui.ui.license_dialog import LicenseGeneratorDialog


class KeysController:
    # ─── Runtime Kit ────────────────────────────────────────────────────

    def _runtime_texts(self) -> dict:
        return runtime_texts()

    def _rtl(self) -> bool:
        return LOCALE_LAYOUT.get(current_locale(), "ltr") == "rtl"

    def _runtime_service_labels(self, config: BuildConfig):
        return [service_label(name) for name in config.runtime_kit.enabled_services()]

    def _runtime_kit_options(self, config: BuildConfig, diagnostic: bool = False):
        """Write the kit for ``config``; returns (PyInstaller options, error text)."""
        engine = engine_for(config)
        if config.runtime_kit.enabled and not engine.supports("runtime_kit"):
            return [], S.ERR_KIT_NEEDS_PYINSTALLER.format(engine=engine.display_name)
        try:
            options, errors = write_kit(
                config, self._runtime_texts(), rtl=self._rtl(), diagnostic=diagnostic
            )
        except OSError as e:
            return [], S.MSG_KIT_INVALID_FMT.format(problems=str(e))
        if errors:
            problems = "\n".join(f"• {finding_title(f)}" for f in errors)
            return [], S.MSG_KIT_INVALID_FMT.format(problems=problems)
        return options, None

    def on_runtime_kit_changed(self):
        self.refresh_runtime_preview()
        self._schedule_doctor()

    def refresh_runtime_preview(self, *_args):
        if not hasattr(self, "runtime_tab"):
            return
        config = self._current_config()
        if not config.runtime_kit.enabled:
            self.runtime_tab.show_preview("", "")
            return
        text = render_runtime_config(
            config.runtime_kit, build_name(config) if config.source or config.output_name
            else "app", config.onefile, self._runtime_texts(), self._rtl(),
        )
        self.runtime_tab.show_preview(render_hook(), text)

    def refresh_signing_key(self):
        self.runtime_tab.show_key(read_public_key(_mw.SIGNING_KEY_FILE), _mw.SIGNING_KEY_FILE)
        self.runtime_tab.show_license_key(read_public_key(_mw.LICENSE_KEY_FILE), _mw.LICENSE_KEY_FILE)

    def use_my_public_key(self):
        public = read_public_key(_mw.SIGNING_KEY_FILE)
        if public:
            self.runtime_tab.public_key.setText(public)

    def generate_signing_key(self):
        """Create the developer's key pair. Replacing one needs a hard yes."""
        existing = read_public_key(_mw.SIGNING_KEY_FILE)
        if existing or os.path.exists(_mw.SIGNING_KEY_FILE):
            reply = QMessageBox.question(
                self, S.MSG_CONFIRM,
                S.MSG_KIT_KEY_REPLACE_CONFIRM.format(fingerprint=fingerprint(existing) or "?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        key = new_signing_key()
        try:
            backup = backup_existing(_mw.SIGNING_KEY_FILE)
            write_key_file(_mw.SIGNING_KEY_FILE, key)
        except OSError as e:
            QMessageBox.critical(self, S.MSG_ERROR, S.ERR_KIT_KEY_WRITE.format(error=str(e)))
            return
        if backup:
            self._append_log(S.LOG_KIT_KEY_REPLACED.format(path=backup))
        # Only the public half is ever shown or logged.
        self._append_log(S.LOG_KIT_KEY_GENERATED.format(fingerprint=fingerprint(key.public_hex)))
        self.refresh_signing_key()
        if self.runtime_tab.service_checks["updater"].isChecked():
            self.runtime_tab.public_key.setText(key.public_hex)

    def _forbidden_key_folders(self):
        config = self._current_config()
        folders = []
        if config.source:
            folders.append(os.path.dirname(os.path.abspath(config.source)))
        if config.output_dir:
            folders.append(config.output_dir)
        return folders

    def export_signing_key(self):
        """Back up the private key — after a warning, and never into the project."""
        self._export_key(_mw.SIGNING_KEY_FILE, S.MSG_KIT_KEY_EXPORT_WARNING,
                         S.DIALOG_KIT_KEY_EXPORT, S.LOG_KIT_KEY_EXPORTED)

    def _export_key(self, key_file: str, warning: str, title: str, log_fmt: str):
        try:
            key = read_key_file(key_file)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_KIT_KEY_READ.format(error=str(e)))
            return
        reply = QMessageBox.warning(
            self, S.MSG_CONFIRM, warning, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        path, _ = _mw.QFileDialog.getSaveFileName(
            self, title, os.path.basename(key_file), S.DIALOG_FILTER_KEY
        )
        if not path:
            return
        if any(is_inside(path, folder) for folder in self._forbidden_key_folders()):
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_KIT_KEY_EXPORT_IN_PROJECT)
            return
        try:
            # The same owner-only write the key store uses; the user chose
            # the destination, so an existing file there is replaced.
            write_key_file(path, key, overwrite=True)
        except OSError as e:
            QMessageBox.critical(self, S.MSG_ERROR, S.ERR_KIT_KEY_WRITE.format(error=str(e)))
            return
        self._append_log(log_fmt.format(path=path))

    def import_signing_key(self):
        self._import_key(_mw.SIGNING_KEY_FILE, S.DIALOG_KIT_KEY_IMPORT,
                         S.MSG_KIT_KEY_REPLACE_CONFIRM, S.LOG_KIT_KEY_IMPORTED)

    def _import_key(self, key_file: str, title: str, replace_fmt: str, log_fmt: str):
        path, _ = _mw.QFileDialog.getOpenFileName(self, title, "", S.DIALOG_FILTER_KEY)
        if not path:
            return
        try:
            key = read_key_file(path)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_KIT_KEY_READ.format(error=str(e)))
            return
        existing = read_public_key(key_file)
        if existing == key.public_hex:
            self._append_log(log_fmt.format(fingerprint=fingerprint(existing)))
            return
        if existing or os.path.exists(key_file):
            reply = QMessageBox.question(
                self, S.MSG_CONFIRM,
                replace_fmt.format(fingerprint=fingerprint(existing) or "?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        try:
            backup = backup_existing(key_file)
            write_key_file(key_file, key)
        except OSError as e:
            QMessageBox.critical(self, S.MSG_ERROR, S.ERR_KIT_KEY_WRITE.format(error=str(e)))
            return
        if backup:
            self._append_log(S.LOG_KIT_KEY_REPLACED.format(path=backup))
        self._append_log(log_fmt.format(fingerprint=fingerprint(key.public_hex)))
        self.refresh_signing_key()

    # ─── Offline licensing (2.0) ────────────────────────────────────────

    def use_my_license_key(self):
        public = read_public_key(_mw.LICENSE_KEY_FILE)
        if public:
            self.runtime_tab.license_public_key.setText(public)

    def create_license_key(self):
        """Create the licence key pair. Replacing one needs a hard yes."""
        existing = read_public_key(_mw.LICENSE_KEY_FILE)
        if existing or os.path.exists(_mw.LICENSE_KEY_FILE):
            reply = QMessageBox.question(
                self, S.MSG_CONFIRM,
                S.MSG_KIT_LICENSE_KEY_REPLACE_CONFIRM.format(
                    fingerprint=fingerprint(existing) or "?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        try:
            key, backup = licensing.replace_key(_mw.LICENSE_KEY_FILE)
        except OSError as e:
            QMessageBox.critical(self, S.MSG_ERROR, S.ERR_KIT_KEY_WRITE.format(error=str(e)))
            return
        if backup:
            self._append_log(S.LOG_KIT_KEY_REPLACED.format(path=backup))
        self._append_log(S.LOG_KIT_LICENSE_KEY_CREATED.format(
            fingerprint=fingerprint(key.public_hex)))
        self.refresh_signing_key()
        if self.runtime_tab.service_checks["licensing"].isChecked():
            self.runtime_tab.license_public_key.setText(key.public_hex)

    def export_license_key(self):
        self._export_key(_mw.LICENSE_KEY_FILE, S.MSG_KIT_LICENSE_KEY_EXPORT_WARNING,
                         S.DIALOG_KIT_LICENSE_KEY_EXPORT, S.LOG_KIT_LICENSE_KEY_EXPORTED)

    def import_license_key(self):
        self._import_key(_mw.LICENSE_KEY_FILE, S.DIALOG_KIT_LICENSE_KEY_IMPORT,
                         S.MSG_KIT_LICENSE_KEY_REPLACE_CONFIRM, S.LOG_KIT_LICENSE_KEY_IMPORTED)

    def _issue_license(self, request):
        """Sign one licence with the stored key; logs the public facts only."""
        key = read_key_file(_mw.LICENSE_KEY_FILE)
        text = licensing.issue(request, key)
        self._append_log(S.LOG_KIT_LICENSE_ISSUED.format(
            name=request.name, product=request.product,
            expiry=request.expiry or S.KIT_LICENSE_NO_EXPIRY, length=len(text),
        ))
        return text

    def open_license_generator(self):
        """The licence dialog; refuses to open without a key rather than
        creating one behind the developer's back."""
        if not read_public_key(_mw.LICENSE_KEY_FILE):
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_KIT_LICENSE_NO_KEY)
            return
        config = self._current_config()
        product = config.runtime_kit.license_product.strip()
        if not product and (config.source or config.output_name):
            product = build_name(config)
        dialog = LicenseGeneratorDialog(self._issue_license, product, self)
        self._license_dialog = dialog  # tests reach it; the user sees it modal
        dialog.exec()

    def publish_update(self):
        """Write and sign update.json for a new build. Uploads nothing."""
        try:
            key = read_key_file(_mw.SIGNING_KEY_FILE)
        except (OSError, ValueError):
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_KIT_NO_KEY)
            return
        fields = self.runtime_tab.publish_fields()
        config = self._current_config()
        app_name = build_name(config) if config.source or config.output_name else ""
        try:
            result = publish_update(
                fields["file"], fields["version"], fields["url"], key,
                notes=fields["notes"], min_version=fields["min_version"], app_name=app_name,
            )
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_KIT_PUBLISH_FMT.format(error=str(e)))
            return
        self._append_log(S.LOG_KIT_PUBLISHED.format(
            manifest=result.manifest_path, signature=result.signature_path
        ))
        self.notify(S.MSG_KIT_PUBLISHED_FMT.format(
            manifest=result.manifest_path, signature=result.signature_path
        ), "success", 0)
