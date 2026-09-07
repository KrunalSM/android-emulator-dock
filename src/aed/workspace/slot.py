"""Visual UI slot hosting an EmulatorInstance with status bar, actions, and display."""

from typing import Optional
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QToolButton, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QKeyEvent

from aed.emulator.instance import EmulatorInstance
from aed.emulator.state import EmulatorState

class EmulatorSlot(QFrame):
    """Container widget representing a single workspace slot."""

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

        # Header bar
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

        # Controls
        self.btn_ext_ctrl = QPushButton("⚙ Extended Controls", self)
        self.btn_ext_ctrl.setStyleSheet("""
            QPushButton {
                background-color: #3b3b4d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #4b4b60; }
        """)
        self.btn_ext_ctrl.clicked.connect(self._open_extended_controls)

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
        h_layout.addWidget(self.btn_ext_ctrl)
        h_layout.addWidget(self.btn_power)
        h_layout.addWidget(self.btn_close)

        layout.addWidget(header)
        layout.addWidget(self.instance.surface, 1)

        # Connect signals
        self.instance.state_changed.connect(self._on_state_changed)
        self.instance.fps_updated.connect(self._on_fps_updated)
        self._on_state_changed(self.instance.state)

    def _open_extended_controls(self):
        self.instance.show_extended_controls("LOCATION")

    def _toggle_power(self):
        if self.instance.state.can_start():
            self.instance.start()
        elif self.instance.state.is_active():
            self.instance.stop()

    def _on_state_changed(self, state: EmulatorState):
        self.state_lbl.setText(state.display_name())
        if state == EmulatorState.RUNNING:
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
            self.btn_ext_ctrl.setEnabled(True)
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
            self.btn_ext_ctrl.setEnabled(False)
            self.fps_lbl.setText("")
        else:
            self.btn_power.setText("Cancel")
            self.btn_ext_ctrl.setEnabled(False)

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
