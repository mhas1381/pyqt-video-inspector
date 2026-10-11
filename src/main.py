from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from assets import app_icon
from main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Video Inspector")
    app.setWindowIcon(app_icon())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
