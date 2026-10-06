"""Runtime Kit: services embedded in the EXE, the update key, and publishing.

The tab holds the settings and shows what will be embedded; generating the
files, managing the key and writing update manifests are the window's (and
the core's) job.
"""

import re

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from py2exe_gui.core.config import RUNTIME_SERVICES, RuntimeKitConfig
from py2exe_gui.strings import LOCALE_LAYOUT, S, current_locale
from py2exe_gui.ui.tabs.base import BaseTab, browse_button, scrollable

# Indent of a service's explanation under its checkbox, in pixels.
_DESC_INDENT = 26
_RLM, _LRM = "\u200f", "\u200e"
# A run of code or a file name inside a sentence: starts with a letter, "_",
# "/" or "(", ends on a letter, digit or ")" — never on sentence punctuation.
_CODE_RUN = re.compile(r"[A-Za-z_/(][\x20-\x7a|~]*[A-Za-z0-9_)]|[A-Za-z_]")
_PLACEHOLDER = re.compile(r"(\{\w+\})")


def code_run(text: str) -> str:
    """Keep a run of code, a key or a path in left-to-right order in RTL text.

    Bracketed by left-to-right marks rather than the LRI/PDI isolates of
    ``size_tab.ltr()``: rendered offscreen, Qt 5.15 still moved the brackets
    of ``print()`` to the wrong end inside an isolate, while the marks (the
    form ``strings.py`` already uses around ``--runtime-hook``) held.
    """
    return f"{_LRM}{text}{_LRM}"


def bidi(text: str) -> str:
    """Make mixed Arabic/code text read correctly in a right-to-left UI.

    Each run of code (``print()``, ``/SILENT``, ``update.json``) goes through
    ``code_run``, otherwise its brackets and slashes migrate to the wrong end
    ("()print"). A leading right-to-left mark keeps a sentence that starts
    with a symbol such as "ℹ️" (a left-to-right character) from being laid out
    as a left-to-right paragraph.
    """
    if not text or LOCALE_LAYOUT.get(current_locale(), "ltr") != "rtl":
        return text
    # "{placeholders}" are left intact for a later .format().
    parts = _PLACEHOLDER.split(text)
    for index in range(0, len(parts), 2):
        parts[index] = _CODE_RUN.sub(lambda m: code_run(m.group(0)), parts[index])
    return _RLM + "".join(parts)


def _muted(text: str = "") -> QLabel:
    label = QLabel(bidi(text))
    label.setObjectName("aboutMuted")
    label.setWordWrap(True)
    return label


def _ltr_line(placeholder: str = "") -> QLineEdit:
    """A field for a URL, a key or a version: always left-to-right."""
    line = QLineEdit()
    line.setPlaceholderText(bidi(placeholder))
    line.setLayoutDirection(Qt.LeftToRight)
    return line


def _code_view() -> QPlainTextEdit:
    view = QPlainTextEdit()
    view.setObjectName("codeView")
    view.setReadOnly(True)
    view.setLayoutDirection(Qt.LeftToRight)
    view.setLineWrapMode(QPlainTextEdit.NoWrap)
    view.setMinimumHeight(150)
    return view


