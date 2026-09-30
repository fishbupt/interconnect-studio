"""Modal progress for file work on the shared TaskRunner."""

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QProgressBar, QVBoxLayout, QWidget

from interconnect_studio.core import DataFormatError
from interconnect_studio.ui.task_runner import TaskRunner


def run_file_operation(
    title: str,
    work: Callable[[], object],
    runner: TaskRunner | None,
    parent: QWidget | None = None,
) -> object:
    """Use modal background work in the application, direct work in headless callers."""

    if runner is None:
        return work()
    dialog = FileOperationDialog(title, work, runner, parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        raise DataFormatError(dialog.error or "File operation did not complete.")
    return dialog.result_value


class FileOperationDialog(QDialog):
    """Keep the workspace stable until an atomic file operation finishes.

    Writes cannot be cancelled half-way through: closing/escape is disabled
    while work is running. Failure stays visible and leaves the workspace intact.
    """

    def __init__(
        self,
        title: str,
        work: Callable[[], object],
        runner: TaskRunner,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setMinimumWidth(400)
        self.result_value: object = None
        self.error = ""
        self._running = True
        self.label = QLabel(f"{title}…", self)
        self.label.setWordWrap(True)
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 0)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=self)
        self.buttons.setEnabled(False)
        self.buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        layout.addWidget(self.buttons)
        self._handle = runner.submit(work, self._finished, self._failed)

    def reject(self) -> None:
        """Allow closing only after the operation has reported."""

        if not self._running:
            super().reject()

    def _finished(self, value: object) -> None:
        self._running = False
        self.result_value = value
        self.accept()

    def _failed(self, message: str) -> None:
        self._running = False
        self.error = message
        self.label.setText(f"操作失败：{message}")
        self.progress.hide()
        self.buttons.setEnabled(True)
