"""Shared plumbing for the tab widgets.

`main_window.py` used to build all eight tabs inline and own every widget,
which is how it reached 1,900 lines. Each tab is now a self-contained widget
that owns its own controls and the browse handlers that belong to it; the
window keeps orchestration (threads, the build pipeline, shortcuts).
"""

from PyQt5.QtWidgets import (
    QFileDialog,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


def browse_button(label: str, handler) -> QPushButton:
    """A '📂' button that screen readers and tooltips can actually describe.

    Emoji-only buttons expose no accessible name of their own, so several
    identical '📂' buttons were indistinguishable to assistive technology and
    to anyone navigating by keyboard.
    """
    button = QPushButton("📂")
    button.setToolTip(label)
    button.setAccessibleName(label)
    button.setAccessibleDescription(label)
    button.clicked.connect(handler)
    return button


class BaseTab(QWidget):
    """Base class for every tab.

    Subclasses implement ``_build()`` and populate ``self`` with their
    widgets. ``window`` is the owning MainWindow, used for logging and for
    the few actions that span tabs.
    """

    def __init__(self, window=None, parent=None):
        super().__init__(parent)
        self.window = window
        self._build()

    def _build(self):  # pragma: no cover - abstract
        raise NotImplementedError

    # ── Helpers available to every tab ─────────────────────────────────────

    def log(self, message: str):
        """Append a line to the shared build log, if the window is attached."""
        if self.window is not None:
            self.window._append_log(message)

    def window_action(self, name: str):
        """A slot forwarding to a MainWindow action, resolved when invoked.

        Connecting straight to ``self.window.foo`` would require the window to
        exist at construction time, which stops a tab from being built (and
        tested) on its own.
        """

        def slot(*_args):
            handler = getattr(self.window, name, None)
            if handler is not None:
                handler()

        return slot

    def _choose_file(self, title: str, file_filter: str, start_dir: str = "") -> str:
        path, _ = QFileDialog.getOpenFileName(self, title, start_dir, file_filter)
        return path

    def _choose_dir(self, title: str, start_dir: str = "") -> str:
        return QFileDialog.getExistingDirectory(self, title, start_dir)


def scrollable(widget: QWidget) -> QScrollArea:
    """Wrap ``widget`` so a field-dense tab stays usable on a short screen."""
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(widget)
    return area


def vbox(parent: QWidget) -> QVBoxLayout:
    layout = QVBoxLayout(parent)
    return layout
