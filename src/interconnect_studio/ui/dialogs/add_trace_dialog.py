"""Add Trace selection dialog."""

from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QWidget,
)

from interconnect_studio.algorithms.network import SParameterFormat
from interconnect_studio.algorithms.network.traces import format_display_name


@dataclass(frozen=True, slots=True)
class TraceSelection:
    """User-selected S-parameter and display format."""

    response_port: int
    source_port: int
    data_format: SParameterFormat


class AddTraceDialog(QDialog):
    """Select an S-parameter and display format for a two-port network."""

    _PARAMETERS = (
        ("S11", 0, 0),
        ("S21", 1, 0),
        ("S12", 0, 1),
        ("S22", 1, 1),
    )

    _COMMON_FORMATS = (
        SParameterFormat.LOG_MAG,
        SParameterFormat.LINEAR_MAG,
        SParameterFormat.PHASE,
        SParameterFormat.UNWRAPPED_PHASE,
        SParameterFormat.GROUP_DELAY,
        SParameterFormat.REAL,
        SParameterFormat.IMAGINARY,
    )

    _REFLECTION_ONLY_FORMATS = (
        SParameterFormat.SWR,
        SParameterFormat.IMPEDANCE_REAL,
        SParameterFormat.IMPEDANCE_IMAGINARY,
        SParameterFormat.IMPEDANCE_MAGNITUDE,
        SParameterFormat.IMPEDANCE_IMAGINARY_MAGNITUDE,
        SParameterFormat.IMPEDANCE_ANGLE,
        SParameterFormat.QUALITY_FACTOR,
        SParameterFormat.DISSIPATION_FACTOR,
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Trace")

        self.parameter_combo = QComboBox(self)
        for name, response_port, source_port in self._PARAMETERS:
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
        formats: tuple[SParameterFormat, ...] = self._COMMON_FORMATS
        if response_port == source_port:
            formats = (*formats, *self._REFLECTION_ONLY_FORMATS)

        for data_format in formats:
            self.format_combo.addItem(format_display_name(data_format), data_format.value)
