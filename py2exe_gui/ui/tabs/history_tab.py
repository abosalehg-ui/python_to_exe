"""Recent builds with restore and clear actions."""

from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from py2exe_gui.strings import S
from py2exe_gui.ui.tabs.base import BaseTab


class HistoryTab(BaseTab):
    """List of recent builds with restore + clear actions."""

    def _build(self):
        layout = QVBoxLayout(self)

        group = QGroupBox(S.GROUP_HISTORY)
        group_layout = QVBoxLayout(group)

        self.history_list = QListWidget()
        self.history_list.setMinimumHeight(220)
        group_layout.addWidget(self.history_list)

        btn_row = QHBoxLayout()
        restore_btn = QPushButton(S.BTN_RESTORE_BUILD)
        restore_btn.clicked.connect(self.window_action("restore_from_history"))
        clear_btn = QPushButton(S.BTN_CLEAR_HISTORY)
        clear_btn.setObjectName("dangerBtn")
        clear_btn.clicked.connect(self.window_action("clear_history"))
        btn_row.addWidget(restore_btn)
        btn_row.addWidget(clear_btn)
        group_layout.addLayout(btn_row)

        layout.addWidget(group)


    def refresh(self, history):
        """Repopulate the list from a BuildHistory."""
        self.history_list.clear()
        if len(history) == 0:
            self.history_list.addItem(S.HISTORY_EMPTY)
            return
        for record in history.records:
            self.history_list.addItem(record.short_label())

    def selected_row(self) -> int:
        return self.history_list.currentRow()
