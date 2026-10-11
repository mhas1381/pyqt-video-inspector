from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from pyqt_video_inspector.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Video Inspector")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
