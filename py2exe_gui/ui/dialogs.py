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


class AddImportDialog(QDialog):
    """نافذة لإضافة Hidden Import."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(S.DIALOG_ADD_IMPORT_TITLE)
        self.setFixedSize(400, 150)
        self.setLayoutDirection(Qt.RightToLeft)

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
        self.setMinimumSize(720, 360)
        self.setLayoutDirection(Qt.RightToLeft)

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
