"""Add Trace selection dialog."""

from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QWidget,
)

from interconnect_studio.algorithms.network import SParameterFormat, cartesian_formats_for
from interconnect_studio.algorithms.network.traces import format_display_name


@dataclass(frozen=True, slots=True)
class TraceSelection:
    """User-selected S-parameter and display format."""

    response_port: int
    source_port: int
    data_format: SParameterFormat


def _parameters(n_ports: int) -> list[tuple[str, int, int]]:
    """S-parameters with zero-based (response, source), in listing order.

    Two ports keep the familiar S11, S21, S12, S22 order; other port counts
    are listed row by row.
    """

    if n_ports == 2:
        return [("S11", 0, 0), ("S21", 1, 0), ("S12", 0, 1), ("S22", 1, 1)]
    return [
        (f"S{row + 1},{col + 1}" if n_ports >= 10 else f"S{row + 1}{col + 1}", row, col)
        for row in range(n_ports)
        for col in range(n_ports)
    ]


class AddTraceDialog(QDialog):
    """Select an S-parameter and display format for an N-port network."""

    def __init__(self, parent: QWidget | None = None, n_ports: int = 2) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Trace")

        self.parameter_combo = QComboBox(self)
        for name, response_port, source_port in _parameters(n_ports):
            self.parameter_combo.addItem(name, (response_port, source_port))
        self.parameter_combo.currentIndexChanged.connect(self._refresh_formats)

        self.format_combo = QComboBox(self)
        self._refresh_formats()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QFormLayout(self)
        layout.addRow("S Parameter", self.parameter_combo)
        layout.addRow("Format", self.format_combo)
        layout.addRow(buttons)

    def selection(self) -> TraceSelection:
        """Return the current dialog selection."""

        response_port, source_port = self.parameter_combo.currentData()
        data_format = SParameterFormat(self.format_combo.currentData())
        return TraceSelection(
            response_port=response_port,
            source_port=source_port,
            data_format=data_format,
        )

    def _refresh_formats(self) -> None:
        self.format_combo.clear()
        response_port, source_port = self.parameter_combo.currentData()
        for data_format in cartesian_formats_for(response_port, source_port):
            self.format_combo.addItem(format_display_name(data_format), data_format.value)
