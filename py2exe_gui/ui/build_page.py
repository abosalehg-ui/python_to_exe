"""The Build page: the main form, then the less common options folded away.

"Advanced settings", "Version info" and "Deploy" were three more tabs that
together form one thing: the options of a build, at three depths of detail.
They are now sections under the main form, closed by default, each with a
one-line summary of what it holds so a closed section is not a mystery. The
tab widgets themselves are unchanged and keep their names on the window
(``advanced_tab``, ``version_info_tab``, ``deploy_tab``), so every reader and
writer of the project model, and every test, finds them where it did.
"""

from py2exe_gui.qt import QWidget
from py2exe_gui.ui.tabs.base import scrolled_layout
from py2exe_gui.ui.widgets.collapsible import CollapsibleSection


class BuildPage(QWidget):
    """``main_tab`` followed by one ``CollapsibleSection`` per extra tab.

    ``sections`` is a list of ``(key, title, widget, summary)`` where
    ``summary`` is a callable returning the one-line subtitle (or ``None``).
    """

    def __init__(self, main_tab: QWidget, sections, expanded: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("buildPage")
        self.main_tab = main_tab
        self.sections = {}
        self._summaries = {}
        layout = scrolled_layout(self)
        layout.setSpacing(10)
        layout.addWidget(main_tab)
        for key, title, widget, summary in sections:
            section = CollapsibleSection(title, widget, expanded=expanded)
            self.sections[key] = section
            self._summaries[key] = summary
            layout.addWidget(section)
        layout.addStretch(1)
        self.refresh_summaries()

    # ── Sections ───────────────────────────────────────────────────────────

    def expand(self, key: str, expanded: bool = True):
        section = self.sections.get(key)
        if section is not None:
            section.set_expanded(expanded)

    def set_all_expanded(self, expanded: bool):
        for section in self.sections.values():
            section.set_expanded(expanded)

    def any_expanded(self) -> bool:
        return any(s.is_expanded() for s in self.sections.values())

    def expanded_keys(self):
        return [key for key, s in self.sections.items() if s.is_expanded()]

    def set_expanded_keys(self, keys):
        keys = set(keys or ())
        for key, section in self.sections.items():
            section.set_expanded(key in keys)

    def section_for(self, widget: QWidget):
        for key, section in self.sections.items():
            if section.content is widget:
                return key
        return None

    def reveal(self, widget: QWidget):
        """Open the section holding ``widget`` (navigation lands here)."""
        key = self.section_for(widget)
        if key is not None:
            self.expand(key, True)

    def refresh_summaries(self):
        """Recompute every section's subtitle from the tabs' current state."""
        for key, section in self.sections.items():
            summary = self._summaries.get(key)
            if summary is None:
                continue
            try:
                section.set_subtitle(summary() or "")
            except Exception:  # a summary must never break the page
                section.set_subtitle("")
