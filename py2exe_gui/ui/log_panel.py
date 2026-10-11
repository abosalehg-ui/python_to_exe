"""The build log, as a panel under the pages rather than a box inside one tab.

Before 2.1 the log sat inside the main tab, where it took a third of the tab
while empty and vanished as soon as the person looked at another tab during
a build. As a bottom panel it is reachable from every section, opens itself
when a build starts, and folds to a single line (the last message) when
nothing is happening.

The buffer-and-filter logic moved here from ``MainTab`` unchanged: every
line ever appended is kept with its severity, and the widget is re-rendered
from that buffer when the filter or the theme changes.
"""

from py2exe_gui.core.log_formatter import classify_line, format_html
from py2exe_gui.qt import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    Qt,
    QTextEdit,
    QTimer,
    QToolButton,
    QVBoxLayout,
    QWidget,
    Signal,
)
from py2exe_gui.strings import S

#: The least the log area may be squeezed to while the panel is open.
MIN_OPEN_HEIGHT = 80


class LogPanel(QWidget):
    """Header row (toggle, title, last line, search, filter, actions) + log."""

    toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("logPanel")
        # Every line ever appended, with its severity. The filter re-renders
        # from this rather than trying to un-hide text already in the widget.
        self._log_lines = []
        self._log_theme = "dark"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("logHeader")
        row = QHBoxLayout(header)
        row.setContentsMargins(8, 2, 8, 2)
        row.setSpacing(8)

        self.toggle_btn = QToolButton()
        self.toggle_btn.setObjectName("logToggle")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_btn.setText(S.LOG_PANEL_TITLE)
        self.toggle_btn.setAccessibleName(S.LOG_PANEL_TITLE)
        self.toggle_btn.setToolTip(S.LOG_PANEL_TOGGLE_TIP)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.toggled.connect(self._on_toggled)
        row.addWidget(self.toggle_btn)

        # The newest line, so a closed panel still reports what just happened.
        self.last_label = QLabel(S.LOG_PANEL_EMPTY)
        self.last_label.setObjectName("logLastLine")
        self.last_label.setTextFormat(Qt.TextFormat.PlainText)
        self.last_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.last_label.setAccessibleName(S.LOG_PANEL_TITLE)
        row.addWidget(self.last_label, 1)

        self.log_search = QLineEdit()
        self.log_search.setPlaceholderText(S.LOG_SEARCH_PLACEHOLDER)
        self.log_search.setAccessibleName(S.LOG_SEARCH_PLACEHOLDER)
        self.log_search.setClearButtonEnabled(True)
        self.log_search.setMaximumWidth(220)
        self.log_search.returnPressed.connect(self._search_log_next)
        # Debounced: searching on every keystroke made the cursor jump around.
        self._log_search_timer = QTimer(self)
        self._log_search_timer.setSingleShot(True)
        self._log_search_timer.setInterval(300)
        self._log_search_timer.timeout.connect(self._search_log_next)
        self.log_search.textChanged.connect(self._log_search_timer.start)
        row.addWidget(self.log_search)

        # Severity filter. Text search alone could not answer "just show me
        # the errors" — the word "error" does not appear in every failure.
        self.log_filter = QComboBox()
        self.log_filter.setAccessibleName(S.LOG_FILTER_LABEL)
        self.log_filter.setToolTip(S.LOG_FILTER_LABEL)
        for label, level in (
            (S.LOG_FILTER_ALL, ""),
            (S.LOG_FILTER_ERRORS, "error"),
            (S.LOG_FILTER_WARNINGS, "warning"),
            (S.LOG_FILTER_SUCCESS, "success"),
        ):
            self.log_filter.addItem(label, level)
        self.log_filter.currentIndexChanged.connect(self._apply_log_filter)
        row.addWidget(self.log_filter)

        self.clear_btn = QPushButton(S.CLEAR_LOG)
        self.clear_btn.setObjectName("flatBtn")
        self.clear_btn.setProperty("iconName", "clear")
        self.clear_btn.setAccessibleName(S.CLEAR_LOG)
        self.clear_btn.clicked.connect(self.clear_log)
        row.addWidget(self.clear_btn)
        self.export_btn = QPushButton(S.BTN_EXPORT_LOG)
        self.export_btn.setObjectName("flatBtn")
        self.export_btn.setProperty("iconName", "export")
        self.export_btn.setAccessibleName(S.BTN_EXPORT_LOG)
        self.export_btn.clicked.connect(self.export_log)
        row.addWidget(self.export_btn)
        layout.addWidget(header)

        self.log_output = QTextEdit()
        self.log_output.setObjectName("logOutput")
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(MIN_OPEN_HEIGHT)
        self.log_output.setAccessibleName(S.LOG_PANEL_TITLE)
        layout.addWidget(self.log_output)

        self.toggle_btn.setChecked(False)
        self._on_toggled(False)

    # ── Open / closed ──────────────────────────────────────────────────────

    def is_expanded(self) -> bool:
        return self.toggle_btn.isChecked()

    def set_expanded(self, expanded: bool):
        if self.toggle_btn.isChecked() != bool(expanded):
            self.toggle_btn.setChecked(bool(expanded))

    def _on_toggled(self, checked: bool):
        self.log_output.setVisible(checked)
        for widget in (self.log_search, self.log_filter, self.clear_btn, self.export_btn):
            widget.setVisible(checked)
        self.last_label.setVisible(not checked)
        self._update_arrow()
        self.toggled.emit(checked)

    def set_chevrons(self, open_icon, closed_icon):
        """Theme-coloured icons for the toggle instead of the style's arrows."""
        self._chevrons = (open_icon, closed_icon)
        self._update_arrow()

    def _update_arrow(self):
        chevrons = getattr(self, "_chevrons", None)
        checked = self.toggle_btn.isChecked()
        if chevrons is not None:
            self.toggle_btn.setArrowType(Qt.ArrowType.NoArrow)
            self.toggle_btn.setIcon(chevrons[0] if checked else chevrons[1])
            return
        self.toggle_btn.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.UpArrow
        )

    # ── Appending and filtering ────────────────────────────────────────────

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
        self._show_last(text)

    def _show_last(self, text: str):
        first = text.strip().splitlines()[0] if text.strip() else ""
        self.last_label.setText(first or S.LOG_PANEL_EMPTY)

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

    def set_theme(self, theme: str):
        """Re-render buffered lines in the new theme's palette."""
        self._log_theme = theme
        self._apply_log_filter()

    def clear_log(self):
        """Clear the widget and the buffer behind it."""
        self._log_lines = []
        self.log_output.clear()
        self.last_label.setText(S.LOG_PANEL_EMPTY)

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
        for text, _level in reversed(self._log_lines):
            if text.strip():
                self._show_last(text)
                break

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
            cursor.movePosition(cursor.MoveOperation.Start)
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
        self.append_log(S.LOG_EXPORT_OK.format(path=path), theme=self._log_theme)
