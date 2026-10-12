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

from frame_view import FrameView
from histogram_window import HistogramWindow
from video_model import VideoModel


class MainWindow(QMainWindow):
    """The application's main window: builds the UI and coordinates the parts.

    This class does not read pixels or draw anything itself. It owns the
    VideoModel, the FrameView and the HistogramWindow, and decides when each
    of them should update.
    """

    def __init__(self) -> None:
        """Create the pieces, wire up the timer, and build the widgets."""
        super().__init__()
        self.setWindowTitle("Video Inspector")
        self.resize(1100, 700)

        # The three collaborating parts.
        self._video = VideoModel()
        self._current_frame: np.ndarray | None = None  # frame on screen right now
        self._current_index = 0  # its frame number
        self._histogram = HistogramWindow(self)
        # Parented to this window so it is not orphaned, but flagged as a
        # separate top-level window so it gets its own title bar and task
        # bar entry instead of being embedded in the layout.
        self._histogram.setWindowFlags(Qt.WindowType.Window)

        # A repeating timer is what drives playback. Qt calls _on_play_tick
        # once per interval; the interval is set from the video's fps.
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_play_tick)

        self._build_ui()
        self._set_controls_enabled(False)  # nothing to control yet

    def _build_ui(self) -> None:
        """Construct every widget and connect its signals to its handlers.

        Layout structure:
            root (horizontal)
             |- sidebar (vertical): Open, Info, Frame, Play/Pause, Histogram
             `- FrameView (takes all remaining space)
        """
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)  # children placed left to right

        sidebar = QVBoxLayout()  # children placed top to bottom
        sidebar.setSpacing(12)

        # --- Open button ---
        self._open_btn = QPushButton("Open")
        self._open_btn.setStyleSheet(
            "QPushButton { background-color: #2d6cdf; color: white; "
            "padding: 8px 16px; font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #3b7aef; }"
        )
        self._open_btn.clicked.connect(self._on_open)  # .connect = signal handler
        sidebar.addWidget(self._open_btn)

        # --- Info box: read-only labels filled in after a video is opened ---
        info_box = QGroupBox("Info")
        info_form = QFormLayout(info_box)  # label : value rows
        self._resolution_label = QLabel("—")
        self._fps_label = QLabel("—")
        self._frame_count_label = QLabel("—")
        info_form.addRow("Resolution:", self._resolution_label)
        info_form.addRow("FPS:", self._fps_label)
        info_form.addRow("Frame Count:", self._frame_count_label)
        sidebar.addWidget(info_box)

        # --- Frame box: numeric entry + slider, kept in sync with each other ---
        frame_box = QGroupBox("Frame")
        frame_layout = QVBoxLayout(frame_box)
        self._frame_spin = QSpinBox()  # type a frame number directly
        self._frame_spin.setMinimum(0)
        self._frame_spin.valueChanged.connect(self._on_spin_changed)
        frame_layout.addWidget(self._frame_spin)

        self._frame_slider = QSlider(Qt.Orientation.Horizontal)
        self._frame_slider.setMinimum(0)
        self._frame_slider.valueChanged.connect(self._on_slider_changed)
        frame_layout.addWidget(self._frame_slider)
        sidebar.addWidget(frame_box)

        # --- Transport buttons ---
        transport = QHBoxLayout()
        self._play_btn = QPushButton("Play")
        self._pause_btn = QPushButton("Pause")
        self._play_btn.clicked.connect(self._on_play)
        self._pause_btn.clicked.connect(self._on_pause)
        transport.addWidget(self._play_btn)
        transport.addWidget(self._pause_btn)
        sidebar.addLayout(transport)

        # --- Histogram button ---
        self._histogram_btn = QPushButton("Show Histogram")
        self._histogram_btn.clicked.connect(self._on_show_histogram)
        sidebar.addWidget(self._histogram_btn)

        sidebar.addStretch(1)  # pushes the widgets above to the top
        root.addLayout(sidebar, 0)  # 0 = sidebar keeps its natural width

        # --- Frame view: takes all leftover space (stretch factor 1) ---
        self._frame_view = FrameView()
        self._frame_view.roi_changed.connect(self._on_roi_changed)
        root.addWidget(self._frame_view, 1)

    def _set_controls_enabled(self, enabled: bool) -> None:
        """Enable or grey out every control that needs an open video."""
        self._frame_spin.setEnabled(enabled)
        self._frame_slider.setEnabled(enabled)
        self._play_btn.setEnabled(enabled)
        self._pause_btn.setEnabled(enabled)
        self._histogram_btn.setEnabled(enabled)

    def _on_open(self) -> None:
        """Handle the Open button: pick a file, load it, and set up the UI.

        Note the early `if not path: return` - that is what happens when the
        user presses Cancel in the file dialog.
        """
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video",
            "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv *.webm);;All Files (*)",
        )
        if not path:
            return

        self._on_pause()  # stop playback of any previous video
        error = self._video.open(path)
        if error:
            # A failed open leaves no video loaded, so the UI must go back to
            # its empty state instead of showing the previous video's frame.
            self._reset_to_empty_state()
            QMessageBox.critical(self, "Open Failed", error)
            return

        meta = self._video.meta
        assert meta is not None  # open() succeeded, so meta is always set

        # Fill in the Info labels.
        self._resolution_label.setText(f"{meta.width}×{meta.height}")
        self._fps_label.setText(f"{meta.fps:.2f}")
        self._frame_count_label.setText(str(meta.frame_count))

        # Set the slider/spin range to the real frame count. Signals are
        # blocked while the values are set so the handlers do not fire and
        # try to decode frames before the range is correct.
        max_index = meta.frame_count - 1
        self._frame_spin.blockSignals(True)
        self._frame_slider.blockSignals(True)
        self._frame_spin.setMaximum(max_index)
        self._frame_slider.setMaximum(max_index)
        self._frame_spin.setValue(0)
        self._frame_slider.setValue(0)
        self._frame_spin.blockSignals(False)
        self._frame_slider.blockSignals(False)

        self._frame_view.clear_roi()  # a new video starts with no selection
        self._set_controls_enabled(True)
        self._show_frame(0, keep_roi=False)

        # Playback speed comes from the video: at 25 fps the timer must fire
        # every 1000/25 = 40 ms.
        fps = meta.fps if meta.fps > 0.0 else 25.0
        interval = max(1, int(round(1000.0 / fps)))
        self._timer.setInterval(interval)

    def _reset_to_empty_state(self) -> None:
        """Return the window to its pre-video state.

        Called when opening fails, so the UI never shows a stale frame or
        leaves controls enabled with nothing behind them.
        """
        self._current_frame = None
        self._current_index = 0
        self._resolution_label.setText("—")
        self._fps_label.setText("—")
        self._frame_count_label.setText("—")
        # Signals blocked for the same reason as in _on_open.
        self._frame_spin.blockSignals(True)
        self._frame_slider.blockSignals(True)
        self._frame_spin.setRange(0, 0)
        self._frame_slider.setRange(0, 0)
        self._frame_spin.setValue(0)
        self._frame_slider.setValue(0)
        self._frame_spin.blockSignals(False)
        self._frame_slider.blockSignals(False)
        self._frame_view.set_frame(None)  # clears the view to the placeholder
        self._set_controls_enabled(False)
        self._refresh_histogram_if_visible()

    def _show_frame(self, index: int, *, keep_roi: bool = True) -> None:
        """Load frame `index`, display it, and update the histogram.

        This is the single place where a frame is fetched, so every caller
        (slider, spinbox, playback timer) behaves identically.
        """
        frame = self._video.get_frame(index)
        self._current_index = index
        self._current_frame = frame
        self._frame_view.set_frame(frame, keep_roi=keep_roi)
        self._refresh_histogram_if_visible()

    def _sync_controls(self, index: int) -> None:
        """Move the slider and spinbox together without triggering handlers.

        Used during playback, where the change comes from the timer rather
        than from the user, so seeking must not happen recursively.
        """
        self._frame_spin.blockSignals(True)
        self._frame_slider.blockSignals(True)
        self._frame_spin.setValue(index)
        self._frame_slider.setValue(index)
        self._frame_spin.blockSignals(False)
        self._frame_slider.blockSignals(False)

    def _on_spin_changed(self, value: int) -> None:
        """Handle the frame-number box: pause, mirror to the slider, seek."""
        self._on_pause()  # manual seeking stops playback
        self._frame_slider.blockSignals(True)
        self._frame_slider.setValue(value)  # mirror without re-entering
        self._frame_slider.blockSignals(False)
        self._show_frame(value)

    def _on_slider_changed(self, value: int) -> None:
        """Handle the slider: pause, mirror to the spinbox, seek."""
        self._on_pause()
        self._frame_spin.blockSignals(True)
        self._frame_spin.setValue(value)
        self._frame_spin.blockSignals(False)
        self._show_frame(value)

    def _on_play(self) -> None:
        """Handle the Play button.

        If already at the last frame, restart from the beginning so Play
        always does something visible.
        """
        if not self._video.is_open:
            return
        if self._current_index >= self._video.frame_count - 1:
            self._sync_controls(0)
            self._show_frame(0)
        self._timer.start()  # begin firing _on_play_tick

    def _on_pause(self) -> None:
        """Stop the playback timer."""
        self._timer.stop()

    def _on_play_tick(self) -> None:
        """Advance one frame. Called by the timer once per frame interval."""
        if not self._video.is_open:
            self._on_pause()
            return
        next_index = self._current_index + 1
        if next_index >= self._video.frame_count:
            self._on_pause()  # reached the end, stop automatically
            return
        self._sync_controls(next_index)
        self._show_frame(next_index)

    def _on_show_histogram(self) -> None:
        """Handle the Show Histogram button: compute and open the window."""
        if self._current_frame is None:
            QMessageBox.information(self, "Histogram", "Open a video first.")
            return
        self._histogram.update_from_frame(
            self._current_frame,
            self._frame_view.roi_in_image(),
        )
        self._histogram.show()
        self._histogram.raise_()  # bring it to the front
        self._histogram.activateWindow()  # focus it

    def _on_roi_changed(self, _roi: QRect) -> None:
        """Handle the FrameView's roi_changed signal.

        The leading underscore marks the argument as unused: this handler
        does not need the rectangle itself because it re-reads the ROI from
        the frame view.
        """
        self._refresh_histogram_if_visible()

    def _refresh_histogram_if_visible(self) -> None:
        """Recompute the histogram, but only while its window is open.

        Skipping the work when hidden avoids recomputing it on every single
        frame during playback for a window nobody is looking at.
        """
        if self._histogram.isVisible():
            self._histogram.update_from_frame(
                self._current_frame,
                self._frame_view.roi_in_image(),
            )

    def closeEvent(self, event) -> None:
        """Clean up when the window is closed.

        Qt calls this instead of closing immediately. Releasing the video
        handle here is what stops the file from staying locked.
        """
        self._on_pause()
        self._histogram.close()
        self._video.close()
        super().closeEvent(event)  # let QMainWindow finish its own cleanup
