"""Project doctor: readiness score, findings, and one-click fixes."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from py2exe_gui.core.fixes import readiness_score
from py2exe_gui.strings import S
from py2exe_gui.ui.finding_text import copy_text, detail_lines, finding_label, origin_label
from py2exe_gui.ui.tabs.base import BaseTab

# Data roles on each list item: the Finding itself.
FINDING_ROLE = Qt.UserRole


class DoctorTab(BaseTab):
    """Shows what the doctor and the last build/run found, with fixes."""

    def _build(self):
        layout = QVBoxLayout(self)

        hint = QLabel(S.DOCTOR_HINT)
        hint.setObjectName("aboutMuted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        header = QHBoxLayout()
        self.score_label = QLabel(S.DOCTOR_SCORE_NONE)
        score_font = QFont()
        score_font.setPointSize(16)
        score_font.setBold(True)
        self.score_label.setFont(score_font)
        self.score_label.setAccessibleName(S.DOCTOR_SCORE_NONE)
        self.summary_label = QLabel("")
        self.summary_label.setObjectName("aboutMuted")
        examine_btn = QPushButton(S.BTN_DOCTOR_EXAMINE)
        examine_btn.setAccessibleName(S.BTN_DOCTOR_EXAMINE)
        examine_btn.clicked.connect(self.window_action("run_doctor"))
        header.addWidget(self.score_label)
        header.addWidget(self.summary_label, stretch=1)
        header.addWidget(examine_btn)
        layout.addLayout(header)

        group = QGroupBox(S.TAB_DOCTOR)
        group_layout = QVBoxLayout(group)
        self.findings_list = QListWidget()
        self.findings_list.setMinimumHeight(160)
        self.findings_list.setAccessibleName(S.TAB_DOCTOR)
        self.findings_list.currentItemChanged.connect(self._on_selection_changed)
        group_layout.addWidget(self.findings_list, stretch=2)

        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        self.detail_view.setAcceptRichText(False)
        self.detail_view.setMinimumHeight(140)
        group_layout.addWidget(self.detail_view, stretch=2)

        self.copy_btn = QPushButton(S.BTN_DOCTOR_COPY)
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self.copy_selected)
        group_layout.addWidget(self.copy_btn, alignment=Qt.AlignLeading)
        layout.addWidget(group, stretch=1)

        buttons = QHBoxLayout()
        self.apply_btn = QPushButton(S.BTN_DOCTOR_APPLY)
        self.apply_btn.clicked.connect(lambda: self._apply(rebuild=False))
        self.rebuild_btn = QPushButton(S.BTN_DOCTOR_APPLY_REBUILD)
        self.rebuild_btn.setObjectName("successBtn")
        self.rebuild_btn.clicked.connect(lambda: self._apply(rebuild=True))
        self.diagnose_btn = QPushButton(S.BTN_DOCTOR_DIAGNOSE)
        self.diagnose_btn.setToolTip(S.BTN_DOCTOR_DIAGNOSE_TIP)
        self.diagnose_btn.setAccessibleDescription(S.BTN_DOCTOR_DIAGNOSE_TIP)
        self.diagnose_btn.clicked.connect(self.window_action("start_diagnostic_run"))
        self.sandbox_btn = QPushButton(S.BTN_SANDBOX)
        self.sandbox_btn.setToolTip(S.BTN_SANDBOX_TIP)
        self.sandbox_btn.setAccessibleDescription(S.BTN_SANDBOX_TIP)
        self.sandbox_btn.clicked.connect(self.window_action("open_in_sandbox"))
        for button in (self.apply_btn, self.rebuild_btn, self.diagnose_btn, self.sandbox_btn):
            button.setAccessibleName(button.text())
            buttons.addWidget(button)
        layout.addLayout(buttons)

        self.doctor_findings = []
        self.build_findings = []
        self.show_findings([], [], has_source=False)

    # ── Display ────────────────────────────────────────────────────────────

    def show_findings(self, doctor_findings, build_findings, has_source=True):
        """Render both lists: what happened first, then what is predicted."""
        self.doctor_findings = list(doctor_findings)
        self.build_findings = list(build_findings)
        self.findings_list.clear()
        self.detail_view.clear()
        self.copy_btn.setEnabled(False)

        if not has_source:
            self.score_label.setText(S.DOCTOR_SCORE_NONE)
            self.summary_label.setText("")
            self.findings_list.addItem(S.DOCTOR_NO_SOURCE)
            self._set_actions_enabled(False)
            return

        score = readiness_score(self.doctor_findings)
        self.score_label.setText(S.DOCTOR_SCORE_FMT.format(score=score))
        self.score_label.setAccessibleName(self.score_label.text())
        summary = S.DOCTOR_SUMMARY_FMT.format(
            errors=sum(f.severity == "error" for f in self.doctor_findings),
            warnings=sum(f.severity == "warning" for f in self.doctor_findings),
            infos=sum(f.severity == "info" for f in self.doctor_findings),
        )
        if self.build_findings:
            summary += "  |  " + S.DOCTOR_BUILD_SUMMARY_FMT.format(
                count=len(self.build_findings)
            )
        self.summary_label.setText(summary)

        everything = self.build_findings + self.doctor_findings
        if not everything:
            self.findings_list.addItem(S.DOCTOR_ALL_CLEAR)
            self._set_actions_enabled(False)
            return

        for finding in everything:
            item = QListWidgetItem(finding_label(finding))
            item.setData(FINDING_ROLE, finding)
            item.setToolTip(origin_label(finding.origin))
            if finding.auto_fixable:
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                # Errors and warnings are ticked by default; info is opt-in.
                checked = finding.severity != "info"
                item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
            self.findings_list.addItem(item)
        self._set_actions_enabled(any(f.auto_fixable for f in everything))
        self.findings_list.setCurrentRow(0)

    def _set_actions_enabled(self, enabled: bool):
        self.apply_btn.setEnabled(enabled)
        self.rebuild_btn.setEnabled(enabled)

    def selected_finding(self):
        item = self.findings_list.currentItem()
        return item.data(FINDING_ROLE) if item is not None else None

    def _on_selection_changed(self, current, _previous=None):
        finding = current.data(FINDING_ROLE) if current is not None else None
        if finding is None:
            self.detail_view.clear()
            self.copy_btn.setEnabled(False)
            return
        self.detail_view.setPlainText("\n".join(detail_lines(finding)))
        text = copy_text(finding)
        self.copy_btn.setEnabled(bool(text))
        self.copy_btn.setText(
            S.BTN_DOCTOR_COPY_PIP if text.startswith("pip ") else S.BTN_DOCTOR_COPY
        )

    # ── Actions ────────────────────────────────────────────────────────────

    def checked_fixes(self):
        """Fixes of every ticked finding, in list order, without duplicates."""
        fixes = []
        for row in range(self.findings_list.count()):
            item = self.findings_list.item(row)
            finding = item.data(FINDING_ROLE)
            if finding is None or not finding.auto_fixable:
                continue
            if item.checkState() != Qt.Checked:
                continue
            fixes.extend(f for f in finding.fixes if f not in fixes)
        return fixes

    def copy_selected(self):
        finding = self.selected_finding()
        text = copy_text(finding) if finding is not None else ""
        if not text:
            return
        QApplication.clipboard().setText(text)
        self.log(S.DOCTOR_COPIED)

    def _apply(self, rebuild: bool):
        if self.window is not None:
            self.window.apply_doctor_fixes(self.checked_fixes(), rebuild=rebuild)
