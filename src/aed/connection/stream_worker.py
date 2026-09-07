"""Dedicated worker thread for gRPC screenshot frame streaming.

Ensures zero UI thread blocking during network and frame consumption.
"""

import time

from PyQt6.QtCore import QThread, pyqtSignal

from aed.connection.client import EmulatorConnection
from aed.logging_util import get_logger

logger = get_logger("connection.stream")


class FrameStreamWorker(QThread):
    """Background worker that continuously pulls frames from EmulatorController.streamScreenshot."""

    # Emits (frame_bytes, width, height, bytes_per_line)
    frame_ready = pyqtSignal(bytes, int, int, int)
    fps_updated = pyqtSignal(float)
    stream_stopped = pyqtSignal()
    stream_error = pyqtSignal(str)

    def __init__(self, connection: EmulatorConnection, target_width: int = 1080, target_height: int = 2400):
        super().__init__()
        self._connection = connection
        self._target_width = target_width
        self._target_height = target_height
        self._is_running = True

    def set_target_resolution(self, width: int, height: int):
        """Update requested stream resolution."""
        self._target_width = max(100, width)
        self._target_height = max(100, height)

    def stop(self):
        """Signal thread to stop."""
        self._is_running = False

    def run(self):
        logger.info("FrameStreamWorker started (target: %dx%d)", self._target_width, self._target_height)
        frame_count = 0
        last_fps_time = time.perf_counter()

        while self._is_running:
            try:
                stream = self._connection.get_frame_stream(width=self._target_width, height=self._target_height)
                if not stream:
                    time.sleep(0.5)
                    continue

                for frame in stream:
                    if not self._is_running:
                        break

                    img_bytes = frame.image
                    fmt = frame.format
                    w = fmt.width
                    h = fmt.height
                    bpl = w * 4  # RGBA8888

                    self.frame_ready.emit(img_bytes, w, h, bpl)

                    frame_count += 1
                    now = time.perf_counter()
                    dt = now - last_fps_time
                    if dt >= 1.0:
                        fps = frame_count / dt
                        self.fps_updated.emit(fps)
                        frame_count = 0
                        last_fps_time = now

            except Exception as e:
                if self._is_running:
                    logger.warning("Frame stream exception: %s. Reconnecting stream...", e)
                    time.sleep(1.0)
                else:
                    break

        logger.info("FrameStreamWorker exiting")
        self.stream_stopped.emit()
