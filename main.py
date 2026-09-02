"""Application Entry Point for DPW 2D Powder-Dispensing Gantry Controller."""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from dpw_gantry.ui.main_window import MainWindow


def main():
    # High-DPI support
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("DPW Gantry Controller")
    app.setOrganizationName("Powder Dispensing Systems")
    app.setApplicationVersion("1.0.0")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
