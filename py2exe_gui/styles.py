"""Qt stylesheet definitions (Catppuccin-inspired dark + light themes)."""

# ── Log line colors ────────────────────────────────────────────────────────
# Single source of truth: log_formatter imports these rather than keeping a
# second copy. One palette per theme, because a single palette cannot clear
# WCAG AA (4.5:1) against both a near-black and a white log background.
#
# Measured contrast against the QTextEdit background of each theme:
#   dark  (on #181825): info 8.34  success 11.81  warning 13.81  error 7.58  muted 6.22
#   light (on #ffffff): info 5.19  success  5.08  warning  4.87  error 5.36  muted 6.27
# Keep every value above 4.5 when editing — tests/test_log_formatter.py enforces it.

LOG_BACKGROUND = {"dark": "#181825", "light": "#ffffff"}

LOG_COLORS = {
    "dark": {
        "info": "#89b4fa",
        "success": "#a6e3a1",
        "warning": "#f9e2af",
        "error": "#f38ba8",
        "muted": "#9399b2",
    },
    "light": {
        "info": "#0969da",
        "success": "#1a7f37",
        "warning": "#9a6700",
        "error": "#cf222e",
        "muted": "#5a6169",
    },
}

DEFAULT_LOG_THEME = "dark"

# ── Fonts ──────────────────────────────────────────────────────────────────
# Segoe UI has thin Arabic coverage and falls back mid-run, which makes mixed
# Arabic/Latin lines sit at inconsistent heights. Arabic-first locales lead
# with faces that actually ship Arabic glyphs.
UI_FONT_STACKS = {
    "ar": ("Segoe UI", "Tahoma", "Dubai", "Noto Naskh Arabic", "Arial"),
    "default": ("Segoe UI", "Arial", "Helvetica"),
}


def font_stack(locale: str = "default") -> tuple:
    """Ordered font family preferences for ``locale``."""
    return UI_FONT_STACKS.get(locale, UI_FONT_STACKS["default"])


def font_family_css(locale: str = "default") -> str:
    """The same stack rendered as a CSS ``font-family`` value."""
    return ", ".join(f"'{name}'" for name in font_stack(locale)) + ", sans-serif"


def themed_stylesheet(theme: str, locale: str = "default") -> str:
    """Return a theme stylesheet with the locale-appropriate font stack."""
    sheet = THEMES.get(theme) or THEMES[DEFAULT_LOG_THEME]
    return sheet.replace(
        "font-family: 'Segoe UI', 'Arial', sans-serif;",
        f"font-family: {font_family_css(locale)};",
    )


DARK_THEME = """
QMainWindow {
    background-color: #1e1e2e;
}
QWidget {
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 9pt;
    color: #cdd6f4;
}
QGroupBox {
    font-weight: bold;
    font-size: 10pt;
    border: 2px solid #45475a;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 10px;
    background-color: #313244;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top right;
    padding: 0 10px;
    color: #89b4fa;
}
QPushButton {
    background-color: #89b4fa;
    color: #1e1e2e;
    /* Transparent border keeps geometry stable when :focus adds a visible one. */
    border: 2px solid transparent;
    padding: 5px 12px;
    border-radius: 6px;
    font-weight: bold;
    min-height: 16px;
}
QPushButton:hover {
    background-color: #b4befe;
}
QPushButton:pressed {
    background-color: #74c7ec;
}
/* Keyboard users could not tell which button had focus. */
QPushButton:focus {
    border: 2px solid #f5e0dc;
}
QPushButton:disabled {
    background-color: #45475a;
    color: #6c7086;
}
QPushButton#dangerBtn {
    background-color: #f38ba8;
}
QPushButton#dangerBtn:hover {
    background-color: #eba0ac;
}
QPushButton#successBtn {
    background-color: #a6e3a1;
}
QPushButton#successBtn:hover {
    background-color: #94e2d5;
}
QLineEdit, QComboBox, QSpinBox {
    background-color: #45475a;
    border: 2px solid #585b70;
    border-radius: 6px;
    padding: 8px;
    color: #cdd6f4;
}
QLineEdit:focus, QComboBox:focus {
    border-color: #89b4fa;
}
QTextEdit {
    background-color: #181825;
    border: 2px solid #45475a;
    border-radius: 8px;
    padding: 10px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 8pt;
    color: #a6e3a1;
}
QListWidget {
    background-color: #45475a;
    border: 2px solid #585b70;
    border-radius: 6px;
    padding: 5px;
}
QListWidget::item {
    padding: 5px;
    border-radius: 4px;
}
QListWidget::item:selected {
    background-color: #89b4fa;
    color: #1e1e2e;
}
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid #585b70;
    background-color: #45475a;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}
QProgressBar {
    border: 2px solid #45475a;
    border-radius: 6px;
    text-align: center;
    background-color: #313244;
    color: #cdd6f4;
    font-weight: bold;
}
QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 4px;
}
QTabWidget::pane {
    border: 2px solid #45475a;
    border-radius: 8px;
    background-color: #313244;
}
QTabBar::tab {
    background-color: #45475a;
    padding: 10px 20px;
    margin: 2px;
    border-radius: 6px;
}
QTabBar::tab:selected {
    background-color: #89b4fa;
    color: #1e1e2e;
}
QStatusBar {
    background-color: #181825;
    color: #6c7086;
}
QLabel#titleLabel {
    font-size: 18pt;
    font-weight: bold;
    color: #89b4fa;
}
QLabel#subtitleLabel {
    font-size: 9pt;
    color: #6c7086;
}
/* About tab. Previously these colours were inline in the HTML, so the tab
   stayed dark-themed (and unreadable) after switching to the light theme. */
QLabel#aboutHeading {
    font-size: 16pt;
    font-weight: bold;
    color: #89b4fa;
}
QLabel#aboutSubheading {
    font-size: 11pt;
    font-weight: bold;
    color: #a6e3a1;
}
QLabel#aboutBody {
    font-size: 10pt;
    color: #cdd6f4;
}
QLabel#aboutMuted {
    font-size: 9pt;
    color: #9399b2;
}
QFrame#aboutSeparator {
    background-color: #45475a;
    max-height: 1px;
    border: none;
}
"""


