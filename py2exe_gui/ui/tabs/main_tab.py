"""Source file, output settings, build options and the build log."""

import os

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from py2exe_gui.core import format_html
from py2exe_gui.strings import S
from py2exe_gui.ui.tabs.base import BaseTab, browse_button


class MainTab(BaseTab):
    """The primary tab: what to build, and what happened when it ran."""

    def _build(self):
        layout = QVBoxLayout(self)

        source_group = QGroupBox(S.GROUP_SOURCE)
        source_layout = QHBoxLayout(source_group)
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText(S.SOURCE_PLACEHOLDER)
        self.source_input.textChanged.connect(self.on_source_changed)
        source_btn = browse_button(S.DIALOG_CHOOSE_PY, self.browse_source)
        source_layout.addWidget(self.source_input, stretch=4)
        source_layout.addWidget(source_btn, stretch=1)
        layout.addWidget(source_group)

        output_group = QGroupBox(S.GROUP_OUTPUT)
        output_layout = QGridLayout(output_group)

        output_layout.addWidget(QLabel(S.OUTPUT_NAME_LABEL), 0, 0)
        self.output_name = QLineEdit()
        self.output_name.setPlaceholderText(S.OUTPUT_NAME_PLACEHOLDER)
        output_layout.addWidget(self.output_name, 0, 1)

        output_layout.addWidget(QLabel(S.OUTPUT_DIR_LABEL), 1, 0)
        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText(S.OUTPUT_DIR_PLACEHOLDER)
        output_dir_btn = browse_button(S.DIALOG_CHOOSE_OUT_DIR, self.browse_output_dir)
        output_layout.addWidget(self.output_dir, 1, 1)
        output_layout.addWidget(output_dir_btn, 1, 2)

        output_layout.addWidget(QLabel(S.ICON_LABEL), 2, 0)
        self.icon_input = QLineEdit()
        self.icon_input.setPlaceholderText(S.ICON_PLACEHOLDER)
        icon_btn = browse_button(S.DIALOG_CHOOSE_ICON, self.browse_icon)
        output_layout.addWidget(self.icon_input, 2, 1)
        output_layout.addWidget(icon_btn, 2, 2)

        layout.addWidget(output_group)

        options_group = QGroupBox(S.GROUP_OPTIONS)
        options_layout = QVBoxLayout(options_group)

        row1 = QHBoxLayout()
        self.onefile_check = QCheckBox(S.OPT_ONEFILE)
        self.onefile_check.setChecked(True)
        self.onefile_check.setToolTip(S.OPT_ONEFILE_TIP)
        self.windowed_check = QCheckBox(S.OPT_WINDOWED)
        self.windowed_check.setToolTip(S.OPT_WINDOWED_TIP)
        self.clean_check = QCheckBox(S.OPT_CLEAN)
        self.clean_check.setChecked(True)
        self.clean_check.setToolTip(S.OPT_CLEAN_TIP)
        row1.addWidget(self.onefile_check)
        row1.addWidget(self.windowed_check)
        row1.addWidget(self.clean_check)

        row2 = QHBoxLayout()
        self.noconsole_check = QCheckBox(S.OPT_NOCONSOLE)
        self.noconsole_check.setToolTip(S.OPT_NOCONSOLE_TIP)
        self.noconfirm_check = QCheckBox(S.OPT_NOCONFIRM)
        self.noconfirm_check.setChecked(True)
        self.noconfirm_check.setToolTip(S.OPT_NOCONFIRM_TIP)
        self.strip_check = QCheckBox(S.OPT_STRIP)
        self.strip_check.setToolTip(S.OPT_STRIP_TIP)
        row2.addWidget(self.noconsole_check)
        row2.addWidget(self.noconfirm_check)
        row2.addWidget(self.strip_check)

        options_layout.addLayout(row1)
        options_layout.addLayout(row2)
        layout.addWidget(options_group)

        log_group = QGroupBox(S.GROUP_LOG)
        log_layout = QVBoxLayout(log_group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(150)

        search_row = QHBoxLayout()
        self.log_search = QLineEdit()
        self.log_search.setPlaceholderText(S.LOG_SEARCH_PLACEHOLDER)
        self.log_search.returnPressed.connect(self._search_log_next)
        # Debounced: searching on every keystroke made the cursor jump around.
        self._log_search_timer = QTimer(self)
        self._log_search_timer.setSingleShot(True)
        self._log_search_timer.setInterval(300)
        self._log_search_timer.timeout.connect(self._search_log_next)
        self.log_search.textChanged.connect(self._log_search_timer.start)
        search_row.addWidget(self.log_search)

        log_btn_row = QHBoxLayout()
        clear_log_btn = QPushButton(S.CLEAR_LOG)
        clear_log_btn.clicked.connect(self.log_output.clear)
        export_log_btn = QPushButton(S.BTN_EXPORT_LOG)
        export_log_btn.clicked.connect(self.export_log)
        log_btn_row.addWidget(clear_log_btn)
        log_btn_row.addWidget(export_log_btn)

        log_layout.addLayout(search_row)
        log_layout.addWidget(self.log_output)
        log_layout.addLayout(log_btn_row)
        layout.addWidget(log_group)


    # ── Browsing ───────────────────────────────────────────────────────────

    def browse_source(self):
        settings = self.window.settings if self.window else {}
        path = self._choose_file(
            S.DIALOG_CHOOSE_PY, S.DIALOG_FILTER_PY, settings.get("last_source_dir", "")
        )
        if path:
            self.source_input.setText(path)
            settings["last_source_dir"] = os.path.dirname(path)

    def browse_output_dir(self):
        settings = self.window.settings if self.window else {}
        path = self._choose_dir(
            S.DIALOG_CHOOSE_OUT_DIR, settings.get("last_output_dir", "")
        )
        if path:
            self.output_dir.setText(path)
            settings["last_output_dir"] = path

    def browse_icon(self):
        path = self._choose_file(S.DIALOG_CHOOSE_ICON, S.DIALOG_FILTER_ICON)
        if path:
            self.icon_input.setText(path)

    def on_source_changed(self, text):
        """Prefill the output name and directory from the chosen script."""
        if text and os.path.isfile(text):
            base_name = os.path.splitext(os.path.basename(text))[0]
            if not self.output_name.text():
                self.output_name.setText(base_name)
            if not self.output_dir.text():
                self.output_dir.setText(os.path.dirname(text))

    # ── Log ────────────────────────────────────────────────────────────────

    def append_log(self, line: str, theme: str = "dark"):
        """Append one line, coloured by severity for the active theme."""
        if line is None:
            return
        text = str(line)
        if text.strip() == "":
            self.log_output.append("")
            return
        self.log_output.append(format_html(text, theme=theme))

    def _search_log_next(self):
        """Find the next occurrence of the search query in the log."""
        query = self.log_search.text().strip()
        if not query:
            return
        if not self.log_output.find(query):
            cursor = self.log_output.textCursor()
            cursor.movePosition(cursor.Start)
            self.log_output.setTextCursor(cursor)
            self.log_output.find(query)

    def export_log(self):
        """Save the current log contents to a text file."""
        if not self.log_output.toPlainText().strip():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, S.DIALOG_EXPORT_LOG, "py2exe_log.txt", S.DIALOG_FILTER_LOG
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log_output.toPlainText())
        except OSError as e:
            QMessageBox.critical(self, S.MSG_ERROR, S.LOG_EXPORT_FAIL.format(error=str(e)))
            return
        self.log(S.LOG_EXPORT_OK.format(path=path))
