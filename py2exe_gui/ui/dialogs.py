"""Reusable dialogs for the main window."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from py2exe_gui.strings import S


def _inherited_direction(parent) -> Qt.LayoutDirection:
    """Layout direction of ``parent``, falling back to the application's."""
    if parent is not None:
        return parent.layoutDirection()
    app = QApplication.instance()
    return app.layoutDirection() if app else Qt.LeftToRight


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

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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
        self.text_view.setLayoutDirection(Qt.LeftToRight)
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


class WelcomeDialog(QDialog):
    """First-run mode picker.

    Eight tabs of PyInstaller options is a lot to meet at once when all you
    wanted was to turn one script into an .exe. This asks, once, which of the
    two tab sets to show, and the answer is remembered.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(S.WELCOME_TITLE)
        self.setMinimumWidth(480)
        self.setLayoutDirection(_inherited_direction(parent))
        # Records the choice; simple mode is the default if the dialog is
        # dismissed with the window close button.
        self.simple_mode = True

        layout = QVBoxLayout(self)

        heading = QLabel(S.WELCOME_TITLE)
        heading.setObjectName("aboutHeading")
        layout.addWidget(heading)

        body = QLabel(S.WELCOME_BODY)
        body.setObjectName("aboutBody")
        body.setWordWrap(True)
        layout.addWidget(body)

        btn_row = QHBoxLayout()
        simple_btn = QPushButton(S.WELCOME_CHOOSE_SIMPLE)
        simple_btn.setObjectName("successBtn")
        simple_btn.setAccessibleName(S.WELCOME_CHOOSE_SIMPLE)
        simple_btn.clicked.connect(self._choose_simple)

        advanced_btn = QPushButton(S.WELCOME_CHOOSE_ADVANCED)
        advanced_btn.setAccessibleName(S.WELCOME_CHOOSE_ADVANCED)
        advanced_btn.clicked.connect(self._choose_advanced)

        btn_row.addWidget(simple_btn)
        btn_row.addWidget(advanced_btn)
        layout.addLayout(btn_row)

    def _choose_simple(self):
        self.simple_mode = True
        self.accept()

    def _choose_advanced(self):
        self.simple_mode = False
        self.accept()


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

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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
        self.release_btn = buttons.addButton(S.BTN_CONFIRM_RELEASE, QDialogButtonBox.AcceptRole)
        self.release_btn.setObjectName("successBtn")
        buttons.addButton(S.BTN_CANCEL_RELEASE, QDialogButtonBox.RejectRole)
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


def _ltr(text: str) -> str:
    return f"⁦{text}⁩"
