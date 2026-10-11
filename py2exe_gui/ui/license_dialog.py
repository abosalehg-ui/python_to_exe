"""The licence generator: who, which product, until when, which features → a key.

The dialog is UI only. It gets an ``issue`` callable from the window (which
holds the private key's path) and shows what comes back; validation
problems from ``core/licensing.py`` are rendered through ``strings``.
"""

import datetime
from typing import Callable, Optional

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from py2exe_gui.core.licensing import LicenseRequest, parse_features, validate_request
from py2exe_gui.strings import S
from py2exe_gui.ui.dialogs import _inherited_direction
from py2exe_gui.ui.tabs.runtime_tab import bidi, code_run
from py2exe_gui.ui.tabs.size_tab import ltr

#: ``issue(request) -> key text``; raises ``ValueError`` for a bad request.
Issuer = Callable[[LicenseRequest], str]


def problem_text(code: str, value: str) -> str:
    """One validation problem from ``core/licensing`` in the active locale."""
    template = getattr(S, f"LICENSE_ERR_{code.upper()}", code)
    try:
        return template.format(value=value)
    except (KeyError, IndexError):
        return template


class LicenseGeneratorDialog(QDialog):
    """Fields for one licence; *Issue the key* fills the read-only key box."""

    def __init__(self, issue: Issuer, product: str = "", parent=None,
                 today: Optional[datetime.date] = None):
        super().__init__(parent)
        self._issue = issue
        self._today = today or datetime.date.today()
        self.key_text = ""
        self.setWindowTitle(S.LICENSE_DIALOG_TITLE)
        self.setMinimumSize(640, 520)
        self.setLayoutDirection(_inherited_direction(parent))

        layout = QVBoxLayout(self)
        heading = QLabel(bidi(S.LICENSE_DIALOG_HEADING))
        heading.setWordWrap(True)
        heading.setObjectName("aboutHeading")
        layout.addWidget(heading)

        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.email_edit.setLayoutDirection(Qt.LeftToRight)
        self.product_edit = QLineEdit(product)
        self.product_edit.setLayoutDirection(Qt.LeftToRight)
        self.features_edit = QLineEdit()
        self.features_edit.setPlaceholderText(bidi(S.LICENSE_FEATURES_PLACEHOLDER))
        self.features_edit.setLayoutDirection(Qt.LeftToRight)

        expiry_row = QHBoxLayout()
        self.expiry_edit = QDateEdit()
        self.expiry_edit.setCalendarPopup(True)
        self.expiry_edit.setDisplayFormat("yyyy-MM-dd")
        self.expiry_edit.setLayoutDirection(Qt.LeftToRight)
        in_a_year = self._today + datetime.timedelta(days=365)
        self.expiry_edit.setDate(QDate(in_a_year.year, in_a_year.month, in_a_year.day))
        self.no_expiry = QCheckBox(bidi(S.LICENSE_NO_EXPIRY_CHECK))
        self.no_expiry.setChecked(True)
        self.no_expiry.toggled.connect(lambda on: self.expiry_edit.setEnabled(not on))
        self.expiry_edit.setEnabled(False)
        expiry_row.addWidget(self.expiry_edit)
        expiry_row.addWidget(self.no_expiry)
        expiry_row.addStretch(1)

        form.addRow(bidi(S.LICENSE_NAME_LABEL), self.name_edit)
        form.addRow(bidi(S.LICENSE_EMAIL_LABEL), self.email_edit)
        form.addRow(bidi(S.LICENSE_PRODUCT_LABEL), self.product_edit)
        form.addRow(bidi(S.LICENSE_EXPIRY_LABEL), expiry_row)
        form.addRow(bidi(S.LICENSE_FEATURES_LABEL), self.features_edit)
        for label, widget in ((S.LICENSE_NAME_LABEL, self.name_edit),
                              (S.LICENSE_EMAIL_LABEL, self.email_edit),
                              (S.LICENSE_PRODUCT_LABEL, self.product_edit),
                              (S.LICENSE_FEATURES_LABEL, self.features_edit)):
            widget.setAccessibleName(label)
        layout.addLayout(form)

        self.issue_btn = QPushButton(S.BTN_LICENSE_ISSUE)
        self.issue_btn.setObjectName("successBtn")
        self.issue_btn.setAccessibleName(S.BTN_LICENSE_ISSUE)
        self.issue_btn.clicked.connect(self.issue)
        layout.addWidget(self.issue_btn, alignment=Qt.AlignLeading)

        self.problems = QLabel()
        self.problems.setObjectName("warningNotice")
        self.problems.setWordWrap(True)
        self.problems.setVisible(False)
        layout.addWidget(self.problems)

        self.result = QLabel()
        self.result.setWordWrap(True)
        self.result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.result)
        self.key_label = QLabel(bidi(S.LICENSE_KEY_LABEL))
        layout.addWidget(self.key_label)
        self.key_view = QPlainTextEdit()
        self.key_view.setObjectName("codeView")
        self.key_view.setReadOnly(True)
        self.key_view.setLayoutDirection(Qt.LeftToRight)
        self.key_view.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.key_view.setAccessibleName(S.LICENSE_KEY_LABEL)
        self.key_view.setMinimumHeight(90)
        layout.addWidget(self.key_view, 1)

        honesty = QLabel(bidi(S.KIT_LICENSE_HONESTY))
        honesty.setObjectName("aboutMuted")
        honesty.setWordWrap(True)
        layout.addWidget(honesty)

        buttons = QDialogButtonBox()
        self.copy_btn = buttons.addButton(S.BTN_LICENSE_COPY, QDialogButtonBox.ActionRole)
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self.copy_key)
        buttons.addButton(S.BTN_LICENSE_CLOSE, QDialogButtonBox.RejectRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ── Reading the form ───────────────────────────────────────────────────

    def expiry(self) -> str:
        if self.no_expiry.isChecked():
            return ""
        return self.expiry_edit.date().toString("yyyy-MM-dd")

    def request(self) -> LicenseRequest:
        return LicenseRequest(
            name=self.name_edit.text().strip(),
            email=self.email_edit.text().strip(),
            product=self.product_edit.text().strip(),
            expiry=self.expiry(),
            features=parse_features(self.features_edit.text()),
        )

    # ── Issuing ────────────────────────────────────────────────────────────

    def issue(self):
        request = self.request()
        problems = validate_request(request, self._today)
        if problems:
            self._show_problems([problem_text(code, value) for code, value in problems])
            return
        try:
            text = self._issue(request)
        except (OSError, ValueError) as e:
            self._show_problems([str(e)])
            return
        self.key_text = text
        self.problems.setVisible(False)
        self.key_view.setPlainText(text)
        self.copy_btn.setEnabled(True)
        expiry = request.expiry or S.KIT_LICENSE_NO_EXPIRY
        self.result.setText(bidi(S.LICENSE_RESULT_FMT).format(
            name=request.name, product=code_run(request.product), expiry=ltr(expiry),
            count=ltr(str(len(request.features))), length=ltr(str(len(text))),
        ))

    def _show_problems(self, lines):
        self.key_text = ""
        self.key_view.setPlainText("")
        self.copy_btn.setEnabled(False)
        self.result.setText("")
        self.problems.setText("\n".join(f"• {bidi(line)}" for line in lines))
        self.problems.setVisible(True)

    def copy_key(self):
        if self.key_text:
            QApplication.clipboard().setText(self.key_text)
            self.setWindowTitle(f"{S.LICENSE_DIALOG_TITLE} — {S.MSG_LICENSE_COPIED}")
