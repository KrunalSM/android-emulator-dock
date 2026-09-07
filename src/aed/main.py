"""Application entry point for Android Emulator Dock."""

import os
import sys

# Ensure Wayland platform plugin is preferred by Qt
if "QT_QPA_PLATFORM" not in os.environ and "WAYLAND_DISPLAY" in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from aed.ui.main_window import MainWindow
from aed.ui.theme import apply_dark_theme
from aed.logging_util import get_logger

logger = get_logger("main")

def main():
    logger.info("Starting Android Emulator Dock...")
    app = QApplication(sys.argv)
    app.setApplicationName("Android Emulator Dock")
    app.setOrganizationName("AED")
    apply_dark_theme(app)

    logger.info("Qt QPA Platform: %s", app.platformName())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
