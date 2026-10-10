"""Build environment, size lab and build report.

The three belong together: the size lab shows what is in the EXE, and the
isolated environment is the biggest lever for taking things out of it.
"""

import os
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from py2exe_gui.core.size_analyzer import format_size, group_label_key
from py2exe_gui.strings import S
from py2exe_gui.ui.finding_text import finding_detail, finding_label
from py2exe_gui.ui.tabs.base import BaseTab, browse_button, scrollable

FINDING_ROLE = Qt.UserRole
_LRI, _PDI = "\u2066", "\u2069"


def ltr(text: str) -> str:
    """Keep "41.6 MB" or "+12.5%" in reading order inside right-to-left text.

    Without the isolate, an RTL paragraph flips them to "MB 41.6".
    """
    return f"{_LRI}{text}{_PDI}"


def size_text(size: int) -> str:
    return ltr(format_size(size))
# Rows in the breakdown before the rest are folded into one line.
BREAKDOWN_ROWS = 15


def _muted(text: str = "") -> QLabel:
    label = QLabel(text)
    label.setObjectName("aboutMuted")
    label.setWordWrap(True)
    return label


class SizeTab(BaseTab):
    """Where the EXE's weight comes from, and how to lose some."""

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        content = QWidget()
        layout = QVBoxLayout(content)
        # Room above the first group box: its title sits in the margin and
        # would be clipped by the top edge of the scroll area.
        layout.setContentsMargins(6, 14, 6, 6)
        outer.addWidget(scrollable(content))

        layout.addWidget(self._build_env_group())
        layout.addWidget(self._build_size_group())
        layout.addWidget(self._build_suggestions_group())
        layout.addWidget(self._build_compare_group())
        layout.addWidget(self._build_report_group())
        layout.addStretch(1)

        self.show_size_report(None)

    # ── Build environment ──────────────────────────────────────────────────

    def _build_env_group(self) -> QGroupBox:
        group = QGroupBox(S.GROUP_BUILD_ENV)
        box = QVBoxLayout(group)
        box.addWidget(_muted(S.ENV_HINT))

        version = ".".join(str(part) for part in sys.version_info[:3])
        self.current_radio = QRadioButton(S.ENV_MODE_CURRENT_FMT.format(version=version))
        self.isolated_radio = QRadioButton(S.ENV_MODE_ISOLATED)
        self.current_radio.setChecked(True)
        mode = QButtonGroup(self)
        mode.addButton(self.current_radio)
        mode.addButton(self.isolated_radio)
        self.isolated_radio.toggled.connect(self.window_action("on_env_mode_changed"))
        box.addWidget(self.current_radio)
        box.addWidget(self.isolated_radio)

        row = QHBoxLayout()
        row.addWidget(QLabel(S.ENV_BASE_PYTHON_LABEL))
        self.base_python = QLineEdit()
        self.base_python.setPlaceholderText(S.ENV_BASE_PYTHON_PLACEHOLDER)
        row.addWidget(self.base_python, stretch=1)
        row.addWidget(browse_button(S.DIALOG_CHOOSE_PYTHON, self.browse_base_python))
        box.addLayout(row)

        self.env_status = QLabel(S.ENV_STATUS_NO_SOURCE)
        self.env_status.setWordWrap(True)
        self.env_status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.env_requirements = _muted()
        self.env_uv = _muted()
        box.addWidget(self.env_status)
        box.addWidget(self.env_requirements)
        box.addWidget(self.env_uv)

        buttons = QHBoxLayout()
        self.env_create_btn = QPushButton(S.BTN_ENV_CREATE)
        self.env_create_btn.clicked.connect(self.window_action("create_build_env"))
        self.env_recreate_btn = QPushButton(S.BTN_ENV_RECREATE)
        self.env_recreate_btn.clicked.connect(self.window_action("recreate_build_env"))
        self.env_lock_btn = QPushButton(S.BTN_ENV_LOCK)
        self.env_lock_btn.setToolTip(S.BTN_ENV_LOCK_TIP)
        self.env_lock_btn.clicked.connect(self.window_action("save_env_lock"))
        self.env_delete_btn = QPushButton(S.BTN_ENV_DELETE)
        self.env_delete_btn.setObjectName("dangerBtn")
        self.env_delete_btn.clicked.connect(self.window_action("delete_build_env"))
        for button in (self.env_create_btn, self.env_recreate_btn,
                       self.env_lock_btn, self.env_delete_btn):
            button.setAccessibleName(button.text())
            buttons.addWidget(button)
        box.addLayout(buttons)
        return group

    def browse_base_python(self):
        path = self._choose_file(S.DIALOG_CHOOSE_PYTHON, S.DIALOG_FILTER_PYTHON)
        if path:
            self.base_python.setText(path)

    def show_env(self, status, requirements_text: str, uv: bool, has_source: bool):
        """Refresh the environment section.

        ``status`` is a ``venv_manager.EnvStatus`` (or None without a source).
        """
        if not has_source or status is None:
            self.env_status.setText(S.ENV_STATUS_NO_SOURCE)
            self.env_requirements.setText("")
            self.env_uv.setText("")
            for button in (self.env_create_btn, self.env_recreate_btn,
                           self.env_lock_btn, self.env_delete_btn):
                button.setEnabled(False)
            return
        if status.exists:
            size = int(status.metadata.get("size_bytes", 0) or 0)
            self.env_status.setText(S.ENV_STATUS_FMT.format(
                version=status.python_version or "?",
                size=size_text(size) if size else "—",
                path=status.env_dir,
            ))
        else:
            self.env_status.setText(S.ENV_STATUS_NONE)
        self.env_requirements.setText(S.ENV_REQUIREMENTS_FMT.format(items=requirements_text))
        self.env_uv.setText(S.ENV_UV_NOTE if uv else "")
        self.env_create_btn.setEnabled(True)
        self.env_recreate_btn.setEnabled(status.exists)
        self.env_lock_btn.setEnabled(status.exists)
        self.env_delete_btn.setEnabled(status.exists)

    def set_env_busy(self):
        """Disable the environment buttons while a command runs; the window
        re-enables the right ones through ``show_env`` when it finishes."""
        for button in (self.env_create_btn, self.env_recreate_btn,
                       self.env_lock_btn, self.env_delete_btn):
            button.setEnabled(False)

    # ── Size lab ───────────────────────────────────────────────────────────

    def _build_size_group(self) -> QGroupBox:
        group = QGroupBox(S.GROUP_SIZE)
        box = QVBoxLayout(group)
        self.size_summary = QLabel(S.SIZE_NONE)
        self.size_summary.setWordWrap(True)
        self.size_compare = _muted()
        box.addWidget(self.size_summary)
        box.addWidget(self.size_compare)

        self.breakdown = QTreeWidget()
        self.breakdown.setColumnCount(3)
        self.breakdown.setHeaderLabels([S.SIZE_COL_PACKAGE, S.SIZE_COL_SIZE, S.SIZE_COL_SHARE])
        self.breakdown.setRootIsDecorated(False)
        self.breakdown.setMinimumHeight(220)
        header = self.breakdown.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        box.addWidget(self.breakdown)

        self.size_hints = _muted()
        box.addWidget(self.size_hints)

        refresh = QPushButton(S.BTN_SIZE_REFRESH)
        refresh.setAccessibleName(S.BTN_SIZE_REFRESH)
        refresh.clicked.connect(self.window_action("analyze_last_build"))
        box.addWidget(refresh, alignment=Qt.AlignLeading)
        return group

    def show_size_report(self, report, previous_bytes: int = 0, hints=()):
        """Render a ``size_analyzer.SizeReport`` (None clears the section)."""
        self.breakdown.clear()
        if report is None or not report.ok:
            self.size_summary.setText(S.SIZE_NONE)
            self.size_compare.setText("")
            self.size_hints.setText("")
            return

        self.size_summary.setText(S.SIZE_SUMMARY_FMT.format(
            disk=size_text(report.output_bytes), content=size_text(report.content_bytes)
        ))
        if previous_bytes and report.output_bytes:
            change = (report.output_bytes - previous_bytes) * 100.0 / previous_bytes
            self.size_compare.setText(S.SIZE_COMPARE_FMT.format(
                previous=size_text(previous_bytes), change=ltr(f"{change:+.1f}%")
            ))
        else:
            self.size_compare.setText("")

        total = report.content_bytes or 1
        ranked = report.ranked()
        shown, rest = ranked[:BREAKDOWN_ROWS], ranked[BREAKDOWN_ROWS:]
        for group, size in shown:
            key = group_label_key(group)
            name = getattr(S, key) if key else group
            self._add_row(name, size, total)
        if rest:
            self._add_row(f"… (+{len(rest)})", sum(s for _g, s in rest), total)
        self.size_hints.setText("\n".join(hints))

    def _add_row(self, name: str, size: int, total: int):
        item = QTreeWidgetItem([name, size_text(size), ltr(f"{size * 100.0 / total:.1f}%")])
        item.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
        item.setTextAlignment(2, Qt.AlignRight | Qt.AlignVCenter)
        self.breakdown.addTopLevelItem(item)

    # ── Suggestions ────────────────────────────────────────────────────────

    def _build_suggestions_group(self) -> QGroupBox:
        group = QGroupBox(S.GROUP_SIZE_SUGGESTIONS)
        box = QVBoxLayout(group)
        box.addWidget(_muted(S.SIZE_SUGGESTIONS_HINT))
        self.suggestions = QListWidget()
        self.suggestions.setMinimumHeight(90)
        box.addWidget(self.suggestions)
        row = QHBoxLayout()
        self.apply_btn = QPushButton(S.BTN_SIZE_APPLY)
        self.apply_btn.clicked.connect(lambda: self._apply(rebuild=False))
        self.rebuild_btn = QPushButton(S.BTN_SIZE_APPLY_REBUILD)
        self.rebuild_btn.setObjectName("successBtn")
        self.rebuild_btn.clicked.connect(lambda: self._apply(rebuild=True))
        for button in (self.apply_btn, self.rebuild_btn):
            button.setAccessibleName(button.text())
            row.addWidget(button)
        box.addLayout(row)
        self.show_suggestions([])
        return group

    def show_suggestions(self, findings):
        self.suggestions.clear()
        if not findings:
            self.suggestions.addItem(S.SIZE_SUGGESTIONS_NONE)
            self.apply_btn.setEnabled(False)
            self.rebuild_btn.setEnabled(False)
            return
        for finding in findings:
            item = QListWidgetItem(finding_label(finding))
            item.setToolTip(finding_detail(finding))
            item.setData(FINDING_ROLE, finding)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.suggestions.addItem(item)
        self.apply_btn.setEnabled(True)
        self.rebuild_btn.setEnabled(True)

    def checked_fixes(self):
        fixes = []
        for row in range(self.suggestions.count()):
            item = self.suggestions.item(row)
            finding = item.data(FINDING_ROLE)
            if finding is not None and item.checkState() == Qt.Checked:
                fixes.extend(f for f in finding.fixes if f not in fixes)
        return fixes

    def _apply(self, rebuild: bool):
        if self.window is not None:
            self.window.apply_doctor_fixes(self.checked_fixes(), rebuild=rebuild)

    # ── Report ─────────────────────────────────────────────────────────────

    # ── Compare engines (2.0) ──────────────────────────────────────────────

    def _build_compare_group(self) -> QGroupBox:
        group = QGroupBox(S.COMPARE_GROUP)
        box = QVBoxLayout(group)
        box.addWidget(_muted(S.COMPARE_INTRO.format(folder="p2e_compare/<engine>")))

        row = QHBoxLayout()
        runs_label = QLabel(S.COMPARE_RUNS_LABEL)
        self.compare_runs = QSpinBox()
        self.compare_runs.setRange(1, 20)
        self.compare_runs.setValue(5)
        self.compare_runs.setAccessibleName(S.COMPARE_RUNS_LABEL)
        runs_label.setBuddy(self.compare_runs)
        timeout_label = QLabel(S.COMPARE_TIMEOUT_LABEL)
        self.compare_timeout = QSpinBox()
        self.compare_timeout.setRange(1, 120)
        self.compare_timeout.setValue(10)
        self.compare_timeout.setAccessibleName(S.COMPARE_TIMEOUT_LABEL)
        timeout_label.setBuddy(self.compare_timeout)
        self.compare_btn = QPushButton(S.BTN_COMPARE)
        self.compare_btn.setAccessibleName(S.BTN_COMPARE)
        self.compare_btn.clicked.connect(self.window_action("start_compare"))
        for widget in (runs_label, self.compare_runs, timeout_label, self.compare_timeout):
            row.addWidget(widget)
        row.addStretch(1)
        row.addWidget(self.compare_btn)
        box.addLayout(row)

        self.compare_table = QTableWidget(0, 0)
        self.compare_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.compare_table.setWordWrap(True)
        self.compare_table.setVisible(False)
        box.addWidget(self.compare_table)
        self.compare_result = QLabel("")
        self.compare_result.setWordWrap(True)
        self.compare_result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.compare_result.setVisible(False)
        box.addWidget(self.compare_result)
        return group

    def show_compare(self, rows, recommendation):
        """Fill the comparison table and the recommendation (None clears them)."""
        from py2exe_gui.texts import compare_table, engine_label, recommendation_lines

        if not rows:
            self.compare_table.setVisible(False)
            self.compare_result.setVisible(False)
            return
        table = compare_table(rows, isolate=True)
        self.compare_table.clear()
        self.compare_table.setColumnCount(len(rows))
        self.compare_table.setRowCount(len(table))
        self.compare_table.setHorizontalHeaderLabels([engine_label(r.engine) for r in rows])
        self.compare_table.setVerticalHeaderLabels([label for label, _cells in table])
        for i, (_label, cells) in enumerate(table):
            for j, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                self.compare_table.setItem(i, j, item)
        header = self.compare_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.compare_table.resizeRowsToContents()
        # Every row visible: the table is short, and a scroll bar inside the
        # tab's own scroll area hides the last rows.
        rows_height = sum(self.compare_table.rowHeight(i) for i in range(len(table)))
        frame = 2 * self.compare_table.frameWidth() + 16
        self.compare_table.setFixedHeight(rows_height + header.height() + frame)
        self.compare_table.setVisible(True)
        lines = recommendation_lines(recommendation, isolate=True)
        self.compare_result.setText("\n".join(lines))
        self.compare_result.setVisible(True)

    def _build_report_group(self) -> QGroupBox:
        group = QGroupBox(S.GROUP_REPORT)
        row = QHBoxLayout(group)
        self.report_auto = QCheckBox(S.REPORT_AUTO)
        self.report_auto.setChecked(True)
        self.report_open_btn = QPushButton(S.BTN_REPORT_OPEN)
        self.report_open_btn.setAccessibleName(S.BTN_REPORT_OPEN)
        self.report_open_btn.setEnabled(False)
        self.report_open_btn.clicked.connect(self.window_action("open_last_report"))
        row.addWidget(self.report_auto, stretch=1)
        row.addWidget(self.report_open_btn)
        return group

    def set_report_path(self, path: str):
        self.report_open_btn.setEnabled(bool(path) and os.path.isfile(path))
        self.report_open_btn.setToolTip(path or "")

    # ── The project model ──────────────────────────────────────────────────

    def read_project(self, project):
        project.build.isolated_env = self.isolated_radio.isChecked()

    def apply_project(self, project, sections=()):
        if "build" not in sections:
            return
        if project.build.isolated_env:
            self.isolated_radio.setChecked(True)
        else:
            self.current_radio.setChecked(True)
