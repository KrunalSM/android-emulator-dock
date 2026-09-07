"""Comprehensive dark theme and palette configuration for Android Emulator Dock."""

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication


def apply_dark_theme(app: QApplication):
    """Apply a complete dark QPalette and global stylesheet to eliminate white-on-white artifacts."""
    app.setStyle("Fusion")

    dark_palette = QPalette()
    # Base background colors
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(18, 18, 22))
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(240, 240, 240))
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(28, 28, 35))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(36, 36, 45))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(30, 30, 38))
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(240, 240, 240))
    dark_palette.setColor(QPalette.ColorRole.Text, QColor(240, 240, 240))
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(40, 40, 52))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(240, 240, 240))
    dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 60, 60))
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(64, 158, 255))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(60, 110, 200))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

    # Disabled colors
    dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(110, 110, 125))
    dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(110, 110, 125))
    dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(110, 110, 125))
    dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, QColor(45, 45, 55))

    app.setPalette(dark_palette)

    # Comprehensive global stylesheet covering all widgets, popups, menus, combo views, dialogs, and tooltips
    global_stylesheet = """
        * {
            color: #e6e6e6;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        QWidget {
            background-color: #121216;
            selection-background-color: #3d5a80;
            selection-color: #ffffff;
        }

        QMainWindow, QDialog, QMessageBox {
            background-color: #121216;
            color: #ffffff;
        }

        QToolBar {
            background-color: #1a1a22;
            border-bottom: 1px solid #2d2d3c;
            spacing: 8px;
            padding: 5px;
        }

        QLabel {
            background-color: transparent;
            color: #d0d0d8;
        }

        QToolTip {
            background-color: #242430;
            color: #ffffff;
            border: 1px solid #4a4a60;
            padding: 5px 8px;
            border-radius: 4px;
        }

        /* ComboBox and its Popup Dropdown */
        QComboBox {
            background-color: #262632;
            color: #ffffff;
            border: 1px solid #3d3d52;
            border-radius: 5px;
            padding: 5px 12px;
            min-height: 20px;
        }

        QComboBox:hover {
            border: 1px solid #555575;
            background-color: #2e2e3d;
        }

        QComboBox:on {
            border-color: #6272a4;
        }

        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 24px;
            border-left-width: 0px;
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
        }

        QComboBox QAbstractItemView {
            background-color: #20202a;
            color: #ffffff;
            border: 1px solid #444458;
            selection-background-color: #3e4a68;
            selection-color: #ffffff;
            outline: 0px;
            padding: 4px;
        }

        QComboBox QAbstractItemView::item {
            min-height: 26px;
            padding: 3px 8px;
            border-radius: 3px;
        }

        QComboBox QAbstractItemView::item:hover {
            background-color: #2f2f3f;
            color: #ffffff;
        }

        QComboBox QAbstractItemView::item:selected {
            background-color: #3e4a68;
            color: #ffffff;
        }

        /* Buttons */
        QPushButton {
            background-color: #343444;
            color: #ffffff;
            border: 1px solid #48485e;
            border-radius: 5px;
            padding: 5px 12px;
            font-weight: 500;
        }

        QPushButton:hover {
            background-color: #424257;
            border-color: #5c5c78;
        }

        QPushButton:pressed {
            background-color: #2a2a38;
        }

        QPushButton:disabled {
            background-color: #1e1e26;
            color: #606072;
            border-color: #2c2c38;
        }

        /* Menus */
        QMenu {
            background-color: #20202a;
            color: #ffffff;
            border: 1px solid #3d3d52;
            border-radius: 6px;
            padding: 5px;
        }

        QMenu::item {
            background-color: transparent;
            color: #e0e0e8;
            padding: 6px 24px 6px 16px;
            border-radius: 4px;
        }

        QMenu::item:selected {
            background-color: #3e4a68;
            color: #ffffff;
        }

        QMenu::item:disabled {
            color: #555566;
        }

        QMenu::separator {
            height: 1px;
            background-color: #323242;
            margin: 4px 6px;
        }

        /* Scrollbars */
        QScrollBar:vertical {
            background-color: #16161c;
            width: 10px;
            margin: 0px;
        }

        QScrollBar::handle:vertical {
            background-color: #383848;
            min-height: 20px;
            border-radius: 5px;
        }

        QScrollBar::handle:vertical:hover {
            background-color: #4c4c62;
        }

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }

        /* Status Bar */
        QStatusBar {
            background-color: #16161c;
            color: #9999a8;
            border-top: 1px solid #282834;
        }

        QStatusBar QLabel {
            color: #9999a8;
        }
    """
    app.setStyleSheet(global_stylesheet)
