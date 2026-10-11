from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class VideoMeta:
    width: int
    height: int
    fps: float
    frame_count: int


class VideoModel:
    """OpenCV-backed video reader with frame seek and RGB conversion."""

    def __init__(self) -> None:
        self._cap: cv2.VideoCapture | None = None
        self._meta: VideoMeta | None = None
        self._path: Path | None = None

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    @property
    def path(self) -> Path | None:
        return self._path

    @property
    def meta(self) -> VideoMeta | None:
        return self._meta

    @property
    def width(self) -> int:
        return self._meta.width if self._meta else 0

    @property
    def height(self) -> int:
        return self._meta.height if self._meta else 0

    @property
    def fps(self) -> float:
        return self._meta.fps if self._meta else 0.0

    @property
    def frame_count(self) -> int:
        return self._meta.frame_count if self._meta else 0

    def open(self, path: str | Path) -> str | None:
        """Open a video file. Returns an error message on failure, else None."""
        path = Path(path)
        self.close()

        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            cap.release()
            return f"Could not open video file:\n{path}"

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS)) or 25.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if width <= 0 or height <= 0 or frame_count <= 0:
            cap.release()
            return f"Invalid or unsupported video file:\n{path}"

        self._cap = cap
        self._path = path
        self._meta = VideoMeta(
            width=width,
            height=height,
            fps=fps,
            frame_count=frame_count,
        )
        return None

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._meta = None
        self._path = None

    def get_frame(self, index: int) -> np.ndarray | None:
        """Return an RGB uint8 frame at the given index, or None on failure."""
        if not self.is_open or self._meta is None:
            return None

        index = max(0, min(index, self._meta.frame_count - 1))
        assert self._cap is not None
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, bgr = self._cap.read()
        if not ok or bgr is None:
            return None
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
