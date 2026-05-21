"""Reusable dialogs for the main window."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
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
