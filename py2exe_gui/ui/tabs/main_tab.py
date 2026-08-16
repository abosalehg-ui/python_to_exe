"""Source file, output settings, build options and the build log."""

import os

from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
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

from py2exe_gui.core import classify_line, format_html
from py2exe_gui.strings import S
from py2exe_gui.ui.tabs.base import BaseTab, browse_button

# The sizes Windows actually pulls out of a multi-resolution .ico. Showing all
# four is how a PNG renamed to .ico gives itself away: it has only one.
ICON_PREVIEW_SIZES = (16, 32, 48, 64)


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
        self.icon_input.textChanged.connect(self.refresh_icon_preview)
        icon_btn = browse_button(S.DIALOG_CHOOSE_ICON, self.browse_icon)
        output_layout.addWidget(self.icon_input, 2, 1)
        output_layout.addWidget(icon_btn, 2, 2)

        # Icon preview: a bad .ico is one of the documented failure modes, and
        # the path alone gives no clue which sizes the file actually contains.
        output_layout.addWidget(QLabel(S.ICON_PREVIEW_LABEL), 3, 0)
        preview_row = QHBoxLayout()
        self.icon_previews = []
        for size in ICON_PREVIEW_SIZES:
            slot = QLabel()
            slot.setFixedSize(QSize(size, size))
            slot.setAlignment(Qt.AlignCenter)
            slot.setAccessibleName(f"{S.ICON_PREVIEW_LABEL} {size}px")
            preview_row.addWidget(slot)
            self.icon_previews.append((size, slot))
        self.icon_status = QLabel(S.ICON_PREVIEW_NONE)
        self.icon_status.setObjectName("aboutMuted")
        self.icon_status.setWordWrap(True)
        preview_row.addWidget(self.icon_status, stretch=1)
        output_layout.addLayout(preview_row, 3, 1, 1, 2)

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
        self.log_search.setAccessibleName(S.LOG_SEARCH_PLACEHOLDER)
        self.log_search.returnPressed.connect(self._search_log_next)
        # Debounced: searching on every keystroke made the cursor jump around.
        self._log_search_timer = QTimer(self)
        self._log_search_timer.setSingleShot(True)
        self._log_search_timer.setInterval(300)
        self._log_search_timer.timeout.connect(self._search_log_next)
        self.log_search.textChanged.connect(self._log_search_timer.start)
        search_row.addWidget(self.log_search, stretch=3)

        # Severity filter. Text search alone could not answer "just show me
        # the errors" — the word "error" does not appear in every failure.
        search_row.addWidget(QLabel(S.LOG_FILTER_LABEL))
        self.log_filter = QComboBox()
        self.log_filter.setAccessibleName(S.LOG_FILTER_LABEL)
        for label, level in (
            (S.LOG_FILTER_ALL, ""),
            (S.LOG_FILTER_ERRORS, "error"),
            (S.LOG_FILTER_WARNINGS, "warning"),
            (S.LOG_FILTER_SUCCESS, "success"),
        ):
            self.log_filter.addItem(label, level)
        self.log_filter.currentIndexChanged.connect(self._apply_log_filter)
        search_row.addWidget(self.log_filter, stretch=1)

        log_btn_row = QHBoxLayout()
        clear_log_btn = QPushButton(S.CLEAR_LOG)
        clear_log_btn.setAccessibleName(S.CLEAR_LOG)
        clear_log_btn.clicked.connect(self.clear_log)
        export_log_btn = QPushButton(S.BTN_EXPORT_LOG)
        export_log_btn.setAccessibleName(S.BTN_EXPORT_LOG)
        export_log_btn.clicked.connect(self.export_log)
        log_btn_row.addWidget(clear_log_btn)
        log_btn_row.addWidget(export_log_btn)

        log_layout.addLayout(search_row)
        log_layout.addWidget(self.log_output)
        log_layout.addLayout(log_btn_row)
        layout.addWidget(log_group)

        # Every line ever appended, with its severity. The filter re-renders
        # from this rather than trying to un-hide text already in the widget.
        self._log_lines = []
        self._log_theme = "dark"


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

    # ── Icon preview ───────────────────────────────────────────────────────

    def refresh_icon_preview(self, path: str = None):
        """Render the chosen icon at each size Windows will ask it for.

        A PNG renamed to .ico loads as a single bitmap and looks blurry in the
        small slots, which is the failure the troubleshooting section of the
        README describes. Seeing it here beats seeing it in the taskbar.
        """
        target = self.icon_input.text().strip() if path is None else str(path).strip()

        for _size, slot in self.icon_previews:
            slot.clear()

        if not target:
            self.icon_status.setText(S.ICON_PREVIEW_NONE)
            return

        if not os.path.isfile(target):
            self.icon_status.setText(S.ICON_PREVIEW_INVALID)
            return

        # QIcon.isNull() only reports whether an engine was created, not
        # whether the file decoded — a text file renamed to .ico passes it.
        # Rendering is what actually tells us, so check the pixmaps.
        icon = QIcon(target)
        rendered = []
        for size, slot in self.icon_previews:
            pixmap = icon.pixmap(QSize(size, size))
            if not pixmap.isNull():
                slot.setPixmap(pixmap)
                rendered.append(size)

        if not rendered:
            self.icon_status.setText(S.ICON_PREVIEW_INVALID)
            return
        self.icon_status.setText(os.path.basename(target))

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
        self._log_theme = theme

        if text.strip() == "":
            self._log_lines.append((text, None))
            if not self.active_log_filter():
                self.log_output.append("")
            return

        level = classify_line(text)
        self._log_lines.append((text, level))
        if self._passes_filter(level):
            self.log_output.append(format_html(text, level=level, theme=theme))

    def active_log_filter(self) -> str:
        """The severity currently selected, or '' for no filtering."""
        return self.log_filter.currentData() or ""

    def _passes_filter(self, level) -> bool:
        active = self.active_log_filter()
        return not active or level == active

    def _apply_log_filter(self, _index=None):
        """Re-render the log from the buffer under the current filter."""
        self.log_output.clear()
        active = self.active_log_filter()
        shown = 0
        for text, level in self._log_lines:
            if level is None:
                if not active:
                    self.log_output.append("")
                continue
            if self._passes_filter(level):
                self.log_output.append(
                    format_html(text, level=level, theme=self._log_theme)
                )
                shown += 1
        if active and shown == 0:
            self.log_output.append(
                format_html(S.LOG_FILTER_EMPTY, level="muted", theme=self._log_theme)
            )

    def clear_log(self):
        """Clear the widget and the buffer behind it."""
        self._log_lines = []
        self.log_output.clear()

    def log_text(self) -> str:
        """The full log as plain text, filter or no filter.

        Exporting has to write everything: exporting only the lines that
        happened to be on screen would silently drop the rest.
        """
        return "\n".join(text for text, _level in self._log_lines)

    def restore_log(self, lines):
        """Repopulate the buffer after the UI is rebuilt for a new locale."""
        self._log_lines = list(lines)
        self._apply_log_filter()

    def log_lines(self):
        """The buffer, for snapshotting across a rebuild."""
        return list(self._log_lines)

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
        """Save the whole log to a text file — not just what the filter shows."""
        contents = self.log_text()
        if not contents.strip():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, S.DIALOG_EXPORT_LOG, "py2exe_log.txt", S.DIALOG_FILTER_LOG
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(contents)
        except OSError as e:
            QMessageBox.critical(self, S.MSG_ERROR, S.LOG_EXPORT_FAIL.format(error=str(e)))
            return
        self.log(S.LOG_EXPORT_OK.format(path=path))
