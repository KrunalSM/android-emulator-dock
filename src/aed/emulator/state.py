"""Lifecycle state machine definitions for Android Emulator instances."""

from enum import Enum, auto

class EmulatorState(Enum):
    STOPPED = auto()
    LAUNCHING = auto()
    WAITING_FOR_DISCOVERY = auto()
    CONNECTING = auto()
    BOOTING = auto()
    RUNNING = auto()
    STOPPING = auto()
    FAILED = auto()
    DISCONNECTED = auto()

    def is_active(self) -> bool:
        return self in (
            EmulatorState.LAUNCHING,
            EmulatorState.WAITING_FOR_DISCOVERY,
            EmulatorState.CONNECTING,
            EmulatorState.BOOTING,
            EmulatorState.RUNNING,
        )

    def can_start(self) -> bool:
        return self in (
            EmulatorState.STOPPED,
            EmulatorState.FAILED,
            EmulatorState.DISCONNECTED,
        )

    def display_name(self) -> str:
        names = {
            EmulatorState.STOPPED: "Stopped",
            EmulatorState.LAUNCHING: "Launching...",
            EmulatorState.WAITING_FOR_DISCOVERY: "Waiting for gRPC...",
            EmulatorState.CONNECTING: "Connecting...",
            EmulatorState.BOOTING: "Booting...",
            EmulatorState.RUNNING: "Running",
            EmulatorState.STOPPING: "Stopping...",
            EmulatorState.FAILED: "Failed",
            EmulatorState.DISCONNECTED: "Disconnected",
        }
        return names.get(self, self.name)
