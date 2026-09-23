"""Emulator launcher responsible for process creation, isolated environments, and command arguments."""

import os
import shutil
import sys
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment

from aed.logging_util import get_logger

logger = get_logger("emulator.launcher")


class GpuMode(str, Enum):
    """Supported GPU rendering modes for Android Emulator."""

    AUTOMATIC = "automatic"
    NVIDIA = "nvidia"

    @classmethod
    def from_string(cls, val: object) -> "GpuMode":
        """Convert a string, GpuMode, or setting value to a GpuMode enum."""
        if isinstance(val, cls):
            return val
        if val is not None:
            v = val.value if hasattr(val, "value") else str(val)
            normalized = v.strip().lower()
            if normalized in ("nvidia", "gpu_nvidia", "nvidia_gpu", "nvidia gpu", "gpumode.nvidia"):
                return cls.NVIDIA
        return cls.AUTOMATIC

    def display_name(self) -> str:
        """User-facing display name."""
        if self == GpuMode.NVIDIA:
            return "NVIDIA GPU"
        return "Automatic / Default"

    @property
    def description(self) -> str:
        """Description of the rendering mode."""
        if self == GpuMode.NVIDIA:
            return "Use NVIDIA PRIME offloading and host GPU rendering for emulator instances."
        return "Standard emulator graphics (default behavior)."


class EmulatorLauncher:
    """Central abstraction responsible for creating and configuring emulator processes.

    Ensures that process arguments and environments are constructed cleanly without
    mutating global state (e.g. os.environ), and isolates launch configuration from
    AVD discovery and UI code.
    """

    @staticmethod
    def build_arguments(avd_name: str, gpu_mode: GpuMode = GpuMode.AUTOMATIC) -> List[str]:
        """Build emulator CLI arguments.

        In Automatic mode, retains standard hosting flags without injecting -gpu host.
        In NVIDIA mode, appends '-gpu host'.
        """
        args = [
            "-avd",
            avd_name,
            "-qt-hide-window",
            "-grpc-use-token",
            "-idle-grpc-timeout",
            "300",
        ]
        if gpu_mode == GpuMode.NVIDIA:
            args.extend(["-gpu", "host"])
        return args

    @staticmethod
    def build_process_environment(gpu_mode: GpuMode = GpuMode.AUTOMATIC) -> QProcessEnvironment:
        """Construct an isolated QProcessEnvironment for the emulator subprocess.

        Crucially, this does NOT modify os.environ of the parent Dock process.
        """
        env = QProcessEnvironment.systemEnvironment()
        if gpu_mode == GpuMode.NVIDIA:
            env.insert("__NV_PRIME_RENDER_OFFLOAD", "1")
            env.insert("__GLX_VENDOR_LIBRARY_NAME", "nvidia")
        return env

    @staticmethod
    def check_nvidia_availability() -> Tuple[bool, Optional[str]]:
        """Lightweight non-invasive check to verify NVIDIA driver/environment availability."""
        if not sys.platform.startswith("linux"):
            return (
                False,
                "NVIDIA GPU PRIME offload rendering is configured for Linux systems. "
                "Please switch GPU Rendering to 'Automatic / Default'.",
            )

        # 1. Fast check for NVIDIA device nodes or procfs entry
        device_node_paths = [
            Path("/dev/nvidiactl"),
            Path("/dev/nvidia0"),
            Path("/proc/driver/nvidia"),
        ]
        has_device_nodes = any(p.exists() for p in device_node_paths)

        # 2. Check for nvidia-smi utility in PATH
        has_nvidia_smi = shutil.which("nvidia-smi") is not None

        if not has_device_nodes and not has_nvidia_smi:
            return (
                False,
                "NVIDIA GPU driver or device nodes (/dev/nvidiactl) not detected on this system. "
                "Verify the NVIDIA proprietary driver is installed and loaded, "
                "or switch GPU Rendering to 'Automatic / Default'.",
            )

        return (True, None)

    @classmethod
    def create_process(
        cls,
        gpu_mode: GpuMode = GpuMode.AUTOMATIC,
        parent: Optional[QObject] = None,
    ) -> QProcess:
        """Create a QProcess configured with an isolated per-process environment."""
        process = QProcess(parent)
        env = cls.build_process_environment(gpu_mode)
        process.setProcessEnvironment(env)
        return process
