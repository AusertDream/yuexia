"""全局主题 - 妹居物语风格（粉白温馨）"""

# 色板
BG = "#fff0f5"
CARD = "#ffffff"
CARD_T = "rgba(255,255,255,220)"
SIDEBAR = "#fce4ec"
BORDER = "#f8bbd0"
ACCENT = "#e91e63"
ACCENT_L = "#f48fb1"
TEXT = "#37474f"
TEXT_SUB = "#78909c"
HOVER = "#fce4ec"


def apply_theme(app):
    app.setStyleSheet(f"""
        * {{
            font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
        }}
        QMainWindow {{
            background: {BG};
        }}
        QWidget {{
            color: {TEXT};
            background: {BG};
        }}
        QGroupBox {{
            background: {CARD};
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 8px;
            margin-top: 14px;
            padding: 16px 8px 8px 8px;
            font-weight: bold;
        }}
        QGroupBox::title {{
            subcontrol-position: top left;
            padding: 0 8px;
            color: {ACCENT};
        }}
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            background: {CARD};
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 6px;
            padding: 5px 8px;
            min-height: 22px;
        }}
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
            border: 1px solid {ACCENT};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox QAbstractItemView {{
            background: {CARD};
            color: {TEXT};
            selection-background-color: {HOVER};
            border: 1px solid {BORDER};
        }}
        QCheckBox::indicator {{
            width: 18px; height: 18px;
            border-radius: 4px;
            border: 1px solid {BORDER};
            background: {CARD};
        }}
        QCheckBox::indicator:checked {{
            background: {ACCENT};
            border-color: {ACCENT};
        }}
        QPushButton {{
            background: {ACCENT};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 7px 18px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background: {ACCENT_L};
        }}
        QPushButton:pressed {{
            background: #c2185b;
        }}
        QScrollArea {{
            border: none;
            background: {BG};
        }}
        QScrollBar:vertical {{
            background: {HOVER};
            width: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {BORDER};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QPlainTextEdit {{
            background: {CARD};
            color: {TEXT};
            border: none;
            font-family: Consolas, "Courier New", monospace;
            font-size: 12px;
            padding: 8px;
        }}
        QToolBar {{
            background: {CARD_T};
            border-bottom: 1px solid {BORDER};
            spacing: 8px;
            padding: 2px 8px;
        }}
        QToolBar QToolButton {{
            background: transparent;
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 6px;
            padding: 4px 12px;
        }}
        QToolBar QToolButton:checked {{
            background: {ACCENT};
            color: white;
            border-color: {ACCENT};
        }}
        QListWidget {{
            background: {SIDEBAR};
            border: none;
            color: {TEXT};
            font-size: 13px;
            outline: none;
        }}
        QListWidget::item {{
            padding: 14px 4px;
            border: none;
        }}
        QListWidget::item:selected {{
            background: {CARD_T};
            color: {TEXT};
            border-left: 3px solid {ACCENT};
        }}
        QLabel {{
            color: {TEXT};
            background: transparent;
        }}
    """)
