from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QWidget


class HistogramWindow(QWidget):
    """Separate window that draws RGB histograms for a frame region."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Histogram")
        self.resize(520, 360)
        self.setMinimumSize(320, 240)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self._hist_r: np.ndarray | None = None
        self._hist_g: np.ndarray | None = None
        self._hist_b: np.ndarray | None = None

    def update_from_frame(self, rgb: np.ndarray | None, roi: QRect) -> None:
        if rgb is None:
            self._hist_r = self._hist_g = self._hist_b = None
            self.update()
            return

        height, width, _ = rgb.shape
        if roi.isNull() or not roi.isValid():
            region = rgb
        else:
            x1 = max(0, min(roi.x(), width - 1))
            y1 = max(0, min(roi.y(), height - 1))
            x2 = max(x1 + 1, min(roi.x() + roi.width(), width))
            y2 = max(y1 + 1, min(roi.y() + roi.height(), height))
            region = rgb[y1:y2, x1:x2]

        if region.size == 0:
            self._hist_r = self._hist_g = self._hist_b = None
            self.update()
            return

        bins = np.arange(257)
        self._hist_r, _ = np.histogram(region[:, :, 0], bins=bins)
        self._hist_g, _ = np.histogram(region[:, :, 1], bins=bins)
        self._hist_b, _ = np.histogram(region[:, :, 2], bins=bins)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(30, 30, 30))

        margin_left = 40
        margin_right = 20
        margin_top = 30
        margin_bottom = 40
        plot = QRect(
            margin_left,
            margin_top,
            max(1, self.width() - margin_left - margin_right),
            max(1, self.height() - margin_top - margin_bottom),
        )

        painter.setPen(QPen(QColor(180, 180, 180)))
        painter.drawRect(plot)
        painter.drawText(10, 20, "RGB Histogram")

        if self._hist_r is None or self._hist_g is None or self._hist_b is None:
            painter.drawText(plot, Qt.AlignmentFlag.AlignCenter, "No data")
            return

        peak = max(
            float(self._hist_r.max()),
            float(self._hist_g.max()),
            float(self._hist_b.max()),
            1.0,
        )

        self._draw_channel(painter, plot, self._hist_r, QColor(220, 60, 60), peak)
        self._draw_channel(painter, plot, self._hist_g, QColor(60, 200, 80), peak)
        self._draw_channel(painter, plot, self._hist_b, QColor(60, 120, 240), peak)

        painter.setPen(QColor(180, 180, 180))
        painter.drawText(plot.left(), self.height() - 15, "0")
        painter.drawText(plot.right() - 24, self.height() - 15, "255")
        painter.drawText(8, plot.bottom(), "0")
        painter.drawText(8, plot.top() + 12, f"{int(peak)}")

    def _draw_channel(
        self,
        painter: QPainter,
        plot: QRect,
        hist: np.ndarray,
        color: QColor,
        peak: float,
    ) -> None:
        pen = QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)

        n = len(hist)
        if n < 2:
            return

        points = []
        for i, value in enumerate(hist):
            x = plot.left() + int(i * (plot.width() - 1) / (n - 1))
            y = plot.bottom() - int((float(value) / peak) * (plot.height() - 1))
            points.append((x, y))

        for i in range(1, len(points)):
            x0, y0 = points[i - 1]
            x1, y1 = points[i]
            painter.drawLine(x0, y0, x1, y1)
