"""AVD data models and parser."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class AvdInfo:
    name: str
    id: str
    path: Optional[Path] = None
    target: Optional[str] = None
    abi: Optional[str] = None
    skin: Optional[str] = None
    device_name: Optional[str] = None
    properties: Dict[str, str] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return self.properties.get("avd.ini.displayname", self.name.replace("_", " "))
