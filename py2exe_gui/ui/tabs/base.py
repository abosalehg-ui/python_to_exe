"""Shared plumbing for the tab widgets.

`main_window.py` used to build all eight tabs inline and own every widget,
which is how it reached 1,900 lines. Each tab is now a self-contained widget
that owns its own controls and the browse handlers that belong to it; the
window keeps orchestration (threads, the build pipeline, shortcuts).
"""

from py2exe_gui.core.platform_support import (
    LINUX,
    MACOS,
    WINDOWS,
    platform_label,
    required_platform,
    unsupported_features,
)
from py2exe_gui.qt import (
    QFileDialog,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from py2exe_gui.strings import S

# Feature key → the locale attribute naming it. Kept beside the banner helper
# because that is the only place the mapping is needed.
_FEATURE_LABELS = {
    "code_signing": "FEATURE_CODE_SIGNING",
    "manifest": "FEATURE_MANIFEST",
    "version_info": "FEATURE_VERSION_INFO",
    "installer": "FEATURE_INSTALLER",
    "appimage": "FEATURE_APPIMAGE",
    "deb": "FEATURE_DEB",
    "dmg": "FEATURE_DMG",
}
# The host a feature needs → the banner text naming it.
_NOTICE_FORMATS = {
    WINDOWS: "PLATFORM_WINDOWS_ONLY_FMT",
    LINUX: "PLATFORM_LINUX_ONLY_FMT",
    MACOS: "PLATFORM_MACOS_ONLY_FMT",
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

    # One paragraph per host the features need (Windows, Linux, macOS).
    paragraphs = []
    for host, attr in _NOTICE_FORMATS.items():
        here = [f for f in affected if required_platform(f) == host]
        if here:
            names = S.LIST_SEPARATOR.join(getattr(S, _FEATURE_LABELS[f]) for f in here)
            paragraphs.append(getattr(S, attr).format(platform=platform_label(platform),
                                                      features=names))
    label = QLabel("\n".join(paragraphs))
    # A caution, not an error: the feature is skipped here, nothing breaks.
    label.setObjectName("noticeWarning")
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


def scrolled_layout(tab: QWidget) -> QVBoxLayout:
    """The layout a tab adds its groups to, inside a scroll area.

    Every tab goes through here. Eight of fifteen tabs used to lay their
    groups straight onto the widget, and when the window was shorter than
    their content (the default 1080x800 window, any 1366x768 laptop) Qt
    squeezed the fields to a couple of pixels instead of scrolling.
    """
    outer = QVBoxLayout(tab)
    outer.setContentsMargins(0, 0, 0, 0)
    content = QWidget()
    layout = QVBoxLayout(content)
    # Room above the first group box: its title sits in the margin and
    # would be clipped by the top edge of the scroll area.
    layout.setContentsMargins(6, 14, 6, 6)
    outer.addWidget(scrollable(content))
    return layout
