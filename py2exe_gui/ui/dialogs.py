"""Reusable dialogs for the main window."""

from py2exe_gui.qt import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    Qt,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)
from py2exe_gui.strings import S


def _inherited_direction(parent) -> Qt.LayoutDirection:
    """Layout direction of ``parent``, falling back to the application's."""
    if parent is not None:
        return parent.layoutDirection()
    app = QApplication.instance()
    return app.layoutDirection() if app else Qt.LayoutDirection.LeftToRight


class AddImportDialog(QDialog):
    """نافذة لإضافة Hidden Import."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(S.DIALOG_ADD_IMPORT_TITLE)
        self.setMinimumSize(400, 150)
        # Inherit the direction rather than forcing RTL: hardcoding it left
        # the English UI with mirrored dialogs.
        self.setLayoutDirection(_inherited_direction(parent))

        layout = QVBoxLayout(self)

        label = QLabel(S.DIALOG_ADD_IMPORT_LABEL)
        self.input = QLineEdit()
        self.input.setPlaceholderText(S.DIALOG_ADD_IMPORT_PLACEHOLDER)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(label)
        layout.addWidget(self.input)
        layout.addWidget(buttons)

    def get_value(self) -> str:
        return self.input.text().strip()


class CommandPreviewDialog(QDialog):
    """Read-only preview of the PyInstaller command that would run."""

    def __init__(self, command, parent=None):
        super().__init__(parent)
        self.setWindowTitle(S.DIALOG_PREVIEW_TITLE)
        self.setMinimumSize(640, 320)
        self.setLayoutDirection(_inherited_direction(parent))

        self._command_text = " ".join(command)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(S.DIALOG_PREVIEW_HINT))

        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.text_view.setPlainText(self._command_text)
        layout.addWidget(self.text_view)

        btn_row = QHBoxLayout()
        copy_btn = QPushButton(S.BTN_COPY_CMD)
        copy_btn.clicked.connect(self._copy_to_clipboard)
        close_btn = QPushButton(S.BTN_CLOSE)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(copy_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _copy_to_clipboard(self):
        QApplication.clipboard().setText(self._command_text)
        # Brief visual feedback in window title.
        self.setWindowTitle(f"{S.DIALOG_PREVIEW_TITLE} — {S.MSG_COPIED}")


class ShortcutsDialog(QDialog):
    """Every keyboard shortcut, from the same table the window binds.

    The shortcuts were documented only in the README; a window that binds
    twenty of them should be able to show them.
    """

    def __init__(self, rows, parent=None):
        super().__init__(parent)
        self.setWindowTitle(S.SHORTCUTS_TITLE)
        self.setMinimumSize(460, 420)
        self.setLayoutDirection(_inherited_direction(parent))
        layout = QVBoxLayout(self)
        hint = QLabel(S.SHORTCUTS_HINT)
        hint.setObjectName("aboutMuted")
        layout.addWidget(hint)

        self.table = QTableWidget(len(rows), 2)
        self.table.setObjectName("shortcutsTable")
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setShowGrid(False)
        self.table.setAccessibleName(S.SHORTCUTS_TITLE)
        for row, (keys, description) in enumerate(rows):
            key_item = QTableWidgetItem(keys)
            key_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 0, key_item)
            self.table.setItem(row, 1, QTableWidgetItem(description))
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        close_btn = QPushButton(S.BTN_CLOSE)
        close_btn.setAccessibleName(S.BTN_CLOSE)
        close_btn.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def rows(self):
        return [(self.table.item(r, 0).text(), self.table.item(r, 1).text())
                for r in range(self.table.rowCount())]


class PresetNameDialog(QDialog):
    """Ask for a name to store the current settings under."""

    def __init__(self, parent=None, initial: str = ""):
        super().__init__(parent)
        self.setWindowTitle(S.BTN_PRESET_SAVE)
        self.setMinimumWidth(400)
        self.setLayoutDirection(_inherited_direction(parent))

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(S.PRESET_NAME_PROMPT))

        self.input = QLineEdit(initial)
        self.input.setAccessibleName(S.PRESET_NAME_PROMPT)
        layout.addWidget(self.input)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_value(self) -> str:
        return self.input.text().strip()


class ReleaseConfirmDialog(QDialog):
    """The last word before a release: everything it will create, run,
    commit, tag, push and upload, listed in full."""

    def __init__(self, summary, version: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(S.RELEASE_CONFIRM_TITLE)
        self.setMinimumSize(640, 460)
        self.setLayoutDirection(_inherited_direction(parent))

        layout = QVBoxLayout(self)
        heading = QLabel(S.RELEASE_CONFIRM_HEADING.format(version=_ltr(version)))
        heading.setWordWrap(True)
        heading.setObjectName("aboutHeading")
        layout.addWidget(heading)

        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setPlainText(self.summary_text(summary))
        layout.addWidget(self.text_view)

        note = QLabel(S.RELEASE_CONFIRM_NOTE)
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QDialogButtonBox()
        self.release_btn = buttons.addButton(S.BTN_CONFIRM_RELEASE, QDialogButtonBox.ButtonRole.AcceptRole)
        self.release_btn.setObjectName("successBtn")
        buttons.addButton(S.BTN_CANCEL_RELEASE, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def summary_text(summary) -> str:
        sections = (
            (S.RELEASE_CONFIRM_CREATED, summary.created),
            (S.RELEASE_CONFIRM_COMMANDS, summary.commands),
            (S.RELEASE_CONFIRM_COMMITS, summary.commits),
            (S.RELEASE_CONFIRM_TAGS, summary.tags),
            (S.RELEASE_CONFIRM_PUSHES, summary.pushes),
            (S.RELEASE_CONFIRM_RELEASES, summary.releases),
            (S.RELEASE_CONFIRM_UPLOADS, summary.uploads),
        )
        blocks = []
        for title, items in sections:
            if items:
                # Paths, commands and URLs read left to right inside RTL text.
                blocks.append("\n".join([title] + [f"  • {_ltr(item)}" for item in items]))
        return "\n\n".join(blocks) or S.RELEASE_CONFIRM_NOTHING


class CiPreviewDialog(QDialog):
    """The whole GitHub Actions workflow, before a byte of it is written.

    The text is read-only and left-to-right (it is YAML), the path it goes to
    is shown in full, an existing file is flagged, and the secrets the file
    names are listed — by name, which is all the file ever holds of them.
    """

    def __init__(self, text: str, path: str, exists: bool, secrets, parent=None):
        super().__init__(parent)
        self.setWindowTitle(S.CI_DIALOG_TITLE)
        self.setMinimumSize(760, 560)
        self.setLayoutDirection(_inherited_direction(parent))
        self._text = text

        layout = QVBoxLayout(self)
        heading = QLabel(S.CI_DIALOG_HEADING.format(path=_ltr(path)))
        heading.setWordWrap(True)
        heading.setObjectName("aboutHeading")
        heading.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(heading)
        if exists:
            warning = QLabel(S.CI_DIALOG_OVERWRITE_NOTE)
            warning.setObjectName("warningNotice")
            warning.setWordWrap(True)
            layout.addWidget(warning)

        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.text_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.text_view.setPlainText(text)
        self.text_view.setAccessibleName(S.CI_DIALOG_TITLE)
        layout.addWidget(self.text_view, 1)

        secrets_note = QLabel(S.CI_DIALOG_SECRETS.format(names=_ltr(", ".join(secrets)))
                              if secrets else S.CI_DIALOG_NO_SECRETS)
        secrets_note.setWordWrap(True)
        layout.addWidget(secrets_note)
        note = QLabel(S.CI_DIALOG_NOTE)
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QDialogButtonBox()
        copy_btn = buttons.addButton(S.BTN_COPY_WORKFLOW, QDialogButtonBox.ButtonRole.ActionRole)
        copy_btn.clicked.connect(self._copy_to_clipboard)
        self.write_btn = buttons.addButton(S.BTN_WRITE_WORKFLOW, QDialogButtonBox.ButtonRole.AcceptRole)
        self.write_btn.setObjectName("successBtn")
        buttons.addButton(S.BTN_CANCEL_WORKFLOW, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _copy_to_clipboard(self):
        QApplication.clipboard().setText(self._text)
        self.setWindowTitle(f"{S.CI_DIALOG_TITLE} — {S.MSG_COPIED}")


def _ltr(text: str) -> str:
    return f"⁦{text}⁩"
