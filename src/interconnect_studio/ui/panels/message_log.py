"""Collapsible message panel backing the status bar."""

from PyQt6.QtWidgets import QTextEdit, QVBoxLayout, QWidget


class MessageLogPanel(QWidget):
    """Accumulates status messages.

    PLTS has no permanent log pane, so this panel stays collapsed and is
    opened from the status bar when the user wants the history.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.view = QTextEdit(self)
        self.view.setReadOnly(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

    def append(self, message: str) -> None:
        """Append one message."""

        self.view.append(message)

    def text(self) -> str:
        """All messages as plain text."""

        return self.view.toPlainText()
