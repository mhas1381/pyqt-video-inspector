from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QRect, Qt, QTimer
from PyQt6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pyqt_video_inspector.frame_view import FrameView
from pyqt_video_inspector.histogram_window import HistogramWindow
from pyqt_video_inspector.video_model import VideoModel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Video Inspector")
        self.resize(1100, 700)

        self._video = VideoModel()
        self._current_frame: np.ndarray | None = None
        self._current_index = 0
        self._histogram = HistogramWindow()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_play_tick)

        self._build_ui()
        self._set_controls_enabled(False)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        sidebar = QVBoxLayout()
        sidebar.setSpacing(12)

        self._open_btn = QPushButton("Open")
        self._open_btn.setStyleSheet(
            "QPushButton { background-color: #2d6cdf; color: white; "
            "padding: 8px 16px; font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #3b7aef; }"
        )
        self._open_btn.clicked.connect(self._on_open)
        sidebar.addWidget(self._open_btn)

        info_box = QGroupBox("Info")
        info_form = QFormLayout(info_box)
        self._resolution_label = QLabel("—")
        self._fps_label = QLabel("—")
        self._frame_count_label = QLabel("—")
        info_form.addRow("Resolution:", self._resolution_label)
        info_form.addRow("FPS:", self._fps_label)
        info_form.addRow("Frame Count:", self._frame_count_label)
        sidebar.addWidget(info_box)

        frame_box = QGroupBox("Frame")
        frame_layout = QVBoxLayout(frame_box)
        self._frame_spin = QSpinBox()
        self._frame_spin.setMinimum(0)
        self._frame_spin.valueChanged.connect(self._on_spin_changed)
        frame_layout.addWidget(self._frame_spin)

        self._frame_slider = QSlider(Qt.Orientation.Horizontal)
        self._frame_slider.setMinimum(0)
        self._frame_slider.valueChanged.connect(self._on_slider_changed)
        frame_layout.addWidget(self._frame_slider)
        sidebar.addWidget(frame_box)

        transport = QHBoxLayout()
        self._play_btn = QPushButton("Play")
        self._pause_btn = QPushButton("Pause")
        self._play_btn.clicked.connect(self._on_play)
        self._pause_btn.clicked.connect(self._on_pause)
        transport.addWidget(self._play_btn)
        transport.addWidget(self._pause_btn)
        sidebar.addLayout(transport)

        self._histogram_btn = QPushButton("Show Histogram")
        self._histogram_btn.clicked.connect(self._on_show_histogram)
        sidebar.addWidget(self._histogram_btn)

        sidebar.addStretch(1)
        root.addLayout(sidebar, 0)

        self._frame_view = FrameView()
        self._frame_view.roi_changed.connect(self._on_roi_changed)
        root.addWidget(self._frame_view, 1)

    def _set_controls_enabled(self, enabled: bool) -> None:
        self._frame_spin.setEnabled(enabled)
        self._frame_slider.setEnabled(enabled)
        self._play_btn.setEnabled(enabled)
        self._pause_btn.setEnabled(enabled)
        self._histogram_btn.setEnabled(enabled)

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video",
            "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv *.webm);;All Files (*)",
        )
        if not path:
            return

        self._on_pause()
        error = self._video.open(path)
        if error:
            QMessageBox.critical(self, "Open Failed", error)
            return

        meta = self._video.meta
        assert meta is not None

        self._resolution_label.setText(f"{meta.width}×{meta.height}")
        self._fps_label.setText(f"{meta.fps:.2f}")
        self._frame_count_label.setText(str(meta.frame_count))

        max_index = meta.frame_count - 1
        self._frame_spin.blockSignals(True)
        self._frame_slider.blockSignals(True)
        self._frame_spin.setMaximum(max_index)
        self._frame_slider.setMaximum(max_index)
        self._frame_spin.setValue(0)
        self._frame_slider.setValue(0)
        self._frame_spin.blockSignals(False)
        self._frame_slider.blockSignals(False)

        self._frame_view.clear_roi()
        self._set_controls_enabled(True)
        self._show_frame(0, keep_roi=False)

        interval = max(1, int(round(1000.0 / meta.fps)))
        self._timer.setInterval(interval)

    def _show_frame(self, index: int, *, keep_roi: bool = True) -> None:
        frame = self._video.get_frame(index)
        self._current_index = index
        self._current_frame = frame
        self._frame_view.set_frame(frame, keep_roi=keep_roi)
        self._refresh_histogram_if_visible()

    def _sync_controls(self, index: int) -> None:
        self._frame_spin.blockSignals(True)
        self._frame_slider.blockSignals(True)
        self._frame_spin.setValue(index)
        self._frame_slider.setValue(index)
        self._frame_spin.blockSignals(False)
        self._frame_slider.blockSignals(False)

    def _on_spin_changed(self, value: int) -> None:
        self._on_pause()
        self._frame_slider.blockSignals(True)
        self._frame_slider.setValue(value)
        self._frame_slider.blockSignals(False)
        self._show_frame(value)

    def _on_slider_changed(self, value: int) -> None:
        self._on_pause()
        self._frame_spin.blockSignals(True)
        self._frame_spin.setValue(value)
        self._frame_spin.blockSignals(False)
        self._show_frame(value)

    def _on_play(self) -> None:
        if not self._video.is_open:
            return
        if self._current_index >= self._video.frame_count - 1:
            self._sync_controls(0)
            self._show_frame(0)
        self._timer.start()

    def _on_pause(self) -> None:
        self._timer.stop()

    def _on_play_tick(self) -> None:
        if not self._video.is_open:
            self._on_pause()
            return
        next_index = self._current_index + 1
        if next_index >= self._video.frame_count:
            self._on_pause()
            return
        self._sync_controls(next_index)
        self._show_frame(next_index)

    def _on_show_histogram(self) -> None:
        if self._current_frame is None:
            QMessageBox.information(self, "Histogram", "Open a video first.")
            return
        self._histogram.update_from_frame(
            self._current_frame,
            self._frame_view.roi_in_image(),
        )
        self._histogram.show()
        self._histogram.raise_()
        self._histogram.activateWindow()

    def _on_roi_changed(self, _roi: QRect) -> None:
        self._refresh_histogram_if_visible()

    def _refresh_histogram_if_visible(self) -> None:
        if self._histogram.isVisible():
            self._histogram.update_from_frame(
                self._current_frame,
                self._frame_view.roi_in_image(),
            )

    def closeEvent(self, event) -> None:
        self._on_pause()
        self._histogram.close()
        self._video.close()
        super().closeEvent(event)
