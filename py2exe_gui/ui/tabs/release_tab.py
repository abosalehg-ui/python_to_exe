"""Release: version, notes, GitHub and winget settings, and the step checklist.

The tab holds the settings and shows progress; planning and running the
release is the window's job (through ``core.release.pipeline``), and the
token never passes through here except on its way into the OS keyring.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from py2exe_gui.core.project_file import ReleaseAssets, ReleaseSettings, WingetSettings
from py2exe_gui.core.release.pipeline import STEPS
from py2exe_gui.strings import S
from py2exe_gui.texts import STATUS_ICONS, reason_text, step_title
from py2exe_gui.ui.tabs.base import BaseTab, scrollable
from py2exe_gui.ui.tabs.runtime_tab import _ltr_line, _muted, bidi
from py2exe_gui.ui.tabs.size_tab import ltr

STEP_ROLE = Qt.UserRole


def _separator() -> str:
    """" — " between a step and its explanation.

    In a right-to-left layout the dash is pinned with right-to-left marks:
    otherwise "SHA-256 — SHA256SUMS.txt" merges into one left-to-right run
    and reads backwards.
    """
    from py2exe_gui.texts import is_rtl

    return "\u200f — \u200f" if is_rtl() else " — "


class ReleaseTab(BaseTab):
    """From version bump to published release, one checklist."""

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 14, 6, 6)
        layout.setSpacing(14)
        outer.addWidget(scrollable(content))

        layout.addWidget(_muted(S.RELEASE_HINT))
        layout.addWidget(self._build_version_group())
        layout.addWidget(self._build_notes_group())
        layout.addWidget(self._build_github_group())
        layout.addWidget(self._build_winget_group())
        layout.addWidget(self._build_steps_group())
        layout.addStretch(1)
        self.reset_steps()
        self.show_token_status("")
        self.show_mismatches([])

    # ── Version ────────────────────────────────────────────────────────────

    def _build_version_group(self) -> QGroupBox:
        group = QGroupBox(S.GROUP_RELEASE_VERSION)
        grid = QGridLayout(group)
        grid.addWidget(QLabel(S.RELEASE_VERSION_LABEL), 0, 0)
        self.version_input = _ltr_line(S.RELEASE_VERSION_PLACEHOLDER)
        self.version_input.setAccessibleName(S.RELEASE_VERSION_LABEL)
        grid.addWidget(self.version_input, 0, 1, 1, 3)

        self.bump_buttons = {}
        for column, part in enumerate(("patch", "minor", "major")):
            button = QPushButton(getattr(S, f"BTN_BUMP_{part.upper()}"))
            button.clicked.connect(lambda _c=False, p=part: self._bump(p))
            grid.addWidget(button, 1, column)
            self.bump_buttons[part] = button
        self.apply_version_btn = QPushButton(S.BTN_APPLY_VERSION)
        self.apply_version_btn.setToolTip(S.BTN_APPLY_VERSION_TIP)
        self.apply_version_btn.clicked.connect(self.window_action("apply_release_version"))
        grid.addWidget(self.apply_version_btn, 1, 3)

        self.mismatch_label = QLabel()
        self.mismatch_label.setObjectName("warningNotice")
        self.mismatch_label.setWordWrap(True)
        grid.addWidget(self.mismatch_label, 2, 0, 1, 4)
        return group

    def _bump(self, part: str):
        from py2exe_gui.core.release.versioning import bump

        try:
            self.version_input.setText(bump(self.version_input.text(), part))
        except ValueError:
            self.version_input.setText({"major": "1.0.0", "minor": "0.1.0",
                                        "patch": "0.0.1"}[part])

    def show_mismatches(self, mismatches):
        """List the tabs whose version disagrees with the project's."""
        if not mismatches:
            self.mismatch_label.setVisible(False)
            return
        rows = "\n".join(
            S.RELEASE_MISMATCH_ROW.format(field=ltr(m.field), value=ltr(m.old or "—"),
                                          expected=ltr(m.new))
            for m in mismatches
        )
        self.mismatch_label.setText(S.RELEASE_MISMATCH_FMT.format(rows=rows))
        self.mismatch_label.setVisible(True)

    # ── Notes ──────────────────────────────────────────────────────────────

    def _build_notes_group(self) -> QGroupBox:
        group = QGroupBox(S.GROUP_RELEASE_NOTES)
        box = QVBoxLayout(group)
        box.addWidget(_muted(S.RELEASE_NOTES_HINT))
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText(S.RELEASE_NOTES_PLACEHOLDER)
        self.notes_edit.setMinimumHeight(120)
        self.notes_edit.setAccessibleName(S.GROUP_RELEASE_NOTES)
        box.addWidget(self.notes_edit)
        row = QHBoxLayout()
        draft = QPushButton(S.BTN_DRAFT_NOTES)
        draft.clicked.connect(self.window_action("draft_release_notes"))
        load = QPushButton(S.BTN_LOAD_NOTES)
        load.clicked.connect(self.load_notes_file)
        row.addWidget(draft)
        row.addWidget(load)
        row.addStretch(1)
        box.addLayout(row)
        return group

    def load_notes_file(self):
        path = self._choose_file(S.BTN_LOAD_NOTES, S.DIALOG_FILTER_NOTES)
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                self.notes_edit.setPlainText(f.read())
        except (OSError, UnicodeDecodeError) as e:
            self.log(S.CLI_NOTES_UNREADABLE.format(error=str(e)))

    # ── GitHub ─────────────────────────────────────────────────────────────

    def _build_github_group(self) -> QGroupBox:
        group = QGroupBox(S.GROUP_RELEASE_GITHUB)
        form = QFormLayout(group)
        repo_row = QHBoxLayout()
        self.repository = _ltr_line("owner/repository")
        detect = QPushButton(S.BTN_DETECT_REPOSITORY)
        detect.clicked.connect(self.window_action("detect_release_repository"))
        repo_row.addWidget(self.repository, 1)
        repo_row.addWidget(detect)
        form.addRow(S.RELEASE_REPOSITORY_LABEL, repo_row)
        self.tag_prefix = _ltr_line("v")
        self.tag_prefix.setMaximumWidth(120)
        form.addRow(S.RELEASE_TAG_PREFIX_LABEL, self.tag_prefix)

        flags = QHBoxLayout()
        self.draft_check = QCheckBox(S.RELEASE_DRAFT)
        self.prerelease_check = QCheckBox(S.RELEASE_PRERELEASE)
        flags.addWidget(self.draft_check)
        flags.addWidget(self.prerelease_check)
        flags.addStretch(1)
        form.addRow(flags)

        assets = QGridLayout()
        self.asset_checks = {}
        for index, name in enumerate(("exe", "installer", "portable_zip", "checksums",
                                      "update_manifest")):
            check = QCheckBox(getattr(S, f"RELEASE_ASSET_{name.upper()}"))
            check.setChecked(True)
            self.asset_checks[name] = check
            assets.addWidget(check, index // 3, index % 3)
        form.addRow(S.RELEASE_ASSETS_LABEL, assets)

        # The token: stored in the OS keyring, shown never.
        self.token_status = QLabel()
        self.token_status.setWordWrap(True)
        form.addRow(S.RELEASE_TOKEN_LABEL, self.token_status)
        token_row = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.Password)
        self.token_input.setLayoutDirection(Qt.LeftToRight)
        self.token_input.setPlaceholderText(S.RELEASE_TOKEN_PLACEHOLDER)
        self.token_input.setAccessibleName(S.RELEASE_TOKEN_LABEL)
        self.save_token_btn = QPushButton(S.BTN_SAVE_TOKEN)
        self.save_token_btn.clicked.connect(self.window_action("save_github_token"))
        self.forget_token_btn = QPushButton(S.BTN_FORGET_TOKEN)
        self.forget_token_btn.clicked.connect(self.window_action("forget_github_token"))
        token_row.addWidget(self.token_input, 1)
        token_row.addWidget(self.save_token_btn)
        token_row.addWidget(self.forget_token_btn)
        form.addRow("", token_row)
        return group

    def show_token_status(self, source: str):
        text = {
            "keyring": S.RELEASE_TOKEN_FROM_KEYRING,
            "env": S.RELEASE_TOKEN_FROM_ENV,
        }.get(source, S.RELEASE_TOKEN_NONE)
        self.token_status.setText(bidi(text))
        self.forget_token_btn.setEnabled(source == "keyring")

    # ── winget ─────────────────────────────────────────────────────────────

    def _build_winget_group(self) -> QGroupBox:
        group = QGroupBox(S.GROUP_RELEASE_WINGET)
        form = QFormLayout(group)
        form.addRow(_muted(S.RELEASE_WINGET_HINT))
        self.winget_check = QCheckBox(S.RELEASE_WINGET_ENABLE)
        form.addRow(self.winget_check)
        self.winget_identifier = _ltr_line("Publisher.AppName")
        self.winget_publisher = QLineEdit()
        self.winget_license = QLineEdit()
        self.winget_license.setPlaceholderText("MIT / Proprietary")
        self.winget_description = QLineEdit()
        self.winget_locale = _ltr_line("en-US")
        self.winget_locale.setMaximumWidth(120)
        form.addRow(S.RELEASE_WINGET_IDENTIFIER, self.winget_identifier)
        form.addRow(S.RELEASE_WINGET_PUBLISHER, self.winget_publisher)
        form.addRow(S.RELEASE_WINGET_LICENSE, self.winget_license)
        form.addRow(S.RELEASE_WINGET_DESCRIPTION, self.winget_description)
        form.addRow(S.RELEASE_WINGET_LOCALE, self.winget_locale)
        self.winget_check.toggled.connect(self._sync_enabled)
        self._sync_enabled()
        return group

    def _sync_enabled(self, *_args):
        on = self.winget_check.isChecked()
        for widget in (self.winget_identifier, self.winget_publisher, self.winget_license,
                       self.winget_description, self.winget_locale):
            widget.setEnabled(on)

    # ── Steps ──────────────────────────────────────────────────────────────

    def _build_steps_group(self) -> QGroupBox:
        group = QGroupBox(S.GROUP_RELEASE_STEPS)
        box = QVBoxLayout(group)
        self.steps_list = QListWidget()
        self.steps_list.setMinimumHeight(300)
        self.steps_list.setAccessibleName(S.GROUP_RELEASE_STEPS)
        box.addWidget(self.steps_list)

        options = QGridLayout()
        self.dry_run_check = QCheckBox(S.RELEASE_DRY_RUN)
        self.dry_run_check.setToolTip(S.RELEASE_DRY_RUN_TIP)
        self.dry_run_check.setChecked(True)
        self.create_tag_check = QCheckBox(S.RELEASE_CREATE_TAG)
        self.create_tag_check.setChecked(True)
        self.push_tag_check = QCheckBox(S.RELEASE_PUSH_TAG)
        self.publish_check = QCheckBox(S.RELEASE_PUBLISH)
        self.publish_check.setChecked(True)
        self.allow_errors_check = QCheckBox(S.RELEASE_ALLOW_DOCTOR_ERRORS)
        for index, check in enumerate((self.dry_run_check, self.create_tag_check,
                                       self.push_tag_check, self.publish_check,
                                       self.allow_errors_check)):
            options.addWidget(check, index // 3, index % 3)
        self.create_tag_check.toggled.connect(self.push_tag_check.setEnabled)
        box.addLayout(options)

        row = QHBoxLayout()
        self.start_btn = QPushButton(S.BTN_START_RELEASE)
        self.start_btn.setObjectName("successBtn")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self.window_action("start_release"))
        row.addWidget(self.start_btn)
        self.open_release_btn = QPushButton(S.BTN_OPEN_RELEASE_FOLDER)
        self.open_release_btn.clicked.connect(self.window_action("open_release_folder"))
        self.open_release_btn.setEnabled(False)
        row.addWidget(self.open_release_btn)
        box.addLayout(row)
        self.result_label = QLabel()
        self.result_label.setWordWrap(True)
        self.result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        box.addWidget(self.result_label)
        return group

    def reset_steps(self):
        self.steps_list.clear()
        for key in STEPS:
            item = QListWidgetItem(f"{STATUS_ICONS['pending']} {step_title(key)}")
            item.setData(STEP_ROLE, key)
            self.steps_list.addItem(item)

    def show_step(self, result):
        """Update one row of the checklist from a ``StepResult``."""
        for row in range(self.steps_list.count()):
            item = self.steps_list.item(row)
            if item.data(STEP_ROLE) != result.key:
                continue
            reason = reason_text(result)
            text = f"{STATUS_ICONS.get(result.status, '•')} {bidi(step_title(result.key))}"
            if reason:
                text += _separator() + bidi(reason)
            item.setText(text)
            item.setToolTip(reason)
            return

    def step_texts(self):
        return [self.steps_list.item(i).text() for i in range(self.steps_list.count())]

    def set_running(self, running: bool):
        self.start_btn.setEnabled(not running)
        for widget in (self.dry_run_check, self.version_input):
            widget.setEnabled(not running)

    def show_result(self, text: str, folder_ready: bool):
        self.result_label.setText(bidi(text))
        self.open_release_btn.setEnabled(folder_ready)

    # ── The project's release settings ─────────────────────────────────────

    def release_settings(self) -> ReleaseSettings:
        checks = self.asset_checks
        return ReleaseSettings(
            repository=self.repository.text().strip(),
            tag_prefix=self.tag_prefix.text().strip() or "v",
            draft=self.draft_check.isChecked(),
            prerelease=self.prerelease_check.isChecked(),
            assets=ReleaseAssets(**{name: check.isChecked() for name, check in checks.items()}),
            winget=WingetSettings(
                enabled=self.winget_check.isChecked(),
                identifier=self.winget_identifier.text().strip(),
                publisher=self.winget_publisher.text().strip(),
                license=self.winget_license.text().strip(),
                short_description=self.winget_description.text().strip(),
                locale=self.winget_locale.text().strip() or "en-US",
            ),
        )

    def set_release_settings(self, release: ReleaseSettings):
        self.repository.setText(release.repository)
        self.tag_prefix.setText(release.tag_prefix)
        self.draft_check.setChecked(release.draft)
        self.prerelease_check.setChecked(release.prerelease)
        for name, check in self.asset_checks.items():
            check.setChecked(bool(getattr(release.assets, name)))
        w = release.winget
        self.winget_check.setChecked(w.enabled)
        self.winget_identifier.setText(w.identifier)
        self.winget_publisher.setText(w.publisher)
        self.winget_license.setText(w.license)
        self.winget_description.setText(w.short_description)
        self.winget_locale.setText(w.locale)

    def read_project(self, project):
        project.version = self.version_input.text().strip()
        project.release = self.release_settings()

    def apply_project(self, project, sections=()):
        if "project" in sections:
            self.version_input.setText(project.version)
        if "release" in sections:
            self.set_release_settings(project.release)
