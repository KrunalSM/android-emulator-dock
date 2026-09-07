"""Android SDK and tooling discovery without assuming environment variables."""

import os
import shutil
from pathlib import Path
from typing import Optional, List, Tuple
from aed.logging_util import get_logger

logger = get_logger("platform.sdk")

STANDARD_LINUX_SDK_LOCATIONS = [
    Path.home() / "Android" / "Sdk",
    Path.home() / ".android-sdk",
    Path("/opt/android-sdk"),
    Path("/usr/lib/android-sdk"),
    Path("/mnt/extra/Software/LinuxSDK"),
]

def find_android_sdk(custom_path: Optional[str] = None) -> Optional[Path]:
    """Find Android SDK root directory checking custom path, env, PATH, and standard Linux locations."""
    if custom_path:
        p = Path(custom_path).expanduser().resolve()
        if p.exists() and (p / "emulator" / "emulator").exists():
            logger.info("Found Android SDK at user-configured path: %s", p)
            return p

    # 1. Environment variables
    for env_var in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        val = os.environ.get(env_var)
        if val:
            p = Path(val).expanduser().resolve()
            if p.exists() and (p / "emulator" / "emulator").exists():
                logger.info("Found Android SDK via %s: %s", env_var, p)
                return p

    # 2. Lookup via emulator in PATH
    emu_in_path = shutil.which("emulator")
    if emu_in_path:
        p = Path(emu_in_path).resolve().parent.parent
        if (p / "emulator" / "emulator").exists():
            logger.info("Found Android SDK via emulator in PATH: %s", p)
            return p

    # 3. Standard Linux locations
    for loc in STANDARD_LINUX_SDK_LOCATIONS:
        if loc.exists() and (loc / "emulator" / "emulator").exists():
            logger.info("Found Android SDK at standard location: %s", loc)
            return loc

    logger.warning("Android SDK could not be automatically located")
    return None

def get_emulator_binary(sdk_path: Optional[Path] = None) -> Optional[Path]:
    """Get path to official emulator executable."""
    if sdk_path and (sdk_path / "emulator" / "emulator").exists():
        return sdk_path / "emulator" / "emulator"

    emu_in_path = shutil.which("emulator")
    if emu_in_path:
        return Path(emu_in_path).resolve()

    detected_sdk = find_android_sdk()
    if detected_sdk and (detected_sdk / "emulator" / "emulator").exists():
        return detected_sdk / "emulator" / "emulator"

    return None

def get_adb_binary(sdk_path: Optional[Path] = None) -> Optional[Path]:
    """Get path to adb executable."""
    if sdk_path and (sdk_path / "platform-tools" / "adb").exists():
        return sdk_path / "platform-tools" / "adb"

    adb_in_path = shutil.which("adb")
    if adb_in_path:
        return Path(adb_in_path).resolve()

    detected_sdk = find_android_sdk()
    if detected_sdk and (detected_sdk / "platform-tools" / "adb").exists():
        return detected_sdk / "platform-tools" / "adb"

    return None
