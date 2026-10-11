"""Side navigation: six sections instead of fifteen tabs in one row.

The tab bar needed 1661px for the Arabic titles (1794px in English) in a
window that offers about 1040px, so six tabs hid behind scroll arrows and the
order followed the history of the project rather than the work. A list down
the side always fits, groups the pages by what the person is doing (build,
check, distribute…), and reads top to bottom in the order the work happens.

``SectionView`` also speaks the small subset of the ``QTabWidget`` API the
window and its tests already used (``count``, ``widget``, ``tabText``,
``indexOf``, ``currentWidget``, ``setCurrentWidget``), so ``window.tabs``
kept its name and nothing that navigates by page had to change. A "leaf" is
one of the former tabs; a section shows one leaf, a row of sub-tabs, or a
composed page (the Build page) that embeds several leaves.
"""

from py2exe_gui.qt import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QSize,
    QSizePolicy,
    QStackedWidget,
    Qt,
    QTabWidget,
    QWidget,
    Signal,
)

NAV_WIDTH = 200
NAV_COLLAPSED_WIDTH = 56
NAV_ROW_HEIGHT = 40
NAV_ICON_SIZE = 20


class SectionNav(QListWidget):
    """The list of sections down the side of the window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sideNav")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setIconSize(QSize(NAV_ICON_SIZE, NAV_ICON_SIZE))
        self.setSpacing(2)
        self.setUniformItemSizes(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setFixedWidth(NAV_WIDTH)
        self._titles = []
        self._collapsed = False

    def add_section(self, title: str, icon=None):
        item = QListWidgetItem(title)
        if icon is not None:
            item.setIcon(icon)
        item.setSizeHint(QSize(0, NAV_ROW_HEIGHT))
        item.setToolTip(title)
        self.addItem(item)
        self._titles.append(title)

    def set_collapsed(self, collapsed: bool):
        """Icons only (the titles stay as tooltips) or icons with titles."""
        self._collapsed = bool(collapsed)
        for row, title in enumerate(self._titles):
            self.item(row).setText("" if self._collapsed else title)
        self.setFixedWidth(NAV_COLLAPSED_WIDTH if self._collapsed else NAV_WIDTH)

    def is_collapsed(self) -> bool:
        return self._collapsed


class _Leaf:
    __slots__ = ("widget", "title", "section", "reveal")

    def __init__(self, widget, title, section, reveal=None):
        self.widget = widget
        self.title = title
        self.section = section
        self.reveal = reveal


class SectionView(QWidget):
    """``nav`` beside ``stack``; one stacked page per section."""

    #: Emitted with the leaf index whenever the visible leaf changes.
    currentChanged = Signal(int)
    #: Emitted with the section key whenever the section changes.
    sectionChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.nav = SectionNav()
        self.stack = QStackedWidget()
        self.stack.setObjectName("sectionStack")
        self._sections = []          # keys, in nav order
        self._section_titles = {}
        self._pages = {}             # key -> the widget in the stack
        self._leaves = []            # registration order == former tab order
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.nav)
        layout.addWidget(self.stack, 1)
        self.nav.currentRowChanged.connect(self._on_nav_changed)

    # ── Building ───────────────────────────────────────────────────────────

    def add_section(self, key: str, title: str, icon=None, page=None, tabbed=False):
        """Register a section. ``page`` is a composed widget that embeds its
        leaves; ``tabbed`` makes a row of sub-tabs for the leaves added later;
        otherwise the first leaf added becomes the page."""
        if page is None and tabbed:
            page = QTabWidget()
            page.setObjectName("subTabs")
            page.setDocumentMode(True)
            page.currentChanged.connect(lambda _i: self._emit_current())
        self._sections.append(key)
        self._section_titles[key] = title
        self._pages[key] = page
        if page is not None:
            self.stack.addWidget(page)
        else:
            # Placeholder so stack index == section index; replaced by the leaf.
            self.stack.addWidget(QWidget())
        self.nav.add_section(title, icon)

    def add_page(self, section: str, widget: QWidget, title: str, reveal=None):
        """Register ``widget`` as a leaf of ``section``.

        ``reveal`` is called when the leaf is navigated to inside a composed
        page (to open the section that holds it, say).
        """
        if section not in self._pages:
            raise KeyError(section)
        page = self._pages[section]
        if page is None:
            index = self._sections.index(section)
            placeholder = self.stack.widget(index)
            self.stack.removeWidget(placeholder)
            placeholder.deleteLater()
            self.stack.insertWidget(index, widget)
            self._pages[section] = widget
        elif isinstance(page, QTabWidget) and page.objectName() == "subTabs":
            page.addTab(widget, title)
        self._leaves.append(_Leaf(widget, title, section, reveal))

    def finish(self):
        """Select the first section once everything is registered."""
        if self.nav.count() and self.nav.currentRow() < 0:
            self.nav.setCurrentRow(0)

    # ── Sections ───────────────────────────────────────────────────────────

    def sections(self):
        return list(self._sections)

    def section_title(self, key: str) -> str:
        return self._section_titles.get(key, "")

    def current_section(self) -> str:
        row = self.nav.currentRow()
        return self._sections[row] if 0 <= row < len(self._sections) else ""

    def set_current_section(self, key: str):
        if key in self._sections:
            self.nav.setCurrentRow(self._sections.index(key))

    def section_of(self, widget: QWidget) -> str:
        leaf = self._leaf_for(widget)
        return leaf.section if leaf else ""

    def page_of(self, key: str):
        return self._pages.get(key)

    def set_collapsed(self, collapsed: bool):
        self.nav.set_collapsed(collapsed)

    # ── The QTabWidget-shaped API ──────────────────────────────────────────

    def count(self) -> int:
        return len(self._leaves)

    def widget(self, index: int):
        return self._leaves[index].widget if 0 <= index < len(self._leaves) else None

    def tabText(self, index: int) -> str:
        return self._leaves[index].title if 0 <= index < len(self._leaves) else ""

    def setTabText(self, index: int, title: str):
        if not 0 <= index < len(self._leaves):
            return
        leaf = self._leaves[index]
        leaf.title = title
        page = self._pages.get(leaf.section)
        if isinstance(page, QTabWidget):
            page.setTabText(page.indexOf(leaf.widget), title)

    def indexOf(self, widget: QWidget) -> int:
        for i, leaf in enumerate(self._leaves):
            if leaf.widget is widget:
                return i
        return -1

    def currentWidget(self):
        key = self.current_section()
        if not key:
            return None
        page = self._pages.get(key)
        if isinstance(page, QTabWidget) and page.objectName() == "subTabs":
            return page.currentWidget()
        for leaf in self._leaves:
            if leaf.section == key:
                return leaf.widget
        return page

    def currentIndex(self) -> int:
        return self.indexOf(self.currentWidget())

    def setCurrentWidget(self, widget: QWidget):
        leaf = self._leaf_for(widget)
        if leaf is None:
            return
        self.set_current_section(leaf.section)
        page = self._pages.get(leaf.section)
        if isinstance(page, QTabWidget) and page.objectName() == "subTabs":
            page.setCurrentWidget(widget)
        if leaf.reveal is not None:
            leaf.reveal()

    def setCurrentIndex(self, index: int):
        widget = self.widget(index)
        if widget is not None:
            self.setCurrentWidget(widget)

    def clear(self):
        while self.stack.count():
            page = self.stack.widget(0)
            self.stack.removeWidget(page)
        self.nav.clear()
        self.nav._titles = []
        self._sections = []
        self._section_titles = {}
        self._pages = {}
        self._leaves = []

    # ── Internals ──────────────────────────────────────────────────────────

    def _leaf_for(self, widget):
        for leaf in self._leaves:
            if leaf.widget is widget:
                return leaf
        return None

    def _on_nav_changed(self, row: int):
        if 0 <= row < self.stack.count():
            self.stack.setCurrentIndex(row)
            self.sectionChanged.emit(self._sections[row])
            self._emit_current()

    def _emit_current(self):
        self.currentChanged.emit(self.currentIndex())