class RuntimeTab(BaseTab):
    """Which ``p2e_runtime`` services the EXE gets, and the updater's key."""

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        content = QWidget()
        layout = QVBoxLayout(content)
        # Room above each group box: its title sits in the margin and would be
        # clipped by whatever is above it.
        layout.setContentsMargins(6, 14, 6, 6)
        layout.setSpacing(14)
        outer.addWidget(scrollable(content))

        layout.addWidget(_muted(S.KIT_HINT))
        layout.addWidget(self._build_services_group())
        layout.addWidget(self._build_updater_group())
        layout.addWidget(self._build_publish_group())
        layout.addWidget(self._build_preview_group())
        layout.addStretch(1)

        self.show_key("", "")
        self.show_preview("", "")

    # ── Services ───────────────────────────────────────────────────────────

    def _build_services_group(self) -> QGroupBox:
        group = QGroupBox(S.GROUP_KIT_SERVICES)
        box = QVBoxLayout(group)
        self.service_checks = {}
        for name in RUNTIME_SERVICES:
            check = QCheckBox(bidi(getattr(S, f"KIT_NAME_{name.upper()}")))
            description = getattr(S, f"KIT_DESC_{name.upper()}")
            check.setToolTip(description)
            check.setAccessibleDescription(description)
            check.toggled.connect(self._changed)
            self.service_checks[name] = check
            box.addWidget(check)
            hint = _muted(description)
            hint.setContentsMargins(_DESC_INDENT, 0, 0, 4)
            box.addWidget(hint)

            if name == "crash_reporter":
                self.support_url = _ltr_line(S.KIT_SUPPORT_URL_PLACEHOLDER)
                self.support_url.textChanged.connect(self._changed)
                box.addLayout(self._indented_row(S.KIT_SUPPORT_URL_LABEL, self.support_url))
            elif name == "single_instance":
                self.instance_message = QLineEdit()
                self.instance_message.setPlaceholderText(
                    bidi(S.KIT_INSTANCE_MESSAGE_PLACEHOLDER)
                )
                self.instance_message.textChanged.connect(self._changed)
                box.addLayout(
                    self._indented_row(S.KIT_INSTANCE_MESSAGE_LABEL, self.instance_message)
                )
        return group

    @staticmethod
    def _indented_row(label: str, field: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(_DESC_INDENT, 0, 0, 6)
        row.addWidget(QLabel(bidi(label)))
        row.addWidget(field, stretch=1)
        return row

    # ── Updater ────────────────────────────────────────────────────────────

    def _build_updater_group(self) -> QGroupBox:
        self.updater_group = QGroupBox(S.GROUP_KIT_UPDATER)
        box = QVBoxLayout(self.updater_group)

        form = QFormLayout()
        self.update_url = _ltr_line(S.KIT_UPDATE_URL_PLACEHOLDER)
        self.app_version = _ltr_line(S.KIT_APP_VERSION_PLACEHOLDER)
        self.installer_args = _ltr_line(S.KIT_INSTALLER_ARGS_PLACEHOLDER)
        form.addRow(bidi(S.KIT_UPDATE_URL_LABEL), self.update_url)
        form.addRow(bidi(S.KIT_APP_VERSION_LABEL), self.app_version)
        form.addRow(bidi(S.KIT_INSTALLER_ARGS_LABEL), self.installer_args)

        key_row = QHBoxLayout()
        self.public_key = _ltr_line(S.KIT_PUBLIC_KEY_PLACEHOLDER)
        self.use_key_btn = QPushButton(S.BTN_KIT_USE_MY_KEY)
        self.use_key_btn.setAccessibleName(S.BTN_KIT_USE_MY_KEY)
        self.use_key_btn.clicked.connect(self.window_action("use_my_public_key"))
        key_row.addWidget(self.public_key, stretch=1)
        key_row.addWidget(self.use_key_btn)
        form.addRow(S.KIT_PUBLIC_KEY_LABEL, key_row)
        box.addLayout(form)

        for line in (self.update_url, self.app_version, self.installer_args, self.public_key):
            line.textChanged.connect(self._changed)

        self.check_on_start = QCheckBox(bidi(S.KIT_CHECK_ON_START))
        self.check_on_start.setToolTip(S.KIT_CHECK_ON_START_TIP)
        self.check_on_start.setAccessibleDescription(S.KIT_CHECK_ON_START_TIP)
        self.check_on_start.toggled.connect(self._changed)
        box.addWidget(self.check_on_start)
        box.addWidget(_muted(S.KIT_ONEDIR_NOTE))
        box.addWidget(_muted(S.KIT_API_HINT))

        self.key_status = QLabel()
        self.key_status.setWordWrap(True)
        self.key_status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        box.addWidget(self.key_status)

        buttons = QHBoxLayout()
        self.key_generate_btn = QPushButton(S.BTN_KIT_KEY_GENERATE)
        self.key_generate_btn.clicked.connect(self.window_action("generate_signing_key"))
        self.key_export_btn = QPushButton(S.BTN_KIT_KEY_EXPORT)
        self.key_export_btn.clicked.connect(self.window_action("export_signing_key"))
        self.key_import_btn = QPushButton(S.BTN_KIT_KEY_IMPORT)
        self.key_import_btn.clicked.connect(self.window_action("import_signing_key"))
        for button in (self.key_generate_btn, self.key_export_btn, self.key_import_btn):
            button.setAccessibleName(button.text())
            buttons.addWidget(button)
        buttons.addStretch(1)
        box.addLayout(buttons)
        return self.updater_group

    def show_key(self, public_hex: str, path: str):
        """Show whether a signing key exists (only its public half, ever)."""
        from py2exe_gui.core.update_signing import fingerprint

        if public_hex:
            # The fingerprint's groups would come out in reverse order inside
            # Arabic text without the marks; the path likewise.
            rtl = LOCALE_LAYOUT.get(current_locale(), "ltr") == "rtl"
            wrap = code_run if rtl else str
            self.key_status.setText(bidi(S.KIT_KEY_STATUS_FMT).format(
                fingerprint=wrap(fingerprint(public_hex)), path=wrap(path)
            ))
        else:
            self.key_status.setText(bidi(S.KIT_KEY_STATUS_NONE))
        self._has_key = bool(public_hex)
        self.key_export_btn.setEnabled(self._has_key)
        self.publish_btn.setEnabled(self._has_key)
        self._sync_enabled()

    # ── Publish ────────────────────────────────────────────────────────────

    def _build_publish_group(self) -> QGroupBox:
        group = QGroupBox(S.GROUP_KIT_PUBLISH)
        box = QVBoxLayout(group)
        box.addWidget(_muted(S.KIT_PUBLISH_HINT))

        form = QFormLayout()
        file_row = QHBoxLayout()
        self.publish_file = QLineEdit()
        self.publish_file.setPlaceholderText(bidi(S.KIT_PUBLISH_FILE_PLACEHOLDER))
        file_row.addWidget(self.publish_file, stretch=1)
        file_row.addWidget(browse_button(S.DIALOG_CHOOSE_UPDATE_FILE, self.browse_publish_file))
        form.addRow(bidi(S.KIT_PUBLISH_FILE_LABEL), file_row)
        self.publish_version = _ltr_line("1.3.0")
        self.publish_url = _ltr_line(S.KIT_PUBLISH_URL_PLACEHOLDER)
        self.publish_min_version = _ltr_line(S.KIT_PUBLISH_MIN_VERSION_PLACEHOLDER)
        self.publish_notes = QPlainTextEdit()
        self.publish_notes.setMaximumHeight(70)
        form.addRow(bidi(S.KIT_PUBLISH_VERSION_LABEL), self.publish_version)
        form.addRow(bidi(S.KIT_PUBLISH_URL_LABEL), self.publish_url)
        form.addRow(bidi(S.KIT_PUBLISH_MIN_VERSION_LABEL), self.publish_min_version)
        form.addRow(bidi(S.KIT_PUBLISH_NOTES_LABEL), self.publish_notes)
        box.addLayout(form)

        self.publish_btn = QPushButton(S.BTN_KIT_PUBLISH)
        self.publish_btn.setObjectName("successBtn")
        self.publish_btn.setAccessibleName(S.BTN_KIT_PUBLISH)
        self.publish_btn.clicked.connect(self.window_action("publish_update"))
        box.addWidget(self.publish_btn, alignment=Qt.AlignLeading)
        return group

    def browse_publish_file(self):
        path = self._choose_file(S.DIALOG_CHOOSE_UPDATE_FILE, S.DIALOG_FILTER_UPDATE_FILE)
        if path:
            self.publish_file.setText(path)

    def publish_fields(self) -> dict:
        return {
            "file": self.publish_file.text().strip(),
            "version": self.publish_version.text().strip(),
            "url": self.publish_url.text().strip(),
            "min_version": self.publish_min_version.text().strip(),
            "notes": self.publish_notes.toPlainText().strip(),
        }

    def set_publish_fields(self, fields: dict):
        self.publish_file.setText(fields.get("file", ""))
        self.publish_version.setText(fields.get("version", ""))
        self.publish_url.setText(fields.get("url", ""))
        self.publish_min_version.setText(fields.get("min_version", ""))
        self.publish_notes.setPlainText(fields.get("notes", ""))

    # ── Preview ────────────────────────────────────────────────────────────

    def _build_preview_group(self) -> QGroupBox:
        group = QGroupBox(S.GROUP_KIT_PREVIEW)
        box = QVBoxLayout(group)
        self.preview_note = _muted()
        box.addWidget(self.preview_note)
        self.preview_tabs = QTabWidget()
        self.preview_config = _code_view()
        self.preview_hook = _code_view()
        self.preview_tabs.addTab(self.preview_config, S.KIT_PREVIEW_CONFIG)
        self.preview_tabs.addTab(self.preview_hook, S.KIT_PREVIEW_HOOK)
        box.addWidget(self.preview_tabs)
        return group

    def show_preview(self, hook: str, config_json: str):
        """Show the generated hook and configuration ('' and '' = nothing on)."""
        nothing = not hook and not config_json
        self.preview_note.setText(bidi(S.KIT_PREVIEW_NONE) if nothing else "")
        self.preview_note.setVisible(nothing)
        self.preview_tabs.setVisible(not nothing)
        self.preview_config.setPlainText(config_json)
        self.preview_hook.setPlainText(hook)

    # ── The configuration ──────────────────────────────────────────────────

    def kit_config(self) -> RuntimeKitConfig:
        checks = self.service_checks
        return RuntimeKitConfig(
            resource_path=checks["resource_path"].isChecked(),
            log_redirect=checks["log_redirect"].isChecked(),
            crash_reporter=checks["crash_reporter"].isChecked(),
            single_instance=checks["single_instance"].isChecked(),
            updater=checks["updater"].isChecked(),
            app_version=self.app_version.text().strip(),
            support_url=self.support_url.text().strip(),
            instance_message=self.instance_message.text().strip(),
            update_url=self.update_url.text().strip(),
            update_public_key=self.public_key.text().strip(),
            update_check_on_start=self.check_on_start.isChecked(),
            installer_args=self.installer_args.text().strip(),
        )

    def set_kit_config(self, kit: RuntimeKitConfig):
        # One refresh at the end, not one per field.
        self._loading = True
        try:
            for name, check in self.service_checks.items():
                check.setChecked(bool(getattr(kit, name)))
            self.app_version.setText(kit.app_version)
            self.support_url.setText(kit.support_url)
            self.instance_message.setText(kit.instance_message)
            self.update_url.setText(kit.update_url)
            self.public_key.setText(kit.update_public_key)
            self.check_on_start.setChecked(kit.update_check_on_start)
            self.installer_args.setText(kit.installer_args)
        finally:
            self._loading = False
        self._changed()

    def _sync_enabled(self):
        """Grey out a service's settings while it is off.

        Key management and publishing stay usable either way: the key
        belongs to the developer, not to one build.
        """
        updater = self.service_checks["updater"].isChecked()
        for widget in (self.update_url, self.app_version, self.installer_args,
                       self.public_key, self.check_on_start):
            widget.setEnabled(updater)
        self.use_key_btn.setEnabled(updater and getattr(self, "_has_key", False))
        self.support_url.setEnabled(self.service_checks["crash_reporter"].isChecked())
        self.instance_message.setEnabled(self.service_checks["single_instance"].isChecked())

    def _changed(self, *_args):
        if getattr(self, "_loading", False) or not hasattr(self, "publish_btn"):
            return
        self._sync_enabled()
        handler = getattr(self.window, "on_runtime_kit_changed", None)
        if handler is not None:
            handler()
