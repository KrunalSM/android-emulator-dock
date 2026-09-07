"""Clean abstraction over official Android Emulator gRPC interfaces.

UI code interacts with this client and NEVER directly imports or calls raw gRPC stubs.
"""

import sys
import queue
from pathlib import Path
from typing import Optional, Iterator, Tuple, Callable
import grpc

# Add generated proto dir to sys.path
proto_dir = Path(__file__).resolve().parent.parent.parent.parent / "proto"
if str(proto_dir) not in sys.path:
    sys.path.insert(0, str(proto_dir))

import emulator_controller_pb2 as ec
import emulator_controller_pb2_grpc as ec_grpc
import ui_controller_service_pb2 as uc
import ui_controller_service_pb2_grpc as uc_grpc
from google.protobuf import empty_pb2

from aed.logging_util import get_logger

logger = get_logger("connection.client")

class EmulatorConnection:
    """Manages gRPC transport, frame streaming, input forwarding, and extended controls."""

    def __init__(self, host: str, port: int, token: str):
        self._host = host
        self._port = port
        self._token = token  # Never logged or printed
        self._channel: Optional[grpc.Channel] = None
        self._controller_stub: Optional[ec_grpc.EmulatorControllerStub] = None
        self._ui_stub: Optional[uc_grpc.UiControllerStub] = None
        self._is_connected = False
        self._wheel_queue: Optional[queue.Queue] = None

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def connect(self, timeout: float = 5.0) -> bool:
        """Establish authenticated gRPC channel."""
        try:
            target = f"{self._host}:{self._port}"
            logger.info("Connecting to gRPC endpoint %s", target)
            self._channel = grpc.insecure_channel(
                target,
                options=[
                    ('grpc.max_receive_message_length', 64 * 1024 * 1024),
                    ('grpc.max_send_message_length', 64 * 1024 * 1024),
                ]
            )
            grpc.channel_ready_future(self._channel).result(timeout=timeout)
            self._controller_stub = ec_grpc.EmulatorControllerStub(self._channel)
            self._ui_stub = uc_grpc.UiControllerStub(self._channel)
            self._is_connected = True
            logger.info("Successfully connected to emulator gRPC service")
            return True
        except Exception as e:
            logger.error("Failed to connect to gRPC service on port %d: %s", self._port, e)
            self.disconnect()
            return False

    def disconnect(self):
        """Tear down gRPC channel."""
        self._is_connected = False
        if self._channel:
            try:
                self._channel.close()
            except Exception:
                pass
            self._channel = None
        self._controller_stub = None
        self._ui_stub = None
        logger.info("gRPC channel closed")

    def _metadata(self) -> list:
        if self._token:
            return [("authorization", f"Bearer {self._token}")]
        return []

    def get_frame_stream(self, width: int = 1080, height: int = 2400) -> Optional[Iterator]:
        """Request streaming screenshot frames in RGBA8888."""
        if not self._is_connected or not self._controller_stub:
            return None
        try:
            fmt = ec.ImageFormat(
                format=ec.ImageFormat.RGBA8888,
                width=width,
                height=height
            )
            return self._controller_stub.streamScreenshot(fmt, metadata=self._metadata())
        except Exception as e:
            logger.error("Failed to start frame stream: %s", e)
            return None

    def send_touch(self, x: int, y: int, pressure: int = 1, identifier: int = 0):
        """Send touch point event (pressure: 1 for down/move, 0 for up)."""
        if not self._is_connected or not self._controller_stub:
            return
        try:
            t = ec.Touch(x=x, y=y, pressure=pressure, identifier=identifier)
            evt = ec.TouchEvent(touches=[t])
            self._controller_stub.sendTouch(evt, metadata=self._metadata())
        except Exception as e:
            logger.warning("Error sending touch event: %s", e)

    def send_key(self, text: Optional[str] = None, key_code: Optional[str] = None, event_type: str = "keypress"):
        """Send keyboard event."""
        if not self._is_connected or not self._controller_stub:
            return
        try:
            et = ec.KeyboardEvent.KeyEventType.keypress
            if event_type == "keydown":
                et = ec.KeyboardEvent.KeyEventType.keydown
            elif event_type == "keyup":
                et = ec.KeyboardEvent.KeyEventType.keyup

            evt = ec.KeyboardEvent(eventType=et)
            if text:
                evt.text = text
            if key_code:
                evt.key = key_code

            self._controller_stub.sendKey(evt, metadata=self._metadata())
        except Exception as e:
            logger.warning("Error sending key event: %s", e)

    def send_mouse(self, x: int, y: int, buttons: int = 0):
        """Send mouse coordinates and buttons."""
        if not self._is_connected or not self._controller_stub:
            return
        try:
            me = ec.MouseEvent(x=x, y=y, buttons=buttons)
            self._controller_stub.sendMouse(me, metadata=self._metadata())
        except Exception as e:
            logger.warning("Error sending mouse event: %s", e)

    def inject_wheel(self, dx: int = 0, dy: int = 0):
        """Send mouse wheel scroll event via injectWheel streaming generator."""
        if not self._is_connected or not self._controller_stub:
            return
        try:
            we = ec.WheelEvent(dx=dx, dy=dy)
            def wheel_gen():
                yield we
            self._controller_stub.injectWheel(wheel_gen(), metadata=self._metadata())
        except Exception as e:
            logger.warning("Error injecting wheel event: %s", e)

    def show_extended_controls(self, pane: str = "LOCATION") -> bool:
        """Open official emulator Extended Controls window."""
        if not self._is_connected or not self._ui_stub:
            return False
        try:
            pane_enum = uc.PaneEntry.LOCATION
            if pane.upper() == "BATTERY":
                pane_enum = uc.PaneEntry.BATTERY
            elif pane.upper() == "CELLULAR":
                pane_enum = uc.PaneEntry.CELLULAR
            elif pane.upper() == "CAMERA":
                pane_enum = uc.PaneEntry.CAMERA
            elif pane.upper() == "SETTINGS":
                pane_enum = uc.PaneEntry.SETTINGS
            elif pane.upper() == "SNAPSHOT":
                pane_enum = uc.PaneEntry.SNAPSHOT

            logger.info("Opening official Extended Controls (%s)", pane)
            req = uc.PaneEntry(index=pane_enum)
            self._ui_stub.showExtendedControls(req, metadata=self._metadata())
            return True
        except Exception as e:
            logger.error("Failed to show Extended Controls: %s", e)
            return False

    def close_extended_controls(self) -> bool:
        """Close official Extended Controls window."""
        if not self._is_connected or not self._ui_stub:
            return False
        try:
            self._ui_stub.closeExtendedControls(empty_pb2.Empty(), metadata=self._metadata())
            return True
        except Exception as e:
            logger.error("Failed to close Extended Controls: %s", e)
            return False
