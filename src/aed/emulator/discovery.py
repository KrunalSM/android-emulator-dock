"""Discovery for running emulator instances via $XDG_RUNTIME_DIR/avd/running."""

import os
from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass
from aed.logging_util import get_logger

logger = get_logger("emulator.discovery")

@dataclass
class RunningEmulatorInfo:
    pid: int
    grpc_port: int
    grpc_token: str
    avd_id: Optional[str] = None
    avd_name: Optional[str] = None
    port_serial: Optional[int] = None
    port_adb: Optional[int] = None
    emulator_version: Optional[str] = None
    ini_path: Optional[Path] = None

def get_running_avd_dir() -> Path:
    """Get the running AVD directory."""
    xdg_runtime = os.environ.get("XDG_RUNTIME_DIR")
    if xdg_runtime:
        p = Path(xdg_runtime) / "avd" / "running"
        return p
    # Fallback
    uid = os.getuid()
    return Path(f"/run/user/{uid}/avd/running")

def parse_discovery_ini(ini_path: Path) -> Optional[RunningEmulatorInfo]:
    """Parse a pid_<PID>.ini file safely."""
    if not ini_path.exists():
        return None

    data: Dict[str, str] = {}
    try:
        with open(ini_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    data[k.strip()] = v.strip()
    except Exception as e:
        logger.warning("Failed to read discovery ini %s: %s", ini_path, e)
        return None

    try:
        pid_str = ini_path.stem.replace("pid_", "")
        pid = int(pid_str)
        grpc_port = int(data.get("grpc.port", 0))
        grpc_token = data.get("grpc.token", "")

        if grpc_port <= 0:
            return None

        serial = int(data["port.serial"]) if "port.serial" in data else None
        adb = int(data["port.adb"]) if "port.adb" in data else None

        info = RunningEmulatorInfo(
            pid=pid,
            grpc_port=grpc_port,
            grpc_token=grpc_token,
            avd_id=data.get("avd.id"),
            avd_name=data.get("avd.name"),
            port_serial=serial,
            port_adb=adb,
            emulator_version=data.get("emulator.version"),
            ini_path=ini_path,
        )
        return info
    except Exception as e:
        logger.warning("Error parsing discovery fields from %s: %s", ini_path, e)
        return None

def find_running_emulator_by_pid(pid: int) -> Optional[RunningEmulatorInfo]:
    """Find discovery info for a specific PID."""
    running_dir = get_running_avd_dir()
    ini_path = running_dir / f"pid_{pid}.ini"
    if ini_path.exists():
        return parse_discovery_ini(ini_path)
    return None

def find_all_running_emulators() -> Dict[int, RunningEmulatorInfo]:
    """Discover all currently running emulators."""
    running_dir = get_running_avd_dir()
    results = {}
    if not running_dir.exists():
        return results

    for ini_file in running_dir.glob("pid_*.ini"):
        info = parse_discovery_ini(ini_file)
        if info:
            results[info.pid] = info
    return results
