"""Domain controllers mixed into MainWindow, one module per area."""

from py2exe_gui.ui.controllers.build import BuildController
from py2exe_gui.ui.controllers.doctor import DoctorController
from py2exe_gui.ui.controllers.environment import EnvironmentController
from py2exe_gui.ui.controllers.keys import KeysController
from py2exe_gui.ui.controllers.project import ProjectController
from py2exe_gui.ui.controllers.release import ReleaseController

__all__ = ["BuildController", "EnvironmentController", "ReleaseController", "KeysController", "ProjectController", "DoctorController"]
