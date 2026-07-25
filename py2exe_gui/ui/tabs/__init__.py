"""Tab widgets. Each owns its own controls and the handlers that belong to it."""

from py2exe_gui.ui.tabs.about_tab import AboutTab
from py2exe_gui.ui.tabs.advanced_tab import AdvancedTab
from py2exe_gui.ui.tabs.base import BaseTab, browse_button, scrollable
from py2exe_gui.ui.tabs.deploy_tab import DeployTab
from py2exe_gui.ui.tabs.history_tab import HistoryTab
from py2exe_gui.ui.tabs.installer_tab import InstallerTab
from py2exe_gui.ui.tabs.main_tab import MainTab
from py2exe_gui.ui.tabs.templates_tab import TemplatesTab
from py2exe_gui.ui.tabs.version_info_tab import VersionInfoTab

__all__ = [
    "AboutTab",
    "AdvancedTab",
    "BaseTab",
    "DeployTab",
    "HistoryTab",
    "InstallerTab",
    "MainTab",
    "TemplatesTab",
    "VersionInfoTab",
    "browse_button",
    "scrollable",
]
