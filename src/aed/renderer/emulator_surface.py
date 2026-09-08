"""High-performance GPU-backed rendering widget for emulator display.

Uses QOpenGLWidget for hardware accelerated composition, letterboxing,
proper aspect ratio preservation, and coordinate transformation for input.
"""

from typing import Optional, Tuple

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal, QEvent
from PyQt6.QtGui import QColor, QImage, QPainter, QEventPoint
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from aed.logging_util import get_logger

logger = get_logger("renderer.surface")


class EmulatorSurface(QOpenGLWidget):
    """OpenGL-backed viewport for rendering emulator frames and handling user input."""

    # Emits normalized device coordinates (x, y) in range [0, device_w], [0, device_h]
    touch_down = pyqtSignal(int, int)
    touch_move = pyqtSignal(int, int)
    touch_up = pyqtSignal(int, int)
    touches_changed = pyqtSignal(list)
    wheel_scrolled = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self._current_image: Optional[QImage] = None
        self._device_width = 1080
        self._device_height = 2400
        self._is_mouse_down = False
        self._target_rect = QRectF()

    def update_frame(self, frame_bytes: bytes, width: int, height: int, bytes_per_line: int):
        """Receive new frame bytes from background worker."""
        self._device_width = width
        self._device_height = height
        img = QImage(frame_bytes, width, height, bytes_per_line, QImage.Format.Format_RGBA8888)
        self._current_image = img.copy()
        self.update()

    def clear(self):
        """Clear current frame to prevent stale or frozen frames upon emulator stop."""
        self._current_image = None
        self._is_mouse_down = False
        self.update()

    def paintGL(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Background letterboxing
        painter.fillRect(self.rect(), QColor(18, 18, 20))

        if not self._current_image or self._current_image.isNull():
            # Draw empty/stopped placeholder
            painter.setPen(QColor(120, 120, 130))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Emulator Stopped")
            painter.end()
            return

        # Calculate aspect-ratio preserving target rectangle
        widget_w = self.width()
        widget_h = self.height()
        aspect = self._device_width / max(1, self._device_height)
        widget_aspect = widget_w / max(1, widget_h)

        if widget_aspect > aspect:
            # Letterbox left & right
            h = widget_h
            w = h * aspect
            x = (widget_w - w) / 2.0
            y = 0.0
        else:
            # Letterbox top & bottom
            w = widget_w
            h = w / aspect
            x = 0.0
            y = (widget_h - h) / 2.0

        self._target_rect = QRectF(x, y, w, h)
        painter.drawImage(self._target_rect, self._current_image)
        painter.end()

    def _widget_to_device_coords(self, pos: QPointF) -> Optional[Tuple[int, int]]:
        """Map widget local coordinates to original emulator screen pixel coordinates."""
        if not self._target_rect.isValid() or self._target_rect.width() <= 0 or self._target_rect.height() <= 0:
            return None

        if not self._target_rect.contains(pos):
            x_rel = min(max(pos.x() - self._target_rect.left(), 0.0), self._target_rect.width())
            y_rel = min(max(pos.y() - self._target_rect.top(), 0.0), self._target_rect.height())
        else:
            x_rel = pos.x() - self._target_rect.left()
            y_rel = pos.y() - self._target_rect.top()

        u = x_rel / self._target_rect.width()
        v = y_rel / self._target_rect.height()

        dev_x = int(u * self._device_width)
        dev_y = int(v * self._device_height)
        return (dev_x, dev_y)

    def _emit_mouse_touches(self, x: int, y: int, pressure: int):
        touches = [{"x": x, "y": y, "pressure": pressure, "identifier": 0}]
        
        if getattr(self, '_is_simulating_multitouch', False):
            mirror_x = self._device_width - x
            mirror_y = self._device_height - y
            touches.append({"x": mirror_x, "y": mirror_y, "pressure": pressure, "identifier": 1})
            
        self.touches_changed.emit(touches)

    def mousePressEvent(self, event):
        self.setFocus()
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_mouse_down = True
            self._is_simulating_multitouch = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
            coords = self._widget_to_device_coords(event.position())
            if coords:
                self._emit_mouse_touches(coords[0], coords[1], 1)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_mouse_down:
            coords = self._widget_to_device_coords(event.position())
            if coords:
                self._emit_mouse_touches(coords[0], coords[1], 1)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_mouse_down = False
            coords = self._widget_to_device_coords(event.position())
            if coords:
                self._emit_mouse_touches(coords[0], coords[1], 0)
            self._is_simulating_multitouch = False
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta()
        # angleDelta is in eighths of a degree, usually 120 per scroll step
        dx = delta.x() // 120
        dy = delta.y() // 120
        if dx != 0 or dy != 0:
            self.wheel_scrolled.emit(dx, dy)
        super().wheelEvent(event)

    def event(self, event):
        if event.type() in (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate, QEvent.Type.TouchEnd):
            touches_data = []
            for pt in event.points():
                coords = self._widget_to_device_coords(pt.position())
                if coords:
                    pressure = 0 if pt.state() == QEventPoint.State.Released else 1
                    touches_data.append({
                        "x": coords[0],
                        "y": coords[1],
                        "pressure": pressure,
                        "identifier": pt.id()
                    })
            if touches_data:
                self.touches_changed.emit(touches_data)
            event.accept()
            return True
        return super().event(event)
