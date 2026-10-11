from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import QRect, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPaintEvent, QPen
from PyQt6.QtWidgets import QWidget

BACKGROUND = QColor(45, 45, 45)
PLOT_BACKGROUND = QColor(24, 24, 24)
GRID_COLOR = QColor(64, 64, 64)
AXIS_COLOR = QColor(190, 190, 190)

CHANNELS: tuple[tuple[str, QColor], ...] = (
    ("Red", QColor(226, 32, 32)),
    ("Green", QColor(60, 200, 64)),
    ("Blue", QColor(32, 112, 232)),
)

X_TICKS = (0, 50, 100, 150, 200, 255)
Y_DIVISIONS = 4

MARGIN_LEFT = 46
MARGIN_RIGHT = 14
MARGIN_TOP = 46
MARGIN_BOTTOM = 30


class HistogramWindow(QWidget):
    """Separate window that draws RGB histograms for a frame region."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Histogram")
        self.resize(430, 350)
        self.setMinimumSize(320, 260)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self._histograms: tuple[np.ndarray, ...] | None = None

    def update_from_frame(self, rgb: np.ndarray | None, roi: QRect) -> None:
        if rgb is None:
            self._histograms = None
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
            self._histograms = None
            self.update()
            return

        bins = np.arange(257)
        self._histograms = tuple(
            np.histogram(region[:, :, index], bins=bins)[0] for index in range(3)
        )
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), BACKGROUND)

        self._draw_legend(painter)

        plot = self._plot_rect()
        painter.fillRect(plot, PLOT_BACKGROUND)

        if self._histograms is None:
            painter.setPen(AXIS_COLOR)
            painter.drawText(plot, Qt.AlignmentFlag.AlignCenter, "No data")
            return

        y_max = self._nice_peak(max(float(hist.max()) for hist in self._histograms))
        self._draw_grid(painter, plot)
        for (_, color), hist in zip(reversed(CHANNELS), reversed(self._histograms)):
            self._draw_channel(painter, plot, hist, color, y_max)
        self._draw_axis_labels(painter, plot, y_max)

    def _plot_rect(self) -> QRectF:
        width = max(1, self.width() - MARGIN_LEFT - MARGIN_RIGHT)
        height = max(1, self.height() - MARGIN_TOP - MARGIN_BOTTOM)
        return QRectF(MARGIN_LEFT, MARGIN_TOP, width, height)

    def _draw_legend(self, painter: QPainter) -> None:
        metrics = painter.fontMetrics()
        swatch = 12
        y = MARGIN_TOP - 26
        x = MARGIN_LEFT

        for name, color in CHANNELS:
            painter.fillRect(QRect(x, y, swatch, swatch), color)
            painter.setPen(AXIS_COLOR)
            text_rect = QRect(
                x + swatch + 6,
                y - 2,
                metrics.horizontalAdvance(name),
                swatch + 4,
            )
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                name,
            )
            x += swatch + 10 + metrics.horizontalAdvance(name) + 20

    def _draw_grid(self, painter: QPainter, plot: QRectF) -> None:
        pen = QPen(GRID_COLOR)
        pen.setWidth(1)
        painter.setPen(pen)

        for step in range(Y_DIVISIONS + 1):
            y = plot.bottom() - plot.height() * step / Y_DIVISIONS
            painter.drawLine(int(plot.left()), int(y), int(plot.right()), int(y))

        for value in X_TICKS:
            x = plot.left() + plot.width() * value / 255.0
            painter.drawLine(int(x), int(plot.top()), int(x), int(plot.bottom()))

    def _draw_axis_labels(self, painter: QPainter, plot: QRectF, y_max: float) -> None:
        painter.setPen(AXIS_COLOR)
        font = QFont(painter.font())
        font.setPointSize(max(7, font.pointSize() - 1))
        painter.setFont(font)
        metrics = painter.fontMetrics()

        for step in range(Y_DIVISIONS + 1):
            value = y_max * step / Y_DIVISIONS
            text = f"{value:.0f}"
            y = plot.bottom() - plot.height() * step / Y_DIVISIONS
            painter.drawText(
                QRectF(
                    plot.left() - metrics.horizontalAdvance(text) - 8,
                    y - metrics.height() / 2,
                    metrics.horizontalAdvance(text),
                    metrics.height(),
                ),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                text,
            )

        for value in X_TICKS:
            x = plot.left() + plot.width() * value / 255.0
            painter.drawText(
                QRectF(x - metrics.horizontalAdvance("255") / 2, plot.bottom() + 6,
                       metrics.horizontalAdvance("255"), metrics.height()),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                str(value),
            )

    def _draw_channel(
        self,
        painter: QPainter,
        plot: QRectF,
        hist: np.ndarray,
        color: QColor,
        y_max: float,
    ) -> None:
        count = len(hist)
        if count < 2 or y_max <= 0.0:
            return

        span = plot.width()
        height = plot.height()
        curve = QPainterPath()
        area = QPainterPath()
        area.moveTo(plot.left(), plot.bottom())

        for index, value in enumerate(hist):
            x = plot.left() + index * span / (count - 1)
            y = plot.bottom() - min(1.0, float(value) / y_max) * height
            if index == 0:
                curve.moveTo(x, y)
            else:
                curve.lineTo(x, y)
            area.lineTo(x, y)

        area.lineTo(plot.left() + span, plot.bottom())
        area.closeSubpath()

        fill = QColor(color)
        fill.setAlpha(120)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.fillPath(area, fill)

        pen = QPen(color)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawPath(curve)

    @staticmethod
    def _nice_peak(peak: float) -> float:
        """Round a raw peak up to a readable axis maximum."""
        if not math.isfinite(peak) or peak <= 0.0:
            return 1.0

        exponent = math.floor(math.log10(peak))
        scale = 10.0**exponent
        fraction = peak / scale
        for step in (1.0, 2.0, 2.5, 5.0, 10.0):
            if fraction <= step:
                return step * scale
        return 10.0 * scale