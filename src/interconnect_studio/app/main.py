"""Executable entry point for Interconnect Studio."""

import sys

from PyQt6.QtWidgets import QApplication

from interconnect_studio.ui import MainWindow
from interconnect_studio.ui.theme import DEFAULT_THEME, apply_theme


def main() -> int:
    """Run the Interconnect Studio desktop application."""

    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)
        # Names the per-user data folder saved templates are kept in.
        app.setApplicationName("Interconnect Studio")

    if isinstance(app, QApplication):
        apply_theme(app, DEFAULT_THEME)

    window = MainWindow()
    window.show()

    if owns_app:
        return app.exec()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
