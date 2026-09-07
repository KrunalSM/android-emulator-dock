"""Dedicated service for capturing emulator screenshots via official gRPC API."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from aed.connection.client import EmulatorConnection
from aed.logging_util import get_logger

logger = get_logger("connection.screenshot")


class ScreenshotService:
    """Handles capturing emulator screenshots without capturing any surrounding Dock UI."""

    def __init__(self, connection: EmulatorConnection, avd_name: str):
        self._connection = connection
        self._avd_name = avd_name

    def capture_screenshot(self, output_dir: Optional[Path] = None) -> Optional[Path]:
        """Capture screenshot from official emulator API and save to file."""
        if not self._connection or not self._connection.is_connected:
            logger.warning("[%s] Cannot capture screenshot: not connected", self._avd_name)
            return None

        img_data = self._connection.get_screenshot()
        if not img_data or not img_data.image:
            logger.error("[%s] Empty screenshot data received from emulator", self._avd_name)
            return None

        if not output_dir:
            output_dir = Path.home() / "Pictures" / "Screenshots"
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Screenshot_{self._avd_name}_{timestamp}.png"
        file_path = output_dir / filename

        try:
            # Construct QImage from received RGBA bytes and save as PNG
            from PyQt6.QtGui import QImage

            fmt = img_data.format
            w = fmt.width
            h = fmt.height
            bpl = w * 4
            qimg = QImage(img_data.image, w, h, bpl, QImage.Format.Format_RGBA8888)
            if qimg.save(str(file_path), "PNG"):
                logger.info("[%s] Saved emulator screenshot to %s", self._avd_name, file_path)
                return file_path
            else:
                logger.error("[%s] Failed to write image to %s", self._avd_name, file_path)
                return None
        except Exception as e:
            logger.error("[%s] Error saving screenshot: %s", self._avd_name, e)
            return None
