"""AVD discovery using SDK tooling and standard AVD directory inspection."""

import os
import subprocess
from pathlib import Path
from typing import List, Optional

from aed.avd.model import AvdInfo
from aed.logging_util import get_logger
from aed.platform.sdk import get_emulator_binary

logger = get_logger("avd.discovery")


def get_avd_home_dir() -> Path:
    """Determine the directory storing AVD definitions."""
    if "ANDROID_AVD_HOME" in os.environ:
        p = Path(os.environ["ANDROID_AVD_HOME"]).expanduser().resolve()
        if p.exists():
            return p
    return Path.home() / ".android" / "avd"


def parse_ini_file(path: Path) -> dict:
    """Parse key=value ini configuration file."""
    res = {}
    if not path.exists():
        return res
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fp:
            for line in fp:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith(";"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    res[k.strip()] = v.strip()
    except Exception as e:
        logger.warning("Error reading %s: %s", path, e)
    return res


def list_avds(emulator_bin: Optional[Path] = None) -> List[AvdInfo]:
    """Discover all available Android Virtual Devices."""
    avd_list: List[AvdInfo] = []
    avd_names = set()

    # 1. Ask emulator -list-avds if binary is available
    if not emulator_bin:
        emulator_bin = get_emulator_binary()

    if emulator_bin and emulator_bin.exists():
        try:
            cmd = [str(emulator_bin), "-list-avds"]
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=5, text=True)
            for line in output.splitlines():
                name = line.strip()
                if name:
                    avd_names.add(name)
        except Exception as e:
            logger.warning("Failed to invoke emulator -list-avds: %s", e)

    # 2. Inspect AVD directory
    avd_home = get_avd_home_dir()
    if avd_home.exists():
        for item in avd_home.glob("*.ini"):
            name = item.stem
            avd_names.add(name)

    # Build AVD info objects
    for name in sorted(avd_names):
        avd_ini = avd_home / f"{name}.ini"
        avd_dir = avd_home / f"{name}.avd"
        props = {}
        if avd_ini.exists():
            props.update(parse_ini_file(avd_ini))
            custom_path = props.get("path")
            if custom_path:
                avd_dir = Path(custom_path)

        config_ini = avd_dir / "config.ini"
        if config_ini.exists():
            props.update(parse_ini_file(config_ini))

        info = AvdInfo(
            name=name,
            id=name,
            path=avd_dir if avd_dir.exists() else None,
            target=props.get("target"),
            abi=props.get("abi.type"),
            skin=props.get("skin.name"),
            device_name=props.get("hw.device.name"),
            properties=props,
        )
        avd_list.append(info)

    logger.info("Discovered %d AVD(s): %s", len(avd_list), [a.name for a in avd_list])
    return avd_list
