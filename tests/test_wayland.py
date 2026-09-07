"""Test verifying native Wayland integration of Android Emulator Dock."""

import os
import sys
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from aed.ui.main_window import MainWindow

class TestWaylandIntegration(unittest.TestCase):
    def test_wayland_platform(self):
        # Enforce Wayland platform if available in environment
        if "WAYLAND_DISPLAY" in os.environ:
            os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"

        app = QApplication.instance() or QApplication(sys.argv)
        platform = app.platformName()
        print(f"\n[Wayland Test] Active Qt QPA Platform: {platform}")

        # If running under Wayland compositor, must be 'wayland'
        if os.environ.get("XDG_SESSION_TYPE") == "wayland":
            self.assertEqual(platform, "wayland", "App must run natively as wayland client")

        # Instantiate MainWindow
        win = MainWindow()
        win.show()
        app.processEvents()

        self.assertTrue(win.isVisible())
        self.assertIsNotNone(win.workspace)

        win.close()
        app.processEvents()

if __name__ == "__main__":
    unittest.main()
