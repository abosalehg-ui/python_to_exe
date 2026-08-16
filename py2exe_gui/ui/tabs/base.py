"""Shared plumbing for the tab widgets.

`main_window.py` used to build all eight tabs inline and own every widget,
which is how it reached 1,900 lines. Each tab is now a self-contained widget
that owns its own controls and the browse handlers that belong to it; the
window keeps orchestration (threads, the build pipeline, shortcuts).
"""

from PyQt5.QtWidgets import (
    QFileDialog,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from py2exe_gui.core.platform_support import platform_label, unsupported_features
from py2exe_gui.strings import S

# Feature key → the locale attribute naming it. Kept beside the banner helper
# because that is the only place the mapping is needed.
_FEATURE_LABELS = {
    "code_signing": "FEATURE_CODE_SIGNING",
    "manifest": "FEATURE_MANIFEST",
    "version_info": "FEATURE_VERSION_INFO",
    "installer": "FEATURE_INSTALLER",
}


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


def platform_notice(*features, platform=None):
    """A banner naming the given features when they do nothing on this OS.

    Returns None on Windows (or when every listed feature works here), so the
    caller can simply skip adding it. The tabs stay visible either way — the
    build itself is cross-platform, and hiding the controls would only make
    the eventual "signtool not found" harder to understand.
    """
    unsupported = set(unsupported_features(platform))
    affected = [f for f in features if f in unsupported]
    if not affected:
        return None

    names = S.LIST_SEPARATOR.join(getattr(S, _FEATURE_LABELS[f]) for f in affected)
    label = QLabel(
        S.PLATFORM_WINDOWS_ONLY_FMT.format(
            platform=platform_label(platform), features=names
        )
    )
    label.setObjectName("warningNotice")
    label.setWordWrap(True)
    label.setAccessibleName(label.text())
    return label


def scrollable(widget: QWidget) -> QScrollArea:
    """Wrap ``widget`` so a field-dense tab stays usable on a short screen."""
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(widget)
    return area


def vbox(parent: QWidget) -> QVBoxLayout:
    layout = QVBoxLayout(parent)
    return layout
