"""The Qt binding, chosen once for the whole application.

Everything outside ``py2exe_gui/core/`` imports Qt from here and nowhere
else::

    from py2exe_gui.qt import QApplication, Qt, Signal

PySide6 is preferred; PyQt5 is the fallback. The choice happens the first
time this module is imported, in this order:

1. ``QT_API`` in the environment (``pyside6`` or ``pyqt5``, the de-facto
   variable that qtpy and matplotlib also honour) forces a binding;
2. a binding that is already imported into the process wins, so two bindings
   are never loaded side by side;
3. PySide6, then PyQt5.

The two bindings differ in a few names, and this module hides them:

- ``pyqtSignal``/``pyqtSlot``/``pyqtProperty`` are exported as ``Signal``,
  ``Slot`` and ``Property`` (PySide6's names);
- ``QAction`` and ``QShortcut`` live in ``QtGui`` in Qt 6 and in
  ``QtWidgets`` in Qt 5, and are exported from here either way;
- any other Qt class is looked up in ``QtWidgets``, ``QtGui`` and ``QtCore``
  in that order (PEP 562 module ``__getattr__``), so
  ``from py2exe_gui.qt import QFileDialog`` works without a per-class table.

Conventions the rest of the code follows so that both bindings behave the
same: fully scoped enums (``Qt.AlignmentFlag.AlignLeft``, never
``Qt.AlignLeft``), ``exec()`` rather than the Qt 5-only ``exec_()``, and
``QFont.setBold`` rather than passing a weight to the ``QFont`` constructor.

``py2exe_gui/core/`` and the command line never import this module: the
import of a binding is a hard failure here, by design, and the core CI job
runs with neither binding installed.
"""

import importlib
import os
import sys
from typing import List, Optional, Tuple

#: The bindings this module knows, in order of preference.
SUPPORTED = ("PySide6", "PyQt5")
#: Environment variable that forces one binding (``pyside6`` or ``pyqt5``).
API_VARIABLE = "QT_API"

_CANONICAL = {name.lower(): name for name in SUPPORTED}


def binding_order(env: Optional[dict] = None, loaded: Optional[dict] = None) -> List[str]:
    """The bindings to try, most preferred first (see the module docstring).

    Pure, so the tests can check the policy without importing Qt: ``env``
    defaults to ``os.environ`` and ``loaded`` to ``sys.modules``.
    """
    env = os.environ if env is None else env
    loaded = sys.modules if loaded is None else loaded
    forced = _CANONICAL.get(env.get(API_VARIABLE, "").strip().lower())
    if forced:
        return [forced]
    already = [name for name in SUPPORTED if loaded.get(name) is not None]
    return already + [name for name in SUPPORTED if name not in already]


def _import_binding(order: List[str]) -> Tuple[str, object, object, object]:
    errors = []
    for name in order:
        try:
            core = importlib.import_module(name + ".QtCore")
            gui = importlib.import_module(name + ".QtGui")
            widgets = importlib.import_module(name + ".QtWidgets")
        except ImportError as e:  # also ModuleNotFoundError, also a blocked module
            errors.append(f"{name}: {e}")
            continue
        return name, core, gui, widgets
    detail = "; ".join(errors) or "no binding tried"
    raise ModuleNotFoundError(
        "No Qt binding is installed (tried " + ", ".join(order) + "). "
        "Install PySide6 (recommended) or PyQt5. " + detail,
        name=order[0] if order else "PySide6",
    )


API, QtCore, QtGui, QtWidgets = _import_binding(binding_order())

if API == "PySide6":
    import PySide6 as _binding_module

    Signal = QtCore.Signal
    Slot = QtCore.Slot
    Property = QtCore.Property
    API_VERSION = _binding_module.__version__
    QT_VERSION = QtCore.qVersion()
    QAction = QtGui.QAction
    QShortcut = QtGui.QShortcut
else:
    Signal = QtCore.pyqtSignal
    Slot = QtCore.pyqtSlot
    Property = QtCore.pyqtProperty
    API_VERSION = QtCore.PYQT_VERSION_STR
    QT_VERSION = QtCore.QT_VERSION_STR
    QAction = QtWidgets.QAction
    QShortcut = QtWidgets.QShortcut

