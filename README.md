# Video Inspector

Desktop app for opening a video, browsing frames, selecting a rectangular ROI, and viewing an RGB histogram of the selected region.

Built with **PyQt6**, **OpenCV**, and **NumPy**.

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)

Dependencies are CPU-only (`numpy`, `opencv-python`, `PyQt6`). No NVIDIA/CUDA drivers or GPU packages are needed.

## Setup

```bash
uv sync
```

## Run

```bash
uv run pyqt-video-inspector
```

## Features

- Open common video formats (mp4, avi, mkv, mov, …)
- Show resolution, FPS, and frame count
- Seek with a slider and numeric frame input
- Play / Pause with `QTimer`
- Drag a rectangular ROI on the frame
- RGB histogram in a separate window (updates live while open)