LIGHT_THEME = """
QMainWindow {
    background-color: #eff1f5;
}
QWidget {
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 9pt;
    color: #4c4f69;
}
QGroupBox {
    font-weight: bold;
    font-size: 10pt;
    border: 2px solid #ccd0da;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 10px;
    background-color: #e6e9ef;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top right;
    padding: 0 10px;
    color: #1e66f5;
}
QPushButton {
    background-color: #1e66f5;
    color: #eff1f5;
    border: 2px solid transparent;
    padding: 5px 12px;
    border-radius: 6px;
    font-weight: bold;
    min-height: 16px;
}
QPushButton:hover {
    background-color: #7287fd;
}
QPushButton:pressed {
    background-color: #04a5e5;
}
QPushButton:focus {
    border: 2px solid #11111b;
}
QPushButton:disabled {
    background-color: #ccd0da;
    color: #9ca0b0;
}
QPushButton#dangerBtn {
    background-color: #d20f39;
}
QPushButton#dangerBtn:hover {
    background-color: #e64553;
}
QPushButton#successBtn {
    background-color: #40a02b;
}
QPushButton#successBtn:hover {
    background-color: #179299;
    color: #eff1f5;
}
QLineEdit, QComboBox, QSpinBox {
    background-color: #eff1f5;
    border: 2px solid #ccd0da;
    border-radius: 6px;
    padding: 8px;
    color: #4c4f69;
}
QLineEdit:focus, QComboBox:focus {
    border-color: #1e66f5;
}
QTextEdit {
    background-color: #ffffff;
    border: 2px solid #ccd0da;
    border-radius: 8px;
    padding: 10px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 8pt;
    color: #4c4f69;
}
QListWidget {
    background-color: #eff1f5;
    border: 2px solid #ccd0da;
    border-radius: 6px;
    padding: 5px;
}
QListWidget::item {
    padding: 5px;
    border-radius: 4px;
}
QListWidget::item:selected {
    background-color: #1e66f5;
    color: #eff1f5;
}
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid #ccd0da;
    background-color: #eff1f5;
}
QCheckBox::indicator:checked {
    background-color: #1e66f5;
    border-color: #1e66f5;
}
QProgressBar {
    border: 2px solid #ccd0da;
    border-radius: 6px;
    text-align: center;
    background-color: #e6e9ef;
    color: #4c4f69;
    font-weight: bold;
}
QProgressBar::chunk {
    background-color: #1e66f5;
    border-radius: 4px;
}
QTabWidget::pane {
    border: 2px solid #ccd0da;
    border-radius: 8px;
    background-color: #e6e9ef;
}
QTabBar::tab {
    background-color: #ccd0da;
    padding: 10px 20px;
    margin: 2px;
    border-radius: 6px;
    color: #4c4f69;
}
QTabBar::tab:selected {
    background-color: #1e66f5;
    color: #eff1f5;
}
QStatusBar {
    background-color: #dce0e8;
    color: #6c6f85;
}
QLabel#titleLabel {
    font-size: 18pt;
    font-weight: bold;
    color: #1e66f5;
}
QLabel#subtitleLabel {
    font-size: 9pt;
    color: #6c6f85;
}
QLabel#aboutHeading {
    font-size: 16pt;
    font-weight: bold;
    color: #1e66f5;
}
QLabel#aboutSubheading {
    font-size: 11pt;
    font-weight: bold;
    color: #1a7f37;
}
QLabel#aboutBody {
    font-size: 10pt;
    color: #4c4f69;
}
QLabel#aboutMuted {
    font-size: 9pt;
    color: #5a6169;
}
QFrame#aboutSeparator {
    background-color: #ccd0da;
    max-height: 1px;
    border: none;
}
"""


THEMES = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
}
