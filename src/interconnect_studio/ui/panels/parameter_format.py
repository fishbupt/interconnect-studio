"""Parameter / format panel.

Where traces are created, matching PLTS: pick an S-parameter, pick a display
format, then either add it to the current plot or open a new one. Also takes
over what a property panel would otherwise do, summarising the current data
file.
"""

from PyQt6.QtCore import pyqtBoundSignal, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from interconnect_studio.algorithms.network import SParameterFormat, cartesian_formats_for
from interconnect_studio.algorithms.network.traces import format_display_name

PLACEHOLDER = "-"


class ParameterFormatPanel(QWidget):
    """Select an S-parameter and format, and summarise the current file."""

    add_trace_requested = pyqtSignal(int, int, str)
    new_plot_requested = pyqtSignal(int, int, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._n_ports = 0
        self._parameter_buttons = QButtonGroup(self)
        self._parameter_buttons.setExclusive(True)
        self._parameter_buttons.idToggled.connect(self._on_parameter_toggled)

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

        self.parameter_box = QGroupBox("S Parameter", self)
        self._parameter_grid = QGridLayout(self.parameter_box)
        self._parameter_grid.setSpacing(2)

        self.format_combo = QComboBox(self)
        self.add_button = QPushButton("Add to Plot", self)
        self.new_plot_button = QPushButton("New Plot", self)
        self.add_button.clicked.connect(self._on_add_clicked)
        self.new_plot_button.clicked.connect(self._on_new_plot_clicked)

        format_box = QGroupBox("Format", self)
        format_layout = QVBoxLayout(format_box)
        format_layout.addWidget(self.format_combo)
        buttons = QHBoxLayout()
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.new_plot_button)
        format_layout.addLayout(buttons)

        self.trace_list = QListWidget(self)
        traces = QGroupBox("Traces", self)
        trace_layout = QVBoxLayout(traces)
        trace_layout.addWidget(self.trace_list)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(summary)
        layout.addWidget(self.parameter_box)
        layout.addWidget(format_box)
        layout.addWidget(traces)

        self.set_port_count(0)

    @property
    def n_ports(self) -> int:
        """Port count the parameter grid is built for."""

        return self._n_ports

    def set_port_count(self, n_ports: int) -> None:
        """Rebuild the parameter grid for a port count.

        Buttons are labelled with one-based port numbers for display and
        carry zero-based indices internally.
        """

        for button in self._parameter_buttons.buttons():
            self._parameter_buttons.removeButton(button)
            button.setParent(None)
        while self._parameter_grid.count():
            item = self._parameter_grid.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.setParent(None)

        self._n_ports = n_ports
        for response in range(n_ports):
            for source in range(n_ports):
                button = QToolButton(self.parameter_box)
                button.setText(f"S{response + 1}{source + 1}")
                button.setCheckable(True)
                self._parameter_grid.addWidget(button, response, source)
                self._parameter_buttons.addButton(button, response * n_ports + source)
            self._parameter_grid.setColumnStretch(response, 1)

        first = self._parameter_buttons.button(0)
        if first is not None:
            first.setChecked(True)
        self._refresh_formats()
        self._set_enabled(n_ports > 0)

    def selected_parameter(self) -> tuple[int, int] | None:
        """Selected S-parameter as zero-based (response, source), if any."""

        button_id = self._parameter_buttons.checkedId()
        if button_id < 0 or self._n_ports == 0:
            return None
        return divmod(button_id, self._n_ports)

    def selected_format(self) -> SParameterFormat | None:
        """Selected display format, if any."""

        value = self.format_combo.currentData()
        return SParameterFormat(value) if value else None

    def set_summary(self, file_name: str, n_ports: int, n_points: int, z0: complex) -> None:
        """Show the current data file's key properties and rebuild the grid."""

        self.file_value.setText(file_name)
        self.ports_value.setText(str(n_ports))
        self.points_value.setText(str(n_points))
        self.z0_value.setText(f"{z0.real:g} Ω")
        if n_ports != self._n_ports:
            self.set_port_count(n_ports)

    def set_traces(self, names: tuple[str, ...]) -> None:
        """Replace the listed trace names."""

        self.trace_list.clear()
        self.trace_list.addItems(list(names))

    def clear(self) -> None:
        """Reset to the empty state."""

        for label in (self.file_value, self.ports_value, self.points_value, self.z0_value):
            label.setText(PLACEHOLDER)
        self.trace_list.clear()
        self.set_port_count(0)

    def _set_enabled(self, enabled: bool) -> None:
        self.format_combo.setEnabled(enabled)
        self.add_button.setEnabled(enabled)
        self.new_plot_button.setEnabled(enabled)

    def _on_parameter_toggled(self, button_id: int, checked: bool) -> None:
        if checked:
            self._refresh_formats()

    def _refresh_formats(self) -> None:
        parameter = self.selected_parameter()
        self.format_combo.clear()
        if parameter is None:
            return
        for data_format in cartesian_formats_for(*parameter):
            self.format_combo.addItem(format_display_name(data_format), data_format.value)

    def _on_add_clicked(self) -> None:
        self._emit(self.add_trace_requested)

    def _on_new_plot_clicked(self) -> None:
        self._emit(self.new_plot_requested)

    def _emit(self, signal: pyqtBoundSignal) -> None:
        parameter = self.selected_parameter()
        data_format = self.selected_format()
        if parameter is None or data_format is None:
            return
        signal.emit(parameter[0], parameter[1], data_format.value)
