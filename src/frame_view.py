from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QMouseEvent, QPainter, QPen, QPixmap, QResizeEvent
from PyQt6.QtWidgets import QLabel, QSizePolicy


class FrameView(QLabel):
    """Displays a video frame and lets the user drag a rectangular ROI."""

    roi_changed = pyqtSignal(QRect)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(400, 300)
        self.setStyleSheet("background-color: #1e1e1e; color: #aaaaaa;")
        self.setText("Open a video to begin")
        self.setMouseTracking(True)

        self._source: QPixmap | None = None
        self._image_rect = QRect()  # where the scaled image sits in widget coords
        self._roi_image = QRect()  # ROI in original image coordinates
        self._drag_start: QPoint | None = None
        self._dragging = False

    def set_frame(self, rgb: np.ndarray | None, *, keep_roi: bool = False) -> None:
        if rgb is None:
            self._source = None
            self._roi_image = QRect()
            self.clear()
            self.setText("Open a video to begin")
            return

        height, width, channels = rgb.shape
        bytes_per_line = channels * width
        image = QImage(
            rgb.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        ).copy()
        self._source = QPixmap.fromImage(image)
        if not keep_roi:
            self._roi_image = QRect()
        elif not self._roi_image.isNull():
            self._roi_image = self._roi_image.intersected(
                QRect(0, 0, width, height)
            )
        self._update_display()

    def set_roi(self, roi: QRect) -> None:
        if self._source is None or roi.isNull() or not roi.isValid():
            self._roi_image = QRect()
        else:
            bounds = QRect(0, 0, self._source.width(), self._source.height())
            self._roi_image = roi.intersected(bounds)
        self._update_display()
        self.roi_changed.emit(QRect(self._roi_image))

    def clear_roi(self) -> None:
        self.set_roi(QRect())

    def roi_in_image(self) -> QRect:
        return QRect(self._roi_image)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._update_display()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._source is None:
            return
        if not self._image_rect.contains(event.position().toPoint()):
            return
        self._dragging = True
        self._drag_start = event.position().toPoint()
        self._roi_image = QRect()
        self._update_display()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._dragging or self._drag_start is None or self._source is None:
            return
        current = event.position().toPoint()
        widget_rect = QRect(self._drag_start, current).normalized()
        widget_rect = widget_rect.intersected(self._image_rect)
        self._roi_image = self._widget_to_image(widget_rect)
        self._update_display()
        self.roi_changed.emit(QRect(self._roi_image))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or not self._dragging:
            return
        self._dragging = False
        self._drag_start = None
        if self._roi_image.width() < 2 or self._roi_image.height() < 2:
            self._roi_image = QRect()
        self._update_display()
        self.roi_changed.emit(QRect(self._roi_image))

    def _update_display(self) -> None:
        if self._source is None:
            return

        scaled = self._source.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        self._image_rect = QRect(x, y, scaled.width(), scaled.height())

        canvas = QPixmap(self.size())
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.drawPixmap(self._image_rect.topLeft(), scaled)

        if not self._roi_image.isNull() and self._roi_image.isValid():
            widget_roi = self._image_to_widget(self._roi_image)
            pen = QPen(Qt.GlobalColor.yellow)
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(widget_roi)

        painter.end()
        self.setPixmap(canvas)

    def _widget_to_image(self, widget_rect: QRect) -> QRect:
        if self._source is None or self._image_rect.isEmpty():
            return QRect()

        sx = self._source.width() / self._image_rect.width()
        sy = self._source.height() / self._image_rect.height()
        x = int((widget_rect.x() - self._image_rect.x()) * sx)
        y = int((widget_rect.y() - self._image_rect.y()) * sy)
        w = max(1, int(widget_rect.width() * sx))
        h = max(1, int(widget_rect.height() * sy))
        rect = QRect(x, y, w, h).normalized()
        return rect.intersected(QRect(0, 0, self._source.width(), self._source.height()))

    def _image_to_widget(self, image_rect: QRect) -> QRect:
        if self._source is None or self._image_rect.isEmpty():
            return QRect()

        sx = self._image_rect.width() / self._source.width()
        sy = self._image_rect.height() / self._source.height()
        x = self._image_rect.x() + int(image_rect.x() * sx)
        y = self._image_rect.y() + int(image_rect.y() * sy)
        w = max(1, int(image_rect.width() * sx))
        h = max(1, int(image_rect.height() * sy))
        return QRect(x, y, w, h)
