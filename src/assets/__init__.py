"""Bundled non-code assets (the application icon).

This is a package rather than a plain folder so that setuptools installs it
alongside the rest of the project and the icon is still found after
installation, not just when running from the source tree.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtGui import QIcon

# Always resolve relative to this file, never to the current working
# directory - otherwise the icon breaks as soon as the app is started from
# somewhere else.
ASSETS_DIR = Path(__file__).resolve().parent

# Checked in order: the .ico first because it already contains every size,
# with the .png as a fallback if the ico is missing or unreadable.
_ICON_CANDIDATES = (
    ASSETS_DIR / "icon.ico",
    ASSETS_DIR / "icon.png",
)


def app_icon() -> QIcon:
    """Return the app icon, falling back gracefully if no asset is present.

    Returning an empty QIcon is a valid "no icon" answer, so a missing file
    degrades to a default icon instead of crashing at startup.
    """
    for candidate in _ICON_CANDIDATES:
        if candidate.is_file():
            icon = QIcon(str(candidate))
            if not icon.isNull():
                return icon
    return QIcon()