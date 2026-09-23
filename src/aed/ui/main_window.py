"""Main Application Window for Android Emulator Dock (native Wayland)."""

from typing import List

from PyQt6.QtCore import QSettings, QTimer
from PyQt6.QtWidgets import QComboBox, QLabel, QMainWindow, QMessageBox, QPushButton, QStatusBar, QToolBar

from aed.avd.discovery import list_avds
from aed.avd.model import AvdInfo
from aed.emulator.instance import EmulatorInstance
from aed.emulator.launcher import GpuMode
from aed.logging_util import get_logger
from aed.platform.sdk import find_android_sdk, get_emulator_binary
from aed.workspace.manager import WorkspaceLayoutManager
from aed.workspace.slot import EmulatorSlot

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
        QTimer.singleShot(0, self._check_sdk_on_startup)

    def _check_sdk_on_startup(self):
        if not self._emulator_bin:
            QMessageBox.warning(
                self,
                "Android SDK Not Found",
                "Could not locate the official Android Emulator executable.\n\n"
                "Please ensure the Android SDK is installed and ANDROID_HOME "
                "or ANDROID_SDK_ROOT is set in your environment variables.",
            )

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

        toolbar.addSeparator()

        toolbar.addWidget(QLabel(" GPU Rendering: "))
        self.gpu_combo = QComboBox(self)
        self.gpu_combo.addItem("Automatic / Default", "automatic")
        self.gpu_combo.addItem("NVIDIA GPU", "nvidia")
        self.gpu_combo.setToolTip(
            "NVIDIA GPU Rendering:\n"
            "Use NVIDIA PRIME offloading and host GPU rendering for emulator instances."
        )
        saved_gpu = self._load_gpu_setting()
        idx = self.gpu_combo.findData(saved_gpu)
        if idx >= 0:
            self.gpu_combo.setCurrentIndex(idx)
        self.gpu_combo.currentIndexChanged.connect(self._on_gpu_mode_changed)
        toolbar.addWidget(self.gpu_combo)

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

    SETTINGS_KEY_GPU = "gpu_rendering"

    def _load_gpu_setting(self) -> str:
        """Load persisted GPU rendering setting, defaulting to 'automatic'."""
        settings = QSettings("AED", "Android Emulator Dock")
        val = settings.value(self.SETTINGS_KEY_GPU, "automatic", type=str)
        return val if val in ("automatic", "nvidia") else "automatic"

    def _save_gpu_setting(self, mode_str: str):
        """Persist user GPU rendering preference."""
        settings = QSettings("AED", "Android Emulator Dock")
        settings.setValue(self.SETTINGS_KEY_GPU, mode_str)

    @property
    def current_gpu_mode(self) -> str:
        """Current globally selected GPU rendering mode."""
        return self.gpu_combo.currentData() or "automatic"

    def _on_gpu_mode_changed(self, index: int):
        """Handle global GPU rendering dropdown selection change."""
        mode_str = self.current_gpu_mode
        self._save_gpu_setting(mode_str)
        logger.info("Global GPU rendering setting changed to: %s", mode_str)
        # Update stopped slots that haven't been explicitly overridden
        for slot in self.workspace.slots:
            if slot.instance.state.can_start() and not slot.instance.has_custom_gpu_override:
                slot.instance.gpu_mode = mode_str
                slot.update_gpu_indicator()

    def _add_selected_avd(self):
        idx = self.avd_combo.currentIndex()
        if idx < 0 or idx >= len(self._avds):
            return

        avd = self._avds[idx]
        if not self._emulator_bin or not self._emulator_bin.exists():
            QMessageBox.critical(
                self,
                "SDK Error",
                "Official emulator executable not found.\nPlease set ANDROID_HOME or configure SDK location.",
            )
            return

        instance = EmulatorInstance(
            avd=avd,
            emulator_binary=self._emulator_bin,
            gpu_mode=self.current_gpu_mode,
            parent=self,
        )
        slot = EmulatorSlot(instance=instance, parent=self.workspace)
        self.workspace.add_slot(slot)
        self.status_bar.showMessage(
            f"Added {avd.display_name} to workspace (GPU: {instance.gpu_mode.display_name()})."
        )

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
