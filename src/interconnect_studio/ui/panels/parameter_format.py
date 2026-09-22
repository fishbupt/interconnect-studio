"""Parameter / format panel.

Takes over what a property panel would otherwise do: it summarises the
current data file and lists its traces. Choosing parameters and formats,
and the data integrity check, land here in a later step.
"""

from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QListWidget,
    QVBoxLayout,
    QWidget,
)

PLACEHOLDER = "-"


class ParameterFormatPanel(QWidget):
    """Summarises the current data file and its traces."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.file_value = QLabel(PLACEHOLDER)
        self.ports_value = QLabel(PLACEHOLDER)
        self.points_value = QLabel(PLACEHOLDER)
        self.z0_value = QLabel(PLACEHOLDER)

        summary = QGroupBox("Data File", self)
        form = QFormLayout(summary)
        form.addRow("File", self.file_value)
        form.addRow("Ports", self.ports_value)
        form.addRow("Points", self.points_value)
        form.addRow("Z0", self.z0_value)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.trace_list = QListWidget(self)

        traces = QGroupBox("Traces", self)
        trace_layout = QVBoxLayout(traces)
        trace_layout.setContentsMargins(6, 6, 6, 6)
        trace_layout.addWidget(self.trace_list)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(summary)
        layout.addWidget(traces)

    def set_summary(self, file_name: str, n_ports: int, n_points: int, z0: complex) -> None:
        """Show the current data file's key properties."""

        self.file_value.setText(file_name)
        self.ports_value.setText(str(n_ports))
        self.points_value.setText(str(n_points))
        self.z0_value.setText(f"{z0.real:g} Ω")

    def set_traces(self, names: tuple[str, ...]) -> None:
        """Replace the listed trace names."""

        self.trace_list.clear()
        self.trace_list.addItems(list(names))

    def clear(self) -> None:
        """Reset to the empty state."""

        for label in (self.file_value, self.ports_value, self.points_value, self.z0_value):
            label.setText(PLACEHOLDER)
        self.trace_list.clear()
