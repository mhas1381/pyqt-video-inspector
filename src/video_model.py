"""Everything that touches the video file itself.

This is the ONLY module that imports OpenCV. Keeping the file-format
knowledge in one place means the rest of the program can stay ignorant of
cv2 and simply ask for "frame number 42".

A frame is returned as a numpy array of shape (height, width, 3) holding
uint8 values in 0-255, in RGB order.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


def _safe_float(value: float) -> float:
    """Coerce a container-reported value to a finite float, else 0.0.

    Broken or unusual video containers can report NaN or infinity for
    width/height/fps/frame_count. Calling int() or float() on those raises
    ValueError/OverflowError and takes the whole application down, so every
    number read from cv2 goes through here first.
    """
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return result if math.isfinite(result) else 0.0


def _safe_int(value: float) -> int:
    """Coerce a container-reported value to a non-negative int, else 0.

    Same protection as _safe_float, for values that must be whole numbers.
    """
    result = _safe_float(value)
    if result < 0.0:
        return 0
    return int(result)


@dataclass(frozen=True)
class VideoMeta:
    """Immutable description of an opened video.

    `frozen=True` means the fields cannot be changed after creation, so the
    metadata cannot drift out of sync with the actual file.
    """

    width: int  # frame width in pixels
    height: int  # frame height in pixels
    fps: float  # frames per second
    frame_count: int  # total number of frames


class VideoModel:
    """OpenCV-backed video reader with frame seek and RGB conversion."""

    def __init__(self) -> None:
        """Start with no video loaded.

        The leading underscore is a convention meaning "private, don't touch
        this from outside the class". Read access goes through the @property
        accessors below.
        """
        self._cap: cv2.VideoCapture | None = None  # OpenCV's file handle
        self._meta: VideoMeta | None = None  # None until open() succeeds
        self._path: Path | None = None

    @property
    def is_open(self) -> bool:
        """True when a video is loaded and still usable."""
        return self._cap is not None and self._cap.isOpened()

    @property
    def path(self) -> Path | None:
        """Path of the currently open file, or None."""
        return self._path

    @property
    def meta(self) -> VideoMeta | None:
        """Full metadata of the current video, or None."""
        return self._meta

    @property
    def width(self) -> int:
        """Frame width, or 0 when nothing is open.

        The `x if x else y` pattern keeps callers from having to check for
        None every time they just want a number.
        """
        return self._meta.width if self._meta else 0

    @property
    def height(self) -> int:
        """Frame height, or 0 when nothing is open."""
        return self._meta.height if self._meta else 0

    @property
    def fps(self) -> float:
        """Frames per second, or 0.0 when nothing is open."""
        return self._meta.fps if self._meta else 0.0

    @property
    def frame_count(self) -> int:
        """Total frame count, or 0 when nothing is open."""
        return self._meta.frame_count if self._meta else 0

    def open(self, path: str | Path) -> str | None:
        """Open a video file. Returns an error message on failure, else None.

        Returning an error string instead of raising keeps the UI code
        simple: the caller just checks `if error:` and shows a dialog.

        Note the local `cap` variable: the file handle is only stored on
        self once everything validated, so a failed open can never leave a
        half-initialised model behind.
        """
        path = Path(path)
        self.close()  # release any previously open file first

        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            cap.release()
            return f"Could not open video file:\n{path}"

        # Read container metadata, sanitising every value.
        width = _safe_int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = _safe_int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = _safe_float(cap.get(cv2.CAP_PROP_FPS))
        frame_count = _safe_int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Some containers report a nonsensical fps; fall back to a sane default.
        if not math.isfinite(fps) or fps <= 0.0:
            fps = 25.0

        # A video with no width, height or frames is unusable.
        if width <= 0 or height <= 0 or frame_count <= 0:
            cap.release()
            return f"Invalid or unsupported video file:\n{path}"

        # Everything checked out - commit the new state.
        self._cap = cap
        self._path = path
        self._meta = VideoMeta(
            width=width,
            height=height,
            fps=fps,
            frame_count=frame_count,
        )
        return None  # None means success

    def close(self) -> None:
        """Release the file handle and forget the current video.

        Always safe to call, even when nothing is open.
        """
        if self._cap is not None:
            self._cap.release()  # free the OS-level file handle
            self._cap = None
        self._meta = None
        self._path = None

    def get_frame(self, index: int) -> np.ndarray | None:
        """Return an RGB uint8 frame at the given index, or None on failure.

        Seeking by frame number is done by telling OpenCV where to jump to
        and then reading a single frame - the frames in between are not
        decoded.
        """
        if not self.is_open or self._meta is None or self._meta.frame_count <= 0:
            return None

        # Clamp so an out-of-range index can never raise or wrap around.
        index = max(0, min(index, self._meta.frame_count - 1))
        assert self._cap is not None  # tell the type checker, not the runtime

        self._cap.set(cv2.CAP_PROP_POS_FRAMES, index)  # seek
        ok, bgr = self._cap.read()  # ok=False if the read failed
        if not ok or bgr is None:
            return None

        # OpenCV hands back BGR (blue, green, red); the rest of the app and
        # Qt's colour format both expect RGB.
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)