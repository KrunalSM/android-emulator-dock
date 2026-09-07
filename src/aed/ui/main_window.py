"""Main Application Window for Android Emulator Dock (native Wayland)."""

from typing import Optional, List
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QToolBar,
    QComboBox, QPushButton, QLabel, QMessageBox, QStatusBar
)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt

from aed.platform.sdk import find_android_sdk, get_emulator_binary
from aed.avd.discovery import list_avds
from aed.avd.model import AvdInfo
from aed.emulator.instance import EmulatorInstance
from aed.workspace.slot import EmulatorSlot
from aed.workspace.manager import WorkspaceLayoutManager
from aed.logging_util import get_logger

logger = get_logger("ui.mainwindow")

class MainWindow(QMainWindow):
    """Main window hosting emulator workspace."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Android Emulator Dock (Wayland Native)")
        self.resize(1200, 900)

        self._sdk_path = find_android_sdk()
        self._emulator_bin = get_emulator_binary(self._sdk_path)
        self._avds: List[AvdInfo] = []

        self._init_ui()
        self._refresh_avds()

    def _init_ui(self):
        # Dark modern palette
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121216;
            }
            QToolBar {
                background-color: #1a1a20;
                border-bottom: 1px solid #2d2d38;
                padding: 6px;
                spacing: 8px;
            }
            QComboBox {
                background-color: #2b2b36;
                color: #ffffff;
                border: 1px solid #3d3d4e;
                border-radius: 4px;
                padding: 4px 10px;
                min-width: 180px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QPushButton {
                background-color: #3d3d52;
                color: #ffffff;
                border: 1px solid #4d4d65;
                border-radius: 4px;
                padding: 5px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4f4f6b;
            }
            QLabel {
                color: #cccccc;
            }
            QStatusBar {
                background-color: #16161c;
                color: #888888;
            }
        """)

        # Toolbar
        toolbar = QToolBar("Controls", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        toolbar.addWidget(QLabel(" AVD: "))
        self.avd_combo = QComboBox(self)
        toolbar.addWidget(self.avd_combo)

        self.btn_add_avd = QPushButton("+ Add to Workspace", self)
        self.btn_add_avd.clicked.connect(self._add_selected_avd)
        toolbar.addWidget(self.btn_add_avd)

        self.btn_refresh = QPushButton("↻ Refresh", self)
        self.btn_refresh.clicked.connect(self._refresh_avds)
        toolbar.addWidget(self.btn_refresh)

        toolbar.addSeparator()

        toolbar.addWidget(QLabel(" Layout: "))
        self.layout_combo = QComboBox(self)
        self.layout_combo.addItems(["Auto", "Single", "Two Columns", "Grid"])
        self.layout_combo.currentTextChanged.connect(self._on_layout_changed)
        toolbar.addWidget(self.layout_combo)

        # Central workspace
        self.workspace = WorkspaceLayoutManager(self)
        self.setCentralWidget(self.workspace)

        # Status bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        if self._emulator_bin:
            self.status_bar.showMessage(f"SDK Ready: {self._emulator_bin}")
        else:
            self.status_bar.showMessage("Android SDK / Emulator not found! Please check configuration.")

    def _refresh_avds(self):
        self.avd_combo.clear()
        self._avds = list_avds(self._emulator_bin)
        for avd in self._avds:
            self.avd_combo.addItem(avd.display_name, avd)
        if self._avds:
            self.status_bar.showMessage(f"Discovered {len(self._avds)} AVDs.")
        else:
            self.status_bar.showMessage("No AVDs found.")

    def _add_selected_avd(self):
        idx = self.avd_combo.currentIndex()
        if idx < 0 or idx >= len(self._avds):
            return

        avd = self._avds[idx]
        if not self._emulator_bin or not self._emulator_bin.exists():
            QMessageBox.critical(
                self, "SDK Error",
                "Official emulator executable not found.\nPlease set ANDROID_HOME or configure SDK location."
            )
            return

        instance = EmulatorInstance(avd=avd, emulator_binary=self._emulator_bin, parent=self)
        slot = EmulatorSlot(instance=instance, parent=self.workspace)
        self.workspace.add_slot(slot)
        self.status_bar.showMessage(f"Added {avd.display_name} to workspace.")

    def _on_layout_changed(self, text: str):
        mapping = {
            "Auto": "AUTO",
            "Single": "SINGLE",
            "Two Columns": "COLUMNS",
            "Grid": "GRID",
        }
        mode = mapping.get(text, "AUTO")
        self.workspace.set_mode(mode)

    def closeEvent(self, event):
        """Clean shutdown of all running emulators on window close."""
        logger.info("Closing main window, stopping all running emulator instances...")
        for slot in self.workspace.slots:
            slot.instance.stop()
        super().closeEvent(event)
