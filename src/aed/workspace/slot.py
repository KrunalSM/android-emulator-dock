"""Visual UI slot hosting an EmulatorInstance with full toolbar, controls, and display."""

from typing import Optional
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMenu, QWidgetAction, QToolTip
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QKeyEvent, QAction

from aed.emulator.instance import EmulatorInstance
from aed.emulator.state import EmulatorState

class EmulatorSlot(QFrame):
    """Container widget representing a single workspace slot with complete controls."""

    close_requested = pyqtSignal(object)

    def __init__(self, instance: EmulatorInstance, parent=None):
        super().__init__(parent)
        self.instance = instance
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setLineWidth(1)
        self.setStyleSheet("""
            EmulatorSlot {
                background-color: #1e1e24;
                border: 1px solid #33333e;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 1. Header bar
        header = QFrame(self)
        header.setStyleSheet("background-color: #282832; border-radius: 6px; padding: 2px;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(6, 2, 6, 2)

        self.title_lbl = QLabel(self.instance.avd.display_name, self)
        font = QFont()
        font.setBold(True)
        self.title_lbl.setFont(font)
        self.title_lbl.setStyleSheet("color: #ffffff;")

        self.state_lbl = QLabel("Stopped", self)
        self.state_lbl.setStyleSheet("color: #aaaaaa; font-size: 11px;")

        self.fps_lbl = QLabel("", self)
        self.fps_lbl.setStyleSheet("color: #00d26a; font-size: 11px; font-weight: bold;")

        self.btn_power = QPushButton("Start", self)
        self.btn_power.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #388e3c; }
        """)
        self.btn_power.clicked.connect(self._toggle_power)

        self.btn_close = QPushButton("✕", self)
        self.btn_close.setToolTip("Close Slot")
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                border: none;
                font-size: 14px;
                padding: 2px 6px;
            }
            QPushButton:hover { color: #ff5555; }
        """)
        self.btn_close.clicked.connect(lambda: self.close_requested.emit(self))

        h_layout.addWidget(self.title_lbl)
        h_layout.addSpacing(8)
        h_layout.addWidget(self.state_lbl)
        h_layout.addSpacing(8)
        h_layout.addWidget(self.fps_lbl)
        h_layout.addStretch()
        h_layout.addWidget(self.btn_power)
        h_layout.addWidget(self.btn_close)

        # 2. Complete Common Toolbar
        toolbar = QFrame(self)
        toolbar.setStyleSheet("""
            QFrame {
                background-color: #22222a;
                border-radius: 5px;
                padding: 2px;
            }
            QPushButton {
                background-color: #333342;
                color: #e0e0e0;
                border: 1px solid #444455;
                border-radius: 4px;
                padding: 3px 7px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #45455c;
                color: #ffffff;
            }
            QPushButton:disabled {
                background-color: #282830;
                color: #555566;
                border-color: #33333c;
            }
        """)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(4, 2, 4, 2)
        tb_layout.setSpacing(4)

        # Navigation Buttons
        self.btn_back = QPushButton("◀ Back", self)
        self.btn_back.setToolTip("Back (GoBack)")
        self.btn_back.clicked.connect(self.instance.send_back)

        self.btn_home = QPushButton("● Home", self)
        self.btn_home.setToolTip("Home (GoHome)")
        self.btn_home.clicked.connect(self.instance.send_home)

        self.btn_recents = QPushButton("■ Recents", self)
        self.btn_recents.setToolTip("Overview / Recents (AppSwitch)")
        self.btn_recents.clicked.connect(self.instance.send_recents)

        # Device Buttons
        self.btn_rotate = QPushButton("↻ Rotate", self)
        self.btn_rotate.setToolTip("Rotate Device 90°")
        self.btn_rotate.clicked.connect(self.instance.rotate_device)

        self.btn_vol_down = QPushButton("🔉 Vol -", self)
        self.btn_vol_down.setToolTip("Volume Down")
        self.btn_vol_down.clicked.connect(self.instance.send_volume_down)

        self.btn_vol_up = QPushButton("🔊 Vol +", self)
        self.btn_vol_up.setToolTip("Volume Up")
        self.btn_vol_up.clicked.connect(self.instance.send_volume_up)

        self.btn_dev_power = QPushButton("⏻ Power", self)
        self.btn_dev_power.setToolTip("Android Power Key")
        self.btn_dev_power.clicked.connect(self.instance.send_power)

        self.btn_screenshot = QPushButton("📷 Screenshot", self)
        self.btn_screenshot.setToolTip("Capture Emulator Display Screenshot")
        self.btn_screenshot.clicked.connect(self._take_screenshot)

        # "More" escape hatch button
        self.btn_more = QPushButton("⋮ More ▾", self)
        self.btn_more.setToolTip("Advanced Extended Controls & Official Emulator Panels")
        self.btn_more.clicked.connect(self._show_more_menu)

        tb_layout.addWidget(self.btn_back)
        tb_layout.addWidget(self.btn_home)
        tb_layout.addWidget(self.btn_recents)
        tb_layout.addSpacing(4)
        tb_layout.addWidget(self.btn_rotate)
        tb_layout.addWidget(self.btn_vol_down)
        tb_layout.addWidget(self.btn_vol_up)
        tb_layout.addWidget(self.btn_dev_power)
        tb_layout.addWidget(self.btn_screenshot)
        tb_layout.addStretch()
        tb_layout.addWidget(self.btn_more)

        self._toolbar_buttons = [
            self.btn_back, self.btn_home, self.btn_recents,
            self.btn_rotate, self.btn_vol_down, self.btn_vol_up,
            self.btn_dev_power, self.btn_screenshot, self.btn_more
        ]

        layout.addWidget(header)
        layout.addWidget(toolbar)
        layout.addWidget(self.instance.surface, 1)

        # Connect instance signals
        self.instance.state_changed.connect(self._on_state_changed)
        self.instance.fps_updated.connect(self._on_fps_updated)
        self.instance.screenshot_saved.connect(self._on_screenshot_saved)
        self._on_state_changed(self.instance.state)

    def _show_more_menu(self):
        """Display full hierarchical menu of official Extended Controls."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #242430;
                color: #ffffff;
                border: 1px solid #3d3d50;
                padding: 4px;
            }
            QMenu::item {
                padding: 5px 20px 5px 20px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #4b4b6a;
            }
            QMenu::separator {
                height: 1px;
                background-color: #3d3d50;
                margin: 4px 8px;
            }
        """)

        # Quick Actions
        fp_action = menu.addAction("Touch Fingerprint Sensor")
        fp_action.triggered.connect(lambda: self.instance.send_fingerprint(1))

        # Fold/Unfold Posture Submenu
        fold_menu = menu.addMenu("Fold / Posture")
        fold_open = fold_menu.addAction("Opened")
        fold_open.triggered.connect(lambda: self.instance.set_fold_posture("POSTURE_OPENED"))
        fold_half = fold_menu.addAction("Half-Opened (Flex)")
        fold_half.triggered.connect(lambda: self.instance.set_fold_posture("POSTURE_HALF_OPENED"))
        fold_closed = fold_menu.addAction("Closed")
        fold_closed.triggered.connect(lambda: self.instance.set_fold_posture("POSTURE_CLOSED"))
        fold_tent = fold_menu.addAction("Tent")
        fold_tent.triggered.connect(lambda: self.instance.set_fold_posture("POSTURE_TENT"))

        menu.addSeparator()

        # Official Extended Controls Panes
        panes = [
            ("Extended Controls (Default)", "KEEP_CURRENT"),
            ("Location & Route Playback", "LOCATION"),
            ("Virtual Sensors & Accelerometer", "VIRT_SENSORS"),
            ("Battery & Power Source", "BATTERY"),
            ("Cellular & Network", "CELLULAR"),
            ("Camera Simulation", "CAMERA"),
            ("Microphone / Audio Input", "MICROPHONE"),
            ("Displays / Multi-Display", "MULTIDISPLAY"),
            ("Fingerprint Configuration", "FINGER"),
            ("Snapshots & Quickboot", "SNAPSHOT"),
            ("Screen Recording", "RECORD"),
            ("Telephone & SMS Call Simulation", "TELEPHONE"),
            ("D-Pad / Remote Controls", "DPAD"),
            ("Rotary Input", "ROTARY"),
            ("Sensor Replay", "SENSOR_REPLAY"),
            ("Google Play Services", "GOOGLE_PLAY"),
            ("Settings & Diagnostics", "SETTINGS"),
            ("Bug Report", "BUGREPORT"),
            ("Help & Documentation", "HELP"),
        ]

        for label, pane_id in panes:
            act = menu.addAction(label)
            act.triggered.connect(lambda checked=False, p=pane_id: self.instance.show_extended_controls(p))

        menu.exec(self.btn_more.mapToGlobal(QPoint(0, self.btn_more.height())))

    def _take_screenshot(self):
        path = self.instance.take_screenshot()
        if path:
            QToolTip.showText(
                self.btn_screenshot.mapToGlobal(QPoint(0, self.btn_screenshot.height())),
                f"Saved to {path.name}",
                self.btn_screenshot,
                msecShowTime=3000
            )

    def _on_screenshot_saved(self, path_str: str):
        pass

    def _toggle_power(self):
        if self.instance.state.can_start():
            self.instance.start()
        elif self.instance.state.is_active():
            self.instance.stop()

    def _on_state_changed(self, state: EmulatorState):
        self.state_lbl.setText(state.display_name())
        is_running = (state == EmulatorState.RUNNING)

        for btn in self._toolbar_buttons:
            btn.setEnabled(is_running)

        if is_running:
            self.btn_power.setText("Stop")
            self.btn_power.setStyleSheet("""
                QPushButton {
                    background-color: #c62828;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover { background-color: #d32f2f; }
            """)
        elif state == EmulatorState.STOPPED:
            self.btn_power.setText("Start")
            self.btn_power.setStyleSheet("""
                QPushButton {
                    background-color: #2e7d32;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover { background-color: #388e3c; }
            """)
            self.fps_lbl.setText("")
        else:
            self.btn_power.setText("Cancel")

    def _on_fps_updated(self, fps: float):
        if self.instance.state == EmulatorState.RUNNING:
            self.fps_lbl.setText(f"{fps:.1f} FPS")

    def keyPressEvent(self, event: QKeyEvent):
        key_text = event.text()
        key_code = None
        if event.key() == Qt.Key.Key_Backspace:
            key_code = "BackSpace"
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            key_code = "Enter"
        elif event.key() == Qt.Key.Key_Escape:
            key_code = "Escape"
        elif event.key() == Qt.Key.Key_Tab:
            key_code = "Tab"

        self.instance.send_key_event(key_text=key_text if key_text else None, key_code=key_code)
        super().keyPressEvent(event)
