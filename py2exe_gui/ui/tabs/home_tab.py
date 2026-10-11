"""Home: the projects workspace (2.0 milestone 6).

One card per recent ``p2e.toml`` with what ``core.workspace`` gathered: name
and version, the last build, a size sparkline over the successful builds, and
the last release. The tab only draws; the summaries come from the core, and
*open*, *build* and *release* are the window's existing actions, so a build
started here is the same build as the Convert button's.
"""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from py2exe_gui.core.size_analyzer import format_size
from py2exe_gui.core.workspace import (
    STATUS_MISSING,
    ProjectSummary,
    short_time,
    sparkline_points,
)
from py2exe_gui.strings import S
from py2exe_gui.texts import is_rtl
from py2exe_gui.ui.tabs.base import BaseTab, scrollable
from py2exe_gui.ui.tabs.size_tab import ltr, size_text

#: Theme tokens the sparkline paints with, when the window gives none.
DEFAULT_COLORS = {"accent": "#89b4fa", "muted": "#a6adc8", "success": "#a6e3a1"}
SPARKLINE_SIZE = (160, 40)


def _rlm(text: str) -> str:
    """Pin a line that starts with a symbol ("✅", "📏") to right-to-left.

    Qt 5 takes a paragraph's direction from its first strong character and
    ignores isolates, so "✅ آخر بناء … 7.3 MB" would otherwise be laid out
    as a left-to-right paragraph with the Arabic reading backwards.
    """
    return "‏" + text if is_rtl() else text


def _label(text: str, object_name: str = "", wrap: bool = True) -> QLabel:
    label = QLabel(_rlm(text))
    if object_name:
        label.setObjectName(object_name)
    label.setWordWrap(wrap)
    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return label


class SizeSparkline(QWidget):
    """The output size of each successful build, oldest to newest, as a line.

    Time runs in the reading direction (``core.workspace.sparkline_points``
    mirrors it under a right-to-left layout), the newest build is marked with
    a dot, and the sizes are also in the tooltip and the accessible name, so
    the picture never says something the text does not.
    """

    def __init__(self, sizes, colors=None, parent=None):
        super().__init__(parent)
        self.sizes = [int(s) for s in sizes]
        self.colors = dict(DEFAULT_COLORS, **(colors or {}))
        self.setFixedSize(*SPARKLINE_SIZE)
        text = S.HOME_SPARKLINE_NAME_FMT.format(
            sizes=ltr(" → ".join(format_size(s) for s in self.sizes)) or "—")
        self.setToolTip(text)
        self.setAccessibleName(text)

    def points(self):
        rtl = self.layoutDirection() == Qt.RightToLeft
        return sparkline_points(self.sizes, self.width(), self.height(), rtl=rtl, padding=5)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width, height = self.width(), self.height()
        base = QPen(QColor(self.colors["muted"]))
        base.setWidthF(1.0)
        base.setStyle(Qt.DotLine)
        painter.setPen(base)
        painter.drawLine(5, height - 5, width - 5, height - 5)
        points = self.points()
        if not points:
            painter.end()
            return
        line = QPen(QColor(self.colors["accent"]))
        line.setWidthF(2.0)
        line.setCapStyle(Qt.RoundCap)
        line.setJoinStyle(Qt.RoundJoin)
        painter.setPen(line)
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            painter.drawLine(int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2)))
        newest_x, newest_y = points[-1]
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(self.colors["success"]))
        painter.drawEllipse(int(round(newest_x)) - 3, int(round(newest_y)) - 3, 7, 7)
        painter.end()