#: Major version of the Qt library underneath (5 or 6).
QT_MAJOR = int(QT_VERSION.split(".")[0])
IS_QT6 = QT_MAJOR >= 6

Qt = QtCore.Qt

_MODULES = (QtWidgets, QtGui, QtCore)


def __getattr__(name: str):
    """Resolve any Qt class from the three modules the application uses.

    ``QtSvg`` (the icon renderer, 2.1) is looked up last and imported on
    first use: it is a separate module in both bindings, and a binding
    installed without it must still open the window (icons fall back to
    the image plugin, then to no icon).
    """
    if name.startswith("_"):
        raise AttributeError(name)
    for module in _MODULES:
        value = getattr(module, name, None)
        if value is not None:
            return value
    if name.startswith("QSvg"):
        try:
            svg = importlib.import_module(API + ".QtSvg")
        except ImportError as e:
            raise AttributeError(f"{API}.QtSvg is not installed: {e}") from e
        value = getattr(svg, name, None)
        if value is not None:
            return value
    raise AttributeError(f"module 'py2exe_gui.qt' ({API}) has no attribute {name!r}")


def describe() -> str:
    """``"PySide6 6.7.2 (Qt 6.7.2)"``: for the About tab and the reports."""
    return f"{API} {API_VERSION} (Qt {QT_VERSION})"


def configure_high_dpi() -> None:
    """Make the window scale with the display, on every Qt version.

    Must run before the ``QApplication`` exists. Qt 6 scales by default and
    the Qt 5 attributes are deprecated there (and warn), so they are set on
    Qt 5 only. The rounding policy is set on both so that a 150 % display
    scales 1.5x rather than rounding to 2x; Qt 5.14+ and Qt 6 both have it.
    """
    app = QtWidgets.QApplication
    if not IS_QT6:
        attribute = Qt.ApplicationAttribute
        for name in ("AA_EnableHighDpiScaling", "AA_UseHighDpiPixmaps"):
            if hasattr(attribute, name):
                app.setAttribute(getattr(attribute, name), True)
    policy = getattr(Qt, "HighDpiScaleFactorRoundingPolicy", None)
    if policy is not None and hasattr(app, "setHighDpiScaleFactorRoundingPolicy"):
        app.setHighDpiScaleFactorRoundingPolicy(policy.PassThrough)


def font_families(locale: str = "ar") -> tuple:
    """Families tried in order for the application font.

    One source: ``styles.UI_FONT_STACKS``, the same table the stylesheet
    renders, so the QFont the widgets inherit and the CSS never disagree.
    "Segoe UI" is the Windows system font and covers Arabic; the others are
    the usual Linux and macOS fonts with Arabic glyphs, so the UI never falls
    back to boxes. Qt's own fontconfig fallback still applies for anything
    missing from them all. Imported lazily: ``styles`` has no Qt, but keeping
    this module free of application imports at load time is worth it.
    """
    from py2exe_gui.styles import font_stack

    return tuple(font_stack(locale))


#: The Arabic-first stack, kept as a constant for callers that only need a name.
FONT_FAMILIES = font_families("ar")


def application_font(point_size: int = 10, locale: str = "ar"):
    """The default UI font, with Arabic-capable fallbacks (Qt 5.13+ and Qt 6)."""
    families = font_families(locale)
    font = QtGui.QFont(families[0], point_size)
    if hasattr(font, "setFamilies"):
        font.setFamilies(list(families))
    return font


__all__ = [
    "API",
    "API_VERSION",
    "API_VARIABLE",
    "FONT_FAMILIES",
    "IS_QT6",
    "Property",
    "QAction",
    "QShortcut",
    "QT_MAJOR",
    "QT_VERSION",
    "Qt",
    "QtCore",
    "QtGui",
    "QtWidgets",
    "SUPPORTED",
    "Signal",
    "Slot",
    "application_font",
    "binding_order",
    "font_families",
    "configure_high_dpi",
    "describe",
]
