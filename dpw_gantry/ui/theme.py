"""Theme and styling definitions for DPW Gantry application."""

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtCore import Qt


class ThemeColors:
    # Backgrounds
    BG_DARK = "#18191f"
    BG_PANEL = "#21222c"
    BG_PANEL_ALT = "#282a36"
    BG_INPUT = "#2f3142"
    BG_HOVER = "#3c3f52"

    # Borders & Dividers
    BORDER = "#414458"
    BORDER_FOCUS = "#6272a4"

    # Foregrounds
    TEXT_MAIN = "#f8f8f2"
    TEXT_MUTED = "#8be9fd"
    TEXT_SECONDARY = "#9ea3c0"

    # Accents & Status
    CYAN_ACCENT = "#8be9fd"
    BLUE_ACCENT = "#50fa7b"
    GREEN_SUCCESS = "#50fa7b"
    AMBER_WARNING = "#ffb86c"
    RED_ALERT = "#ff5555"
    PURPLE_ACCENT = "#bd93f9"
    PINK_ACCENT = "#ff79c6"

    # Canvas Toolpath Colors
    CANVAS_BED_BG = QColor(24, 25, 31)
    CANVAS_GRID_MAJOR = QColor(60, 63, 82, 180)
    CANVAS_GRID_MINOR = QColor(45, 47, 62, 100)
    CANVAS_ORIGIN = QColor(255, 85, 85, 220)
    
    PATH_OUTLINE = QColor(139, 233, 253, 240)        # Light cyan
    PATH_FILL_HATCH = QColor(255, 184, 108, 220)     # Orange
    PATH_FILL_SPIRAL = QColor(189, 147, 249, 220)    # Purple
    PATH_RAPID_TRAVEL = QColor(255, 85, 85, 160)     # Red dashed
    PATH_NOZZLE_HEAD = QColor(80, 250, 123, 255)     # Green neon


DARK_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #18191f;
    color: #f8f8f2;
    font-family: "Segoe UI", "Helvetica Neue", sans-serif;
    font-size: 13px;
}

QWidget {
    color: #f8f8f2;
}

QTabWidget::pane {
    border: 1px solid #3c3f52;
    background-color: #21222c;
    border-radius: 4px;
}

QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

QTabBar::tab {
    background-color: #1c1d25;
    color: #9ea3c0;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    font-weight: 500;
}

QTabBar::tab:selected {
    background-color: #21222c;
    color: #8be9fd;
    border-bottom: 2px solid #8be9fd;
}

QTabBar::tab:hover:!selected {
    background-color: #282a36;
    color: #f8f8f2;
}

QGroupBox {
    border: 1px solid #3c3f52;
    border-radius: 6px;
    margin-top: 18px;
    padding-top: 14px;
    padding-bottom: 8px;
    padding-left: 8px;
    padding-right: 8px;
    font-weight: bold;
    background-color: #21222c;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 4px;
    color: #8be9fd;
}

QPushButton {
    background-color: #2f3142;
    color: #f8f8f2;
    border: 1px solid #45485f;
    border-radius: 5px;
    padding: 6px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #3e4157;
    border-color: #8be9fd;
}

QPushButton:pressed {
    background-color: #282a36;
}

QPushButton:disabled {
    background-color: #1e1f29;
    color: #5d6179;
    border-color: #2c2e3d;
}

/* Primary Action Buttons */
QPushButton#btn_primary {
    background-color: #bd93f9;
    color: #18191f;
    border: none;
    font-weight: bold;
}
QPushButton#btn_primary:hover {
    background-color: #caa8fa;
}

/* Success Action Buttons */
QPushButton#btn_success {
    background-color: #50fa7b;
    color: #18191f;
    border: none;
    font-weight: bold;
}
QPushButton#btn_success:hover {
    background-color: #69fb8d;
}

/* Danger / Emergency Buttons */
QPushButton#btn_danger {
    background-color: #ff5555;
    color: #ffffff;
    border: none;
    font-weight: bold;
    font-size: 14px;
}
QPushButton#btn_danger:hover {
    background-color: #ff6e6e;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #282a36;
    color: #f8f8f2;
    border: 1px solid #414458;
    border-radius: 4px;
    padding: 5px 8px;
    selection-background-color: #6272a4;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #8be9fd;
}

QComboBox QAbstractItemView {
    background-color: #282a36;
    color: #f8f8f2;
    border: 1px solid #414458;
    selection-background-color: #44475a;
}

QSlider::groove:horizontal {
    border: 1px solid #414458;
    height: 6px;
    background: #282a36;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #ffb86c;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #f8f8f2;
    border: 1px solid #ffb86c;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #ffb86c;
}

QProgressBar {
    border: 1px solid #414458;
    border-radius: 4px;
    background-color: #282a36;
    text-align: center;
    color: #f8f8f2;
    font-weight: bold;
}

QProgressBar::chunk {
    background-color: #50fa7b;
    border-radius: 3px;
}

QScrollBar:vertical {
    border: none;
    background: #18191f;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #414458;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #6272a4;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QToolBar {
    background-color: #1e1f29;
    border-bottom: 1px solid #3c3f52;
    spacing: 6px;
    padding: 4px;
}

QToolButton {
    background-color: transparent;
    color: #f8f8f2;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 6px 10px;
    font-weight: 500;
}

QToolButton:hover {
    background-color: #2f3142;
    border-color: #45485f;
}

QToolButton:checked {
    background-color: #3c3f52;
    border-color: #8be9fd;
    color: #8be9fd;
}

QStatusBar {
    background-color: #18191f;
    color: #9ea3c0;
    border-top: 1px solid #282a36;
}

QPlainTextEdit, QTextEdit {
    background-color: #1e1f29;
    color: #f8f8f2;
    border: 1px solid #3c3f52;
    border-radius: 4px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
}
"""