class ProjectCard(QFrame):
    """One recent project. ``tab`` forwards the buttons to the window."""

    def __init__(self, summary: ProjectSummary, tab, current: bool = False, colors=None,
                 parent=None):
        super().__init__(parent)
        self.summary = summary
        self.path = summary.path
        self.setObjectName("projectCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setAccessibleName(summary.display_name())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        head = QHBoxLayout()
        self.name_label = _label(summary.display_name(), "projectName", wrap=False)
        head.addWidget(self.name_label)
        if summary.ok:
            version = (S.HOME_VERSION_FMT.format(version=ltr(summary.version))
                       if summary.version else S.HOME_NO_VERSION)
            self.version_label = _label(version, "aboutMuted", wrap=False)
            head.addWidget(self.version_label)
        if current:
            self.current_label = _label(S.HOME_CURRENT_PROJECT, "projectCurrent", wrap=False)
            head.addWidget(self.current_label)
        head.addStretch(1)
        layout.addLayout(head)

        self.path_label = _label(ltr(summary.path), "aboutMuted")
        layout.addWidget(self.path_label)

        if summary.ok:
            self._build_details(layout, colors)
        else:
            self._build_problem(layout)

        buttons = QHBoxLayout()
        self.open_btn = self._button(S.BTN_HOME_OPEN, "open_project_path", tab, buttons)
        self.build_btn = self._button(S.BTN_HOME_BUILD, "build_project", tab, buttons,
                                      "successBtn")
        self.release_btn = self._button(S.BTN_HOME_RELEASE, "release_project", tab, buttons)
        buttons.addStretch(1)
        self.forget_btn = self._button(S.BTN_HOME_FORGET, "forget_project", tab, buttons,
                                       "dangerBtn")
        for button in (self.open_btn, self.build_btn, self.release_btn):
            # A file that is gone or refused has nothing to open or build:
            # the buttons go, not just grey out, and only "remove" stays.
            button.setEnabled(summary.ok)
            button.setVisible(summary.ok)
        layout.addLayout(buttons)

    def _button(self, text, action, tab, row, object_name="") -> QPushButton:
        button = QPushButton(text)
        if object_name:
            button.setObjectName(object_name)
        button.setAccessibleName(f"{text} — {self.summary.display_name()}")
        button.clicked.connect(lambda _checked=False: tab.act(action, self.path))
        row.addWidget(button)
        return button

    def _build_details(self, layout, colors):
        summary = self.summary
        meta = []
        if summary.engine and summary.engine != "pyinstaller":
            meta.append(S.HOME_ENGINE_FMT.format(engine=ltr(summary.engine)))
        if summary.repository:
            meta.append(S.HOME_REPOSITORY_FMT.format(repository=ltr(summary.repository)))
        if meta:
            layout.addWidget(_label(" · ".join(meta), "aboutMuted"))
        if summary.warnings:
            layout.addWidget(_label(S.HOME_WARNINGS_FMT.format(count=len(summary.warnings)),
                                    "aboutMuted"))

        record = summary.last_build
        if record is None:
            build_text = S.HOME_NO_BUILDS
        elif record.success:
            build_text = S.HOME_LAST_BUILD_OK_FMT.format(
                time=ltr(short_time(record.timestamp)), size=size_text(record.size_bytes))
        else:
            build_text = S.HOME_LAST_BUILD_FAILED_FMT.format(
                time=ltr(short_time(record.timestamp)))
        if record is not None and summary.builds > 1:
            build_text += " · " + S.HOME_BUILDS_COUNT_FMT.format(count=ltr(str(summary.builds)))
        self.build_label = _label(build_text)
        layout.addWidget(self.build_label)

        size_row = QHBoxLayout()
        self.sparkline = SizeSparkline(summary.sizes, colors)
        size_row.addWidget(self.sparkline)
        self.size_label = _label(self._size_text())
        size_row.addWidget(self.size_label, 1)
        layout.addLayout(size_row)

        release = summary.last_release
        if release is None:
            release_text = S.HOME_NO_RELEASE
        else:
            release_text = S.HOME_LAST_RELEASE_FMT.format(
                version=ltr(release.version), time=ltr(short_time(release.timestamp)),
                files=ltr(str(release.files)), path=ltr(release.path))
            if not release.checksums:
                release_text += " · " + S.HOME_RELEASE_NO_CHECKSUMS
        self.release_label = _label(release_text)
        layout.addWidget(self.release_label)

    def _size_text(self) -> str:
        sizes = self.summary.sizes
        if not sizes:
            return S.HOME_SIZE_NONE
        if len(sizes) == 1:
            return S.HOME_SIZE_SINGLE_FMT.format(size=size_text(sizes[0]))
        delta = self.summary.size_delta() or 0
        if delta > 0:
            delta_text = S.HOME_DELTA_UP_FMT.format(size=format_size(delta))
        elif delta < 0:
            delta_text = S.HOME_DELTA_DOWN_FMT.format(size=format_size(-delta))
        else:
            delta_text = S.HOME_DELTA_SAME
        return S.HOME_SIZE_TREND_FMT.format(
            count=ltr(str(len(sizes))), first=size_text(sizes[0]), last=size_text(sizes[-1]),
            delta=ltr(delta_text) if delta else delta_text)

    def _build_problem(self, layout):
        from py2exe_gui.core.project_file import ProjectFileError
        from py2exe_gui.texts import project_error_text

        summary = self.summary
        if summary.status == STATUS_MISSING:
            text = S.HOME_MISSING
        else:
            error = ProjectFileError(summary.error_code or "generic", summary.error_detail)
            text = S.HOME_UNREADABLE_FMT.format(error=project_error_text(error))
        self.problem_label = _label(text, "warningNotice")
        layout.addWidget(self.problem_label)


class HomeTab(BaseTab):
    """The list of recent projects, one card each."""

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 14, 6, 6)
        layout.setSpacing(12)
        outer.addWidget(scrollable(content))

        layout.addWidget(_label(S.HOME_HINT, "aboutMuted"))

        toolbar = QHBoxLayout()
        self.open_other_btn = QPushButton(S.BTN_HOME_OPEN_OTHER)
        self.open_other_btn.setAccessibleName(S.BTN_HOME_OPEN_OTHER)
        self.open_other_btn.clicked.connect(self.window_action("open_project_dialog"))
        toolbar.addWidget(self.open_other_btn)
        self.refresh_btn = QPushButton(S.BTN_HOME_REFRESH)
        self.refresh_btn.setAccessibleName(S.BTN_HOME_REFRESH)
        self.refresh_btn.clicked.connect(self.window_action("refresh_home"))
        toolbar.addWidget(self.refresh_btn)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self.empty_label = _label(S.HOME_EMPTY, "aboutMuted")
        layout.addWidget(self.empty_label)

        self.cards_box = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_box)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)
        layout.addWidget(self.cards_box)
        layout.addStretch(1)
        self.cards = []

    def show_projects(self, summaries, current_path: str = "", colors=None):
        """Replace the cards with one per summary (most recent first)."""
        for card in self.cards:
            self.cards_layout.removeWidget(card)
            card.setParent(None)
            card.deleteLater()
        self.cards = []
        for summary in summaries:
            current = bool(current_path) and _same(summary.path, current_path)
            card = ProjectCard(summary, self, current=current, colors=colors)
            self.cards_layout.addWidget(card)
            self.cards.append(card)
        self.empty_label.setVisible(not self.cards)

    def card_for(self, path: str):
        for card in self.cards:
            if _same(card.path, path):
                return card
        return None

    def act(self, action: str, path: str):
        """Forward a card's button to the window's action of that name."""
        handler = getattr(self.window, action, None)
        if handler is not None:
            handler(path)

    # Summaries are plain data: nothing to read into or apply from a project.
    def read_project(self, project):  # pragma: no cover - not a project tab
        return project

    def apply_project(self, project, sections=()):  # pragma: no cover
        return None


def _same(a: str, b: str) -> bool:
    return os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(b))


__all__ = ["HomeTab", "ProjectCard", "SizeSparkline"]
