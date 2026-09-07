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

# Map human-friendly pane names to official proto PaneIndex
PANE_INDEX_MAP = {
    "LOCATION": uc.PaneEntry.LOCATION,
    "MULTIDISPLAY": uc.PaneEntry.MULTIDISPLAY,
    "CELLULAR": uc.PaneEntry.CELLULAR,
    "BATTERY": uc.PaneEntry.BATTERY,
    "CAMERA": uc.PaneEntry.CAMERA,
    "TELEPHONE": uc.PaneEntry.TELEPHONE,
    "DPAD": uc.PaneEntry.DPAD,
    "TV_REMOTE": uc.PaneEntry.TV_REMOTE,
    "ROTARY": uc.PaneEntry.ROTARY,
    "MICROPHONE": uc.PaneEntry.MICROPHONE,
    "FINGER": uc.PaneEntry.FINGER,
    "VIRT_SENSORS": uc.PaneEntry.VIRT_SENSORS,
    "SNAPSHOT": uc.PaneEntry.SNAPSHOT,
    "BUGREPORT": uc.PaneEntry.BUGREPORT,
    "RECORD": uc.PaneEntry.RECORD,
    "GOOGLE_PLAY": uc.PaneEntry.GOOGLE_PLAY,
    "SETTINGS": uc.PaneEntry.SETTINGS,
    "HELP": uc.PaneEntry.HELP,
    "CAR": uc.PaneEntry.CAR,
    "CAR_ROTARY": uc.PaneEntry.CAR_ROTARY,
    "SENSOR_REPLAY": uc.PaneEntry.SENSOR_REPLAY,
}

class EmulatorConnection:
    """Manages gRPC transport, frame streaming, input forwarding, device controls, and extended controls."""

    def __init__(self, host: str, port: int, token: str):
        self._host = host
        self._port = port
        self._token = token  # Never logged or printed
        self._channel: Optional[grpc.Channel] = None
        self._controller_stub: Optional[ec_grpc.EmulatorControllerStub] = None
        self._ui_stub: Optional[uc_grpc.UiControllerStub] = None
        self._is_connected = False
        self._current_rotation = 0  # 0: PORTRAIT, 1: LANDSCAPE, 2: REVERSE_PORTRAIT, 3: REVERSE_LANDSCAPE

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

    def get_screenshot(self, width: int = 0, height: int = 0):
        """Capture a single full-resolution screenshot."""
        if not self._is_connected or not self._controller_stub:
            return None
        try:
            fmt = ec.ImageFormat(
                format=ec.ImageFormat.RGBA8888,
                width=width,
                height=height
            )
            return self._controller_stub.getScreenshot(fmt, metadata=self._metadata())
        except Exception as e:
            logger.error("Failed to get screenshot: %s", e)
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

    # Standard Android Navigation & Hardware Controls
    def send_back(self):
        """Send Android Back navigation event."""
        self.send_key(key_code="GoBack")

    def send_home(self):
        """Send Android Home navigation event."""
        self.send_key(key_code="GoHome")

    def send_recents(self):
        """Send Android Overview/Recents navigation event."""
        self.send_key(key_code="AppSwitch")

    def send_power(self):
        """Send Android Power button event."""
        self.send_key(key_code="Power")

    def send_volume_up(self):
        """Send Android Volume Up hardware key event."""
        self.send_key(key_code="AudioVolumeUp")

    def send_volume_down(self):
        """Send Android Volume Down hardware key event."""
        self.send_key(key_code="AudioVolumeDown")

    def rotate_device(self):
        """Rotate device orientation 90 degrees clockwise."""
        if not self._is_connected or not self._controller_stub:
            return
        try:
            self._current_rotation = (self._current_rotation + 1) % 4
            # PhysicalModelValue with ROTATION
            # ROTATION expects z-axis angle (0, 90, 180, 270)
            angles = [0.0, 90.0, 180.0, 270.0]
            val = angles[self._current_rotation]
            param = ec.ParameterValue(data=[0.0, 0.0, val])
            req = ec.PhysicalModelValue(
                target=ec.PhysicalModelValue.PhysicalType.ROTATION,
                value=param
            )
            self._controller_stub.setPhysicalModel(req, metadata=self._metadata())
            logger.info("Rotated device to %d deg", int(val))
        except Exception as e:
            logger.warning("Error rotating device: %s", e)

    def set_fold_posture(self, posture_name: str = "POSTURE_OPENED"):
        """Set foldable device posture (e.g. POSTURE_OPENED, POSTURE_CLOSED, POSTURE_HALF_OPENED)."""
        if not self._is_connected or not self._controller_stub:
            return
        try:
            val = getattr(ec.Posture.PostureValue, posture_name, ec.Posture.PostureValue.POSTURE_OPENED)
            req = ec.Posture(value=val)
            self._controller_stub.setPosture(req, metadata=self._metadata())
            logger.info("Set fold posture to %s", posture_name)
        except Exception as e:
            logger.warning("Error setting posture: %s", e)

    def send_fingerprint(self, touch_id: int = 1):
        """Trigger virtual fingerprint touch event."""
        if not self._is_connected or not self._controller_stub:
            return
        try:
            req = ec.Fingerprint(isTouching=True, touchId=touch_id)
            self._controller_stub.sendFingerprint(req, metadata=self._metadata())
            logger.info("Dispatched virtual fingerprint touch (touchId=%d)", touch_id)
        except Exception as e:
            logger.warning("Error sending fingerprint: %s", e)

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
            pane_enum = PANE_INDEX_MAP.get(pane.upper(), uc.PaneEntry.LOCATION)
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
