"""Executable entry point for Interconnect Studio."""

import sys

from PyQt6.QtWidgets import QApplication

from interconnect_studio.ui import MainWindow


def main() -> int:
    """Run the Interconnect Studio desktop application."""

    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    if owns_app:
        return app.exec()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
