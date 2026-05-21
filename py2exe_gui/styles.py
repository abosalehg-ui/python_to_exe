"""Qt stylesheet definitions (Catppuccin-inspired dark + light themes)."""


# Log line colors (used as inline HTML when appending to QTextEdit).
class LogColors:
    """Color palette for log entries — works on both themes."""

    INFO = "#89b4fa"
    SUCCESS = "#40a02b"
    WARNING = "#df8e1d"
    ERROR = "#d20f39"
    MUTED = "#6c7086"


DARK_THEME = """
QMainWindow {
    background-color: #1e1e2e;
}
QWidget {
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 12px;
    color: #cdd6f4;
}
QGroupBox {
    font-weight: bold;
    font-size: 13px;
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
    border: none;
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
    font-size: 11px;
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
    font-size: 24px;
    font-weight: bold;
    color: #89b4fa;
}
QLabel#subtitleLabel {
    font-size: 12px;
    color: #6c7086;
}
"""


LIGHT_THEME = """
QMainWindow {
    background-color: #eff1f5;
}
QWidget {
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 12px;
    color: #4c4f69;
}
QGroupBox {
    font-weight: bold;
    font-size: 13px;
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
    border: none;
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
    font-size: 11px;
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
    font-size: 24px;
    font-weight: bold;
    color: #1e66f5;
}
QLabel#subtitleLabel {
    font-size: 12px;
    color: #6c6f85;
}
"""


THEMES = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
}
