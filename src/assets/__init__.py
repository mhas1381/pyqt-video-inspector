from __future__ import annotations

from pathlib import Path

from PyQt6.QtGui import QIcon

ASSETS_DIR = Path(__file__).resolve().parent

_ICON_CANDIDATES = (
    ASSETS_DIR / "icon.ico",
    ASSETS_DIR / "icon.png",
)


def app_icon() -> QIcon:
    """Return the app icon, falling back gracefully if no asset is present."""
    for candidate in _ICON_CANDIDATES:
        if candidate.is_file():
            icon = QIcon(str(candidate))
            if not icon.isNull():
                return icon
    return QIcon()