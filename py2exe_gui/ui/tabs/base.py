"""Shared plumbing for the tab widgets.

`main_window.py` used to build all eight tabs inline and own every widget,
which is how it reached 1,900 lines. Each tab is now a self-contained widget
that owns its own controls and the browse handlers that belong to it; the
window keeps orchestration (threads, the build pipeline, shortcuts).
"""

from py2exe_gui import icons
from py2exe_gui.bidi import bidi, rlm
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
    QSize,
    Qt,
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


ICON_BUTTON_SIZE = 32
ICON_SIZE = 18


def icon_button(icon_name: str, label: str, handler, size: int = ICON_BUTTON_SIZE) -> QPushButton:
    """A square button that shows an icon and *says* ``label``.

    The icon is drawn in the default colour here and recoloured by the window
    for the active theme (``MainWindow._apply_icons`` reads ``iconName``).
    The tooltip and the accessible name are not optional: an icon alone is
    indistinguishable to assistive technology and to anyone new to the app.
    """
    button = QPushButton()
    button.setObjectName("iconBtn")
    button.setProperty("iconName", icon_name)
    button.setFixedSize(size, size)
    button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
    button.setIcon(icons.icon(icon_name))
    button.setToolTip(label)
    button.setAccessibleName(label)
    button.setAccessibleDescription(label)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.clicked.connect(handler)
    return button


def browse_button(label: str, handler, folder: bool = False) -> QPushButton:
    """The "choose a file/folder" button next to a path field."""
    return icon_button("browse_folder" if folder else "browse_file", label, handler)


def em_width(widget: QWidget, ems: int) -> int:
    """``ems`` times the width of "M" in ``widget``'s font, in pixels.

    For widths that used to be fixed pixel counts: a 180px bar is a third of
    the action bar at 9pt and a sliver at 18pt after Ctrl+=.
    """
    return widget.fontMetrics().horizontalAdvance("M") * ems


def labelled(label_text: str, widget: QWidget) -> QLabel:
    """The label of a form field, wired to the field it names.

    ``setBuddy`` gives the label's mnemonic focus to the field and lets a
    screen reader read the label as the field's name; ``setAccessibleName``
    covers the readers that do not follow buddies. A field without either is
    announced as "edit text", which says nothing about what to type.
    """
    label = QLabel(label_text)
    label.setBuddy(widget)
    if not widget.accessibleName():
        widget.setAccessibleName(label_text.replace("&", ""))
    return label


def muted_label(text: str = "") -> QLabel:
    """A wrapped, muted explanation (``aboutMuted``), bidi-fixed for RTL."""
    label = QLabel(bidi(text))
    label.setObjectName("aboutMuted")
    label.setWordWrap(True)
    return label


def text_label(text: str, object_name: str = "", wrap: bool = True) -> QLabel:
    """A selectable label whose direction follows the UI even when the text
    starts with a symbol or a number (see :func:`py2exe_gui.bidi.rlm`)."""
    label = QLabel(rlm(text))
    if object_name:
        label.setObjectName(object_name)
    label.setWordWrap(wrap)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


class BaseTab(QWidget):
    """Base class for every tab.

    Subclasses implement ``_build()`` and populate ``self`` with their
    widgets. ``window`` is the owning MainWindow, used for logging and for
    the few actions that span tabs.
    """

    def __init__(self, window=None, parent=None, embedded=False):
        super().__init__(parent)
        self.window = window
        # An embedded tab is one section of a larger scrolling page (the Build
        # page): it must not bring a scroll area of its own, or the page would
        # scroll inside a page.
        self.embedded = bool(embedded)
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


def scrolled_layout(tab: QWidget, spacing: int = -1) -> QVBoxLayout:
    """The layout a tab adds its groups to, inside a scroll area.

    Every tab goes through here. Eight of fifteen tabs used to lay their
    groups straight onto the widget, and when the window was shorter than
    their content (the default 1080x800 window, any 1366x768 laptop) Qt
    squeezed the fields to a couple of pixels instead of scrolling.
    ``spacing`` (pixels between groups) is left to the style when negative.
    """
    if getattr(tab, "embedded", False):
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        if spacing >= 0:
            layout.setSpacing(spacing)
        return layout
    outer = QVBoxLayout(tab)
    outer.setContentsMargins(0, 0, 0, 0)
    content = QWidget()
    layout = QVBoxLayout(content)
    # Room above the first group box: its title sits in the margin and
    # would be clipped by the top edge of the scroll area.
    layout.setContentsMargins(6, 14, 6, 6)
    if spacing >= 0:
        layout.setSpacing(spacing)
    outer.addWidget(scrollable(content))
    return layout
