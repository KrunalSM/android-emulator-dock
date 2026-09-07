"""Single Emulator instance managing process, discovery, gRPC connection, and renderer."""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QProcess, QTimer, pyqtSignal

from aed.avd.model import AvdInfo
from aed.connection.client import EmulatorConnection
from aed.connection.screenshot_service import ScreenshotService
from aed.connection.stream_worker import FrameStreamWorker
from aed.emulator.discovery import RunningEmulatorInfo, find_running_emulator_by_pid
from aed.emulator.state import EmulatorState
from aed.logging_util import get_logger
from aed.renderer.emulator_surface import EmulatorSurface

logger = get_logger("emulator.instance")


class EmulatorInstance(QObject):
    """Encapsulates a single Android Virtual Device instance lifecycle and gRPC bridge."""

    state_changed = pyqtSignal(EmulatorState)
    fps_updated = pyqtSignal(float)
    error_occurred = pyqtSignal(str)
    screenshot_saved = pyqtSignal(str)

    def __init__(self, avd: AvdInfo, emulator_binary: Path, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.avd = avd
        self.emulator_binary = emulator_binary
        self.state = EmulatorState.STOPPED

        self._process: Optional[QProcess] = None
        self._pid: Optional[int] = None
        self._discovery_info: Optional[RunningEmulatorInfo] = None
        self._connection: Optional[EmulatorConnection] = None
        self._stream_worker: Optional[FrameStreamWorker] = None
        self._screenshot_service: Optional[ScreenshotService] = None

        self._surface = EmulatorSurface()
        self._setup_surface_events()

        self._discovery_timer = QTimer(self)
        self._discovery_timer.setInterval(500)
        self._discovery_timer.timeout.connect(self._check_discovery)
        self._discovery_attempts = 0

    @property
    def surface(self) -> EmulatorSurface:
        return self._surface

    @property
    def connection(self) -> Optional[EmulatorConnection]:
        return self._connection

    def _set_state(self, new_state: EmulatorState):
        if self.state != new_state:
            self.state = new_state
            logger.info("[%s] State -> %s", self.avd.name, new_state.display_name())
            self.state_changed.emit(new_state)

    def _setup_surface_events(self):
        self._surface.touch_down.connect(self._on_touch_down)
        self._surface.touch_move.connect(self._on_touch_move)
        self._surface.touch_up.connect(self._on_touch_up)
        self._surface.wheel_scrolled.connect(self._on_wheel)

    def _on_touch_down(self, x: int, y: int):
        if self._connection and self._connection.is_connected:
            self._connection.send_touch(x, y, pressure=1)

    def _on_touch_move(self, x: int, y: int):
        if self._connection and self._connection.is_connected:
            self._connection.send_touch(x, y, pressure=1)

    def _on_touch_up(self, x: int, y: int):
        if self._connection and self._connection.is_connected:
            self._connection.send_touch(x, y, pressure=0)

    def _on_wheel(self, dx: int, dy: int):
        if self._connection and self._connection.is_connected:
            self._connection.inject_wheel(dx, dy)

    def send_key_event(self, key_text: Optional[str] = None, key_code: Optional[str] = None):
        if self._connection and self._connection.is_connected:
            self._connection.send_key(text=key_text, key_code=key_code)

    # Navigation & Hardware Controls
    def send_back(self):
        if self._connection and self._connection.is_connected:
            self._connection.send_back()

    def send_home(self):
        if self._connection and self._connection.is_connected:
            self._connection.send_home()

    def send_recents(self):
        if self._connection and self._connection.is_connected:
            self._connection.send_recents()

    def send_power(self):
        if self._connection and self._connection.is_connected:
            self._connection.send_power()

    def send_volume_up(self):
        if self._connection and self._connection.is_connected:
            self._connection.send_volume_up()

    def send_volume_down(self):
        if self._connection and self._connection.is_connected:
            self._connection.send_volume_down()

    def rotate_device(self):
        if self._connection and self._connection.is_connected:
            self._connection.rotate_device()

    def send_fingerprint(self, touch_id: int = 1):
        if self._connection and self._connection.is_connected:
            self._connection.send_fingerprint(touch_id)

    def set_fold_posture(self, posture: str):
        if self._connection and self._connection.is_connected:
            self._connection.set_fold_posture(posture)

    def take_screenshot(self) -> Optional[Path]:
        if self._screenshot_service:
            path = self._screenshot_service.capture_screenshot()
            if path:
                self.screenshot_saved.emit(str(path))
                return path
        return None

    def show_extended_controls(self, pane: str = "LOCATION"):
        if self._connection and self._connection.is_connected:
            self._connection.show_extended_controls(pane)

    def start(self):
        """Launch official emulator with full audio and boot animation support."""
        if not self.state.can_start():
            logger.warning("[%s] Cannot start in state %s", self.avd.name, self.state)
            return

        self._set_state(EmulatorState.LAUNCHING)
        
        # Clean up stale locks that could prevent launch
        if self.avd.path and self.avd.path.exists():
            import shutil
            for lock_item in self.avd.path.glob("*.lock"):
                try:
                    if lock_item.is_dir():
                        shutil.rmtree(lock_item, ignore_errors=True)
                    else:
                        lock_item.unlink(missing_ok=True)
                except OSError:
                    pass

        self._process = QProcess(self)

        # Retain hosting flags, remove -no-audio and -no-boot-anim for complete parity
        args = [
            "-avd",
            self.avd.name,
            "-qt-hide-window",
            "-grpc-use-token",
            "-idle-grpc-timeout",
            "300",
        ]

        self._process.errorOccurred.connect(self._on_process_error)
        self._process.finished.connect(self._on_process_finished)

        logger.info("[%s] Launching emulator: %s %s", self.avd.name, self.emulator_binary, " ".join(args))
        self._process.start(str(self.emulator_binary), args)

        if not self._process.waitForStarted(3000):
            self._set_state(EmulatorState.FAILED)
            self.error_occurred.emit(f"Failed to start emulator binary for {self.avd.name}")
            return

        self._pid = self._process.processId()
        logger.info("[%s] Emulator started with PID %d", self.avd.name, self._pid)

        self._set_state(EmulatorState.WAITING_FOR_DISCOVERY)
        self._discovery_attempts = 0
        self._discovery_timer.start()

    def _check_discovery(self):
        self._discovery_attempts += 1
        if not self._pid:
            self._discovery_timer.stop()
            return

        info = find_running_emulator_by_pid(self._pid)
        if info:
            self._discovery_timer.stop()
            self._discovery_info = info
            logger.info("[%s] Discovered gRPC port %d for PID %d", self.avd.name, info.grpc_port, self._pid)
            self._connect_grpc()
            return

        if self._discovery_attempts > 60:  # 30 seconds timeout
            self._discovery_timer.stop()
            self._set_state(EmulatorState.FAILED)
            self.error_occurred.emit(f"Timed out waiting for discovery info for {self.avd.name}")

    def _connect_grpc(self):
        if not self._discovery_info:
            return

        self._set_state(EmulatorState.CONNECTING)
        self._connection = EmulatorConnection(
            host="127.0.0.1", port=self._discovery_info.grpc_port, token=self._discovery_info.grpc_token
        )

        if not self._connection.connect():
            self._set_state(EmulatorState.FAILED)
            self.error_occurred.emit(f"Could not connect to gRPC on port {self._discovery_info.grpc_port}")
            return

        self._screenshot_service = ScreenshotService(self._connection, self.avd.name)
        self._set_state(EmulatorState.BOOTING)
        self._start_stream()

    def _start_stream(self):
        if not self._connection:
            return

        self._stream_worker = FrameStreamWorker(self._connection, target_width=1080, target_height=2400)
        self._stream_worker.frame_ready.connect(self._on_frame_ready)
        self._stream_worker.fps_updated.connect(self._on_fps_updated)
        self._stream_worker.start()

    def _on_frame_ready(self, frame_bytes: bytes, w: int, h: int, bpl: int):
        # Discard late arriving frames if stopping or stopped
        if not self.state.is_active():
            return
        if self.state == EmulatorState.BOOTING:
            self._set_state(EmulatorState.RUNNING)
        self._surface.update_frame(frame_bytes, w, h, bpl)

    def _on_fps_updated(self, fps: float):
        if self.state == EmulatorState.RUNNING:
            self.fps_updated.emit(fps)

    def stop(self):
        """Cleanly terminate emulator and reset renderer."""
        self._set_state(EmulatorState.STOPPING)
        self._discovery_timer.stop()

        if self._stream_worker:
            self._stream_worker.stop()
            self._stream_worker.wait(3000)
            self._stream_worker = None

        if self._connection:
            self._connection.disconnect()
            self._connection = None

        self._screenshot_service = None

        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            logger.info("[%s] Terminating emulator process PID %s", self.avd.name, self._pid)
            self._process.terminate()
            if not self._process.waitForFinished(10000):
                self._process.kill()

        # Clear surface to remove frozen frame
        self._surface.clear()
        self._set_state(EmulatorState.STOPPED)

    def _on_process_error(self, err):
        logger.error("[%s] Process error: %s", self.avd.name, err)
        self._set_state(EmulatorState.FAILED)

    def _on_process_finished(self, exit_code, exit_status):
        logger.info("[%s] Process finished (code=%d, status=%s)", self.avd.name, exit_code, exit_status)
        if self.state != EmulatorState.STOPPED:
            self._surface.clear()
            self._set_state(EmulatorState.DISCONNECTED)
