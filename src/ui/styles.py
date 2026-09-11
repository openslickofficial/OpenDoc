"""
Accessible High-Contrast Design System for Snapdragon Document Assistant.
Provides dark slate color tokens, accessible typography (14px+ default),
and comprehensive QSS stylesheets for all PySide6 widgets.
"""

# Color Palette Tokens
BG_MAIN = "#11121c"
BG_CARD = "#1a1c2b"
BG_CARD_HOVER = "#232538"
BG_INPUT = "#161824"
BORDER_DEFAULT = "#32364c"
BORDER_FOCUS = "#00d2ff"

TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#b8bdd4"
TEXT_MUTED = "#7a809b"

ACCENT_PRIMARY = "#ff4b6e"  # Snapdragon Crimson
ACCENT_PRIMARY_HOVER = "#ff6b87"
ACCENT_PRIMARY_ACTIVE = "#e03759"
ACCENT_CYAN = "#00d2ff"

STATE_SUCCESS_BG = "#0c2b18"
STATE_SUCCESS_BORDER = "#00e676"
STATE_SUCCESS_TEXT = "#69f0ae"

STATE_WARNING_BG = "#331f00"
STATE_WARNING_BORDER = "#ffb300"
STATE_WARNING_TEXT = "#ffd54f"

STATE_ERROR_BG = "#330a14"
STATE_ERROR_BORDER = "#ff3366"
STATE_ERROR_TEXT = "#ff80ab"

STATE_INFO_BG = "#082538"
STATE_INFO_BORDER = "#00b0ff"
STATE_INFO_TEXT = "#80d8ff"

GLOBAL_STYLESHEET = f"""
/* Global Reset & Base Typography */
QWidget {{
    background-color: {BG_MAIN};
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', 'SF Pro Text', 'Arial', sans-serif;
    font-size: 14px;
    selection-background-color: {ACCENT_PRIMARY};
    selection-color: #ffffff;
}}

/* Main Window */
QMainWindow {{
    background-color: {BG_MAIN};
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: {BG_CARD};
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_DEFAULT};
    min-height: 24px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT_CYAN};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* Cards & Frames */
QFrame#cardFrame {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 10px;
}}

QFrame#dropArea {{
    background-color: {BG_INPUT};
    border: 2px dashed {BORDER_DEFAULT};
    border-radius: 12px;
}}
QFrame#dropArea:hover {{
    border-color: {ACCENT_CYAN};
    background-color: {BG_CARD};
}}

/* Primary Buttons */
QPushButton#primaryButton {{
    background-color: {ACCENT_PRIMARY};
    color: #ffffff;
    font-size: 15px;
    font-weight: bold;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
}}
QPushButton#primaryButton:hover {{
    background-color: {ACCENT_PRIMARY_HOVER};
}}
QPushButton#primaryButton:pressed {{
    background-color: {ACCENT_PRIMARY_ACTIVE};
}}
QPushButton#primaryButton:disabled {{
    background-color: #43212c;
    color: #885c6b;
}}

/* Secondary Buttons */
QPushButton#secondaryButton {{
    background-color: {BG_CARD_HOVER};
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 600;
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 6px;
    padding: 8px 16px;
}}
QPushButton#secondaryButton:hover {{
    border-color: {ACCENT_CYAN};
    background-color: {BORDER_DEFAULT};
}}
QPushButton#secondaryButton:pressed {{
    background-color: {BG_CARD};
}}

/* Text Fields & Inputs */
QComboBox {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    font-weight: 500;
}}
QComboBox:hover {{
    border-color: {ACCENT_CYAN};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_DEFAULT};
    selection-background-color: {ACCENT_PRIMARY};
    selection-color: #ffffff;
    padding: 4px;
}}

QCheckBox {{
    font-size: 13px;
    color: {TEXT_PRIMARY};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid {BORDER_DEFAULT};
    background-color: {BG_INPUT};
}}
QCheckBox::indicator:hover {{
    border-color: {ACCENT_CYAN};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT_PRIMARY};
    border-color: {ACCENT_PRIMARY};
}}

/* Tab Widget */
QTabWidget::pane {{
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 8px;
    background-color: {BG_CARD};
    top: -1px;
}}
QTabBar::tab {{
    background-color: {BG_MAIN};
    color: {TEXT_SECONDARY};
    font-weight: 600;
    font-size: 13px;
    padding: 10px 18px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    border: 1px solid transparent;
}}
QTabBar::tab:hover {{
    color: {TEXT_PRIMARY};
    background-color: {BG_CARD_HOVER};
}}
QTabBar::tab:selected {{
    background-color: {BG_CARD};
    color: {ACCENT_CYAN};
    border: 1px solid {BORDER_DEFAULT};
    border-bottom: 1px solid {BG_CARD};
}}

/* Text Editors & Document Viewers */
QTextEdit {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 6px;
    padding: 12px;
    font-size: 15px;
    line-height: 1.5;
}}
QTextEdit:focus {{
    border-color: {BORDER_FOCUS};
}}

/* Table Widget */
QTableWidget {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_DEFAULT};
    gridline-color: {BORDER_DEFAULT};
    border-radius: 6px;
    font-size: 13px;
}}
QTableWidget::item {{
    padding: 8px;
}}
QHeaderView::section {{
    background-color: {BG_CARD};
    color: {TEXT_SECONDARY};
    font-weight: 600;
    font-size: 12px;
    border: none;
    border-bottom: 1px solid {BORDER_DEFAULT};
    border-right: 1px solid {BORDER_DEFAULT};
    padding: 8px;
}}

/* Sliders */
QSlider::groove:horizontal {{
    height: 6px;
    background: {BORDER_DEFAULT};
    border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT_PRIMARY};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: #ffffff;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background: {ACCENT_CYAN};
}}
"""
