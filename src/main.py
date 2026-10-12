"""Application entry point.

This is the file that actually starts the program. When you run
`uv run pyqt-video-inspector`, Python imports this module and calls
`main()` (see the `[project.scripts]` section of pyproject.toml).
"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from assets import app_icon
from main_window import MainWindow


def main() -> None:
    """Create the Qt application, show the main window, and run the event loop.

    Step 1 - QApplication: every Qt GUI program must create exactly one of
        these before touching any widget. It owns shared resources such as
        fonts, the clipboard and the display connection.

    Step 5 - app.exec(): starts Qt's event loop. This call BLOCKS here and
        keeps dispatching events (clicks, timers, key presses, repaints)
        until the last window is closed. Nothing after it ever runs.
    """
    app = QApplication(sys.argv)  # 1. the GUI application itself
    app.setApplicationName("Video Inspector")
    app.setWindowIcon(app_icon())  # 2. icon for the taskbar and title bar
    window = MainWindow()  # 3. build the main window (widgets are created here)
    window.show()  # 4. make it visible
    sys.exit(app.exec())  # 5. run forever until the user quits