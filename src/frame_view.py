"""Displays a video frame and lets the user drag a rectangular ROI.

ROI means "Region Of Interest" - the rectangle the user selects to focus the
histogram on.

Coordinate systems used here (the part that confuses everyone):
  * image coordinates - pixels of the original video frame, e.g. (0,0)-(639,479)
  * widget coordinates - pixels on screen, where the frame is scaled down and
    centred inside the label
The `_widget_to_image` / `_image_to_widget` helpers convert between them.
"""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QMouseEvent, QPainter, QPen, QPixmap, QResizeEvent
from PyQt6.QtWidgets import QLabel, QSizePolicy


class FrameView(QLabel):
    """Displays a video frame and lets the user drag a rectangular ROI."""

    # A signal is how Qt widgets talk to each other. Anything that calls
    # .connect() on it gets notified whenever the ROI changes.
    roi_changed = pyqtSignal(QRect)

    def __init__(self, parent=None) -> None:
        """Build an empty frame view showing a placeholder message."""
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(400, 300)
        self.setStyleSheet("background-color: #1e1e1e; color: #aaaaaa;")
        self.setText("Open a video to begin")
        self.setMouseTracking(True)  # receive move events even without a button held

        self._source: QPixmap | None = None  # the frame at full resolution
        self._image_rect = QRect()  # where the scaled image sits in widget coords
        self._roi_image = QRect()  # ROI in original image coordinates
        self._drag_start: QPoint | None = None  # where the mouse went down
        self._dragging = False

    def set_frame(self, rgb: np.ndarray | None, *, keep_roi: bool = False) -> None:
        """Display a new frame.

        Passing None clears the view back to the placeholder text.
        `keep_roi` decides whether the existing selection survives: keep it
        while scrubbing through frames, drop it when a new video is opened.
        """
        if rgb is None:
            self._source = None
            self._roi_image = QRect()
            self.clear()
            self.setText("Open a video to begin")
            return

        height, width, channels = rgb.shape
        bytes_per_line = channels * width  # 3 bytes per pixel, tightly packed

        # QImage cannot outlive the numpy buffer, so .copy() makes an
        # independent copy of the pixel data before wrapping it.
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
            # Clip the ROI so it stays valid if the new frame is smaller.
            self._roi_image = self._roi_image.intersected(QRect(0, 0, width, height))

        self._update_display()

    def set_roi(self, roi: QRect) -> None:
        """Set the ROI from image coordinates, clamped to the frame bounds."""
        if self._source is None or roi.isNull() or not roi.isValid():
            self._roi_image = QRect()
        else:
            bounds = QRect(0, 0, self._source.width(), self._source.height())
            self._roi_image = roi.intersected(bounds)
        self._update_display()
        self.roi_changed.emit(QRect(self._roi_image))  # tell the main window

    def clear_roi(self) -> None:
        """Remove the selection (also notifies listeners)."""
        self.set_roi(QRect())

    def roi_in_image(self) -> QRect:
        """Return a copy of the current ROI in image coordinates."""
        return QRect(self._roi_image)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Redraw on resize, because the scaled image position changes."""
        super().resizeEvent(event)
        self._update_display()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Start a new selection. Only left button, and only on the image."""
        if event.button() != Qt.MouseButton.LeftButton or self._source is None:
            return
        if not self._image_rect.contains(event.position().toPoint()):
            return  # clicked the empty margin around the frame
        self._dragging = True
        self._drag_start = event.position().toPoint()
        self._roi_image = QRect()  # hide the old rectangle while dragging
        self._update_display()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """While dragging, update the ROI live so the user sees it grow."""
        if not self._dragging or self._drag_start is None or self._source is None:
            return
        current = event.position().toPoint()
        # normalized() handles drags that go up/left, giving a positive size.
        widget_rect = QRect(self._drag_start, current).normalized()
        widget_rect = widget_rect.intersected(self._image_rect)
        self._roi_image = self._widget_to_image(widget_rect)
        self._update_display()
        self.roi_changed.emit(QRect(self._roi_image))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Finish the selection; drop it if it was just an accidental click."""
        if event.button() != Qt.MouseButton.LeftButton or not self._dragging:
            return
        self._dragging = False
        self._drag_start = None
        if self._roi_image.width() < 2 or self._roi_image.height() < 2:
            self._roi_image = QRect()  # too small to be meaningful
        self._update_display()
        self.roi_changed.emit(QRect(self._roi_image))

    def _update_display(self) -> None:
        """Repaint: scale the frame to fit, then draw the ROI on top.

        Instead of letting QLabel scale the pixmap itself, a full-size
        pixmap is composed here so the ROI rectangle can be drawn over it.
        """
        if self._source is None:
            return

        scaled = self._source.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,  # never distort the aspect ratio
            Qt.TransformationMode.SmoothTransformation,
        )
        # Centre the scaled image in the widget.
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
        """Convert a screen rectangle to original-image coordinates.

        Scaling factors are source_size / displayed_size, so a 160px wide
        frame shown at 800px wide scales widget coordinates by 160/800.
        """
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
        """Convert original-image coordinates to screen coordinates."""
        if self._source is None or self._image_rect.isEmpty():
            return QRect()

        sx = self._image_rect.width() / self._source.width()
        sy = self._image_rect.height() / self._source.height()
        x = self._image_rect.x() + int(image_rect.x() * sx)
        y = self._image_rect.y() + int(image_rect.y() * sy)
        w = max(1, int(image_rect.width() * sx))
        h = max(1, int(image_rect.height() * sy))
        return QRect(x, y, w, h)