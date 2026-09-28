"""Data Integrity Check, reached from the Parameter / Format panel.

Shows what ``algorithms.network.quality`` found, and nothing more: the
checks are read-only, so this dialog never offers to fix anything. Putting
a "correct this" button here would invite exactly the silent rewriting of
measured data that ``ALGORITHM_GUIDE.md`` §12.5 keeps as a separate,
explicit algorithm.

The checks are an SVD per frequency, which is seconds of work on a large
file, so they run on the shared ``TaskRunner`` rather than on the GUI
thread.
"""

from collections.abc import Callable
from typing import Final

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from interconnect_studio.algorithms.network import (
    MEASUREMENT_TOLERANCE,
    QualityResult,
    check_network,
)
from interconnect_studio.core import Network
from interconnect_studio.ui.task_runner import TaskRunner

_COLUMNS: Final[tuple[str, ...]] = (
    "Check",
    "Result",
    "Worst value",
    "At",
    "Points outside",
)

_TOLERANCE_NOTE: Final[str] = (
    f"Tolerance {MEASUREMENT_TOLERANCE:g}. Measured data never satisfies these "
    "exactly; the numbers matter more than the verdict. This threshold is "
    "provisional and needs setting from real instrument exports."
)


def check_summary(results: tuple[QualityResult, ...]) -> str:
    """One line for the status bar, naming what failed rather than a count."""

    failed = [result.name for result in results if not result.passed]
    if not failed:
        return "Data integrity: all checks passed."
    return f"Data integrity: {', '.join(failed)} outside tolerance."


def run_checks(
    network: Network,
    tolerance: float = MEASUREMENT_TOLERANCE,
) -> Callable[[], object]:
    """The work to hand to a ``TaskRunner``; touches no widget."""

    return lambda: check_network(network, tolerance=tolerance)


class DataIntegrityDialog(QDialog):
    """Passivity and reciprocity for the current file."""

    def __init__(
        self,
        network: Network,
        runner: TaskRunner,
        parent: QWidget | None = None,
        tolerance: float = MEASUREMENT_TOLERANCE,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Data Integrity Check")

        self.status_label = QLabel("Checking ...", self)
        self.table = QTableWidget(0, len(_COLUMNS), self)
        self.table.setHorizontalHeaderLabels(list(_COLUMNS))
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        rows_header = self.table.verticalHeader()
        if rows_header is not None:
            rows_header.setVisible(False)
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        note = QLabel(_TOLERANCE_NOTE, self)
        note.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=self)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table)
        layout.addWidget(note)
        layout.addWidget(buttons)

        self.results: tuple[QualityResult, ...] = ()
        self._handle = runner.submit(
            run_checks(network, tolerance), self._on_results, self._on_error
        )

    def reject(self) -> None:
        """Closing disowns the running check instead of waiting for it."""

        self._handle.cancel()
        super().reject()

    def _on_results(self, results: object) -> None:
        assert isinstance(results, tuple)
        self.results = results
        self.status_label.setText(check_summary(self.results))
        self.table.setRowCount(len(self.results))
        for row, result in enumerate(self.results):
            self._fill_row(row, result)

    def _on_error(self, message: str) -> None:
        self.status_label.setText(f"Check failed: {message}")

    def _fill_row(self, row: int, result: QualityResult) -> None:
        # Nine significant figures: a passivity excess of 3e-4 is the whole
        # point of looking, and "1.0003" would round it away.
        values = (
            result.name.capitalize(),
            "Pass" if result.passed else "Outside tolerance",
            f"{result.worst_metric:.9g}",
            f"{result.worst_frequency_hz / 1e9:.6g} GHz",
            f"{result.violations.size} of {result.metric.size}",
        )
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            if column >= 2:
                item.setTextAlignment(
                    int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                )
            self.table.setItem(row, column, item)
