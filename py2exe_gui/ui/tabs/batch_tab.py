"""Queue several .py files and build them all with the current settings."""

import os

from PyQt5.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from py2exe_gui.core.batch_runner import make_jobs, summarize
from py2exe_gui.strings import S
from py2exe_gui.ui.tabs.base import BaseTab


class BatchTab(BaseTab):
    """The file queue, its controls, and the summary of the last run."""

    def _build(self):
        layout = QVBoxLayout(self)

        files_group = QGroupBox(S.GROUP_BATCH_FILES)
        files_layout = QVBoxLayout(files_group)

        hint = QLabel(S.BATCH_HINT)
        hint.setWordWrap(True)
        files_layout.addWidget(hint)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.file_list.setAccessibleName(S.GROUP_BATCH_FILES)
        self.file_list.setMinimumHeight(160)
        files_layout.addWidget(self.file_list)

        button_row = QHBoxLayout()
        for label, handler in (
            (S.BTN_BATCH_ADD, self.add_files),
            (S.BTN_BATCH_REMOVE, self.remove_selected),
            (S.BTN_BATCH_CLEAR, self.clear_files),
        ):
            button = QPushButton(label)
            button.setAccessibleName(label)
            button.clicked.connect(handler)
            button_row.addWidget(button)
        files_layout.addLayout(button_row)
        layout.addWidget(files_group)

        action_row = QHBoxLayout()
        self.start_btn = QPushButton(S.BTN_BATCH_START)
        self.start_btn.setObjectName("successBtn")
        self.start_btn.setAccessibleName(S.BTN_BATCH_START)
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self.window_action("start_batch_conversion"))

        self.cancel_btn = QPushButton(S.BTN_BATCH_CANCEL)
        self.cancel_btn.setObjectName("dangerBtn")
        self.cancel_btn.setAccessibleName(S.BTN_BATCH_CANCEL)
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.window_action("cancel_batch_conversion"))

        action_row.addWidget(self.start_btn)
        action_row.addWidget(self.cancel_btn)
        layout.addLayout(action_row)

        result_group = QGroupBox(S.GROUP_BATCH_RESULT)
        result_layout = QVBoxLayout(result_group)
        self.summary_label = QLabel(S.BATCH_EMPTY)
        self.summary_label.setWordWrap(True)
        self.summary_label.setAccessibleName(S.GROUP_BATCH_RESULT)
        result_layout.addWidget(self.summary_label)
        layout.addWidget(result_group)

        layout.addStretch()

    # ── Queue management ───────────────────────────────────────────────────

    def add_files(self):
        settings = self.window.settings if self.window else {}
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            S.DIALOG_CHOOSE_BATCH_FILES,
            settings.get("last_source_dir", ""),
            S.DIALOG_FILTER_PY,
        )
        if not paths:
            return
        settings["last_source_dir"] = os.path.dirname(paths[0])
        self.set_sources(self.sources() + list(paths))

    def remove_selected(self):
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))
        self._reset_summary()

    def clear_files(self):
        self.file_list.clear()
        self._reset_summary()

    def sources(self):
        """Every queued path, in order."""
        return [
            self.file_list.item(i).data(256) or self.file_list.item(i).text()
            for i in range(self.file_list.count())
        ]

    def set_sources(self, paths):
        """Replace the queue, dropping duplicates via ``make_jobs``."""
        self.file_list.clear()
        for job in make_jobs(paths):
            self._add_row(job)
        self._reset_summary()

    def _add_row(self, job):
        self.file_list.addItem(job.source)
        item = self.file_list.item(self.file_list.count() - 1)
        # Qt.UserRole == 256: keep the real path even once the row shows status.
        item.setData(256, job.source)

    def jobs(self):
        """Fresh job objects for the current queue."""
        return make_jobs(self.sources())

    # ── Run feedback ───────────────────────────────────────────────────────

    def set_running(self, running: bool):
        self.start_btn.setEnabled(not running)
        self.cancel_btn.setEnabled(running)

    def update_row(self, index: int, job):
        """Repaint a single row with the job's current status marker."""
        item = self.file_list.item(index)
        if item is not None:
            item.setText(f"{job.label()}  —  {job.source}")

    def show_summary(self, jobs):
        summary = summarize(jobs)
        text = S.BATCH_SUMMARY_FMT.format(
            total=summary.total,
            succeeded=summary.succeeded,
            failed=summary.failed,
            cancelled=summary.cancelled,
            duration=round(summary.duration_seconds, 1),
        )
        if summary.failures:
            text += "\n" + S.BATCH_FAILURES_FMT.format(names=", ".join(summary.failures))
        self.summary_label.setText(text)

    def _reset_summary(self):
        self.summary_label.setText(
            S.BATCH_EMPTY if self.file_list.count() == 0 else ""
        )
