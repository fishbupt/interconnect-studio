"""Parameter / format panel.

Where traces are created, matching PLTS: pick a parameter, pick a display
format, then either add it to the current plot or open a new one. Also takes
over what a property panel would otherwise do, summarising the current data
file.

The grid shows single-ended parameters for a plain network and the
mixed-mode block matrix for a differential one, so its layout always matches
the matrix the data actually has.
"""

from dataclasses import dataclass

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

from interconnect_studio.algorithms.mixed_mode import (
    cartesian_formats_for_mixed_mode,
    mixed_mode_parameter_name,
)
from interconnect_studio.algorithms.network import SParameterFormat, cartesian_formats_for
from interconnect_studio.algorithms.network.traces import format_display_name
from interconnect_studio.core import Mode

PLACEHOLDER = "-"


@dataclass(frozen=True, slots=True)
class ParameterChoice:
    """One selectable parameter.

    ``response_mode`` and ``source_mode`` are ``None`` for single-ended
    parameters. Ports are 0-based, and for a mixed-mode choice they index
    within the mode rather than the whole matrix.
    """

    label: str
    response_port: int
    source_port: int
    response_mode: Mode | None = None
    source_mode: Mode | None = None

    @property
    def is_mixed_mode(self) -> bool:
        """Whether this names a mixed-mode parameter."""

        return self.response_mode is not None and self.source_mode is not None


def single_ended_choices(n_ports: int) -> list[ParameterChoice]:
    """Choices for an n-port single-ended matrix, in row-major order."""

    return [
        ParameterChoice(
            label=f"S{response + 1}{source + 1}",
            response_port=response,
            source_port=source,
        )
        for response in range(n_ports)
        for source in range(n_ports)
    ]


def mixed_mode_choices(n_mode_ports: int) -> list[ParameterChoice]:
    """Choices for a mixed-mode matrix, laid out as [[Sdd, Sdc], [Scd, Scc]]."""

    modes = [Mode.DIFFERENTIAL, Mode.COMMON]
    rows = [(mode, port) for mode in modes for port in range(n_mode_ports)]
    return [
        ParameterChoice(
            label=mixed_mode_parameter_name(
                response_mode, source_mode, response_port, source_port
            ),
            response_port=response_port,
            source_port=source_port,
            response_mode=response_mode,
            source_mode=source_mode,
        )
        for response_mode, response_port in rows
        for source_mode, source_port in rows
    ]


class ParameterFormatPanel(QWidget):
    """Select a parameter and format, and summarise the current file."""

    add_trace_requested = pyqtSignal(object, str)
    new_plot_requested = pyqtSignal(object, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._choices: list[ParameterChoice] = []
        self._columns = 0
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
        """Matrix size the grid is built for."""

        return self._columns

    @property
    def is_mixed_mode(self) -> bool:
        """Whether the grid currently shows mixed-mode parameters."""

        return bool(self._choices) and self._choices[0].is_mixed_mode

    def set_port_count(self, n_ports: int) -> None:
        """Show the single-ended matrix for a port count.

        Buttons are labelled with one-based port numbers for display and
        carry zero-based indices internally.
        """

        self._rebuild(single_ended_choices(n_ports), n_ports)

    def set_mixed_mode(self, n_mode_ports: int) -> None:
        """Show the mixed-mode block matrix for a differential DUT."""

        self._rebuild(mixed_mode_choices(n_mode_ports), 2 * n_mode_ports)

    def selected_choice(self) -> ParameterChoice | None:
        """Selected parameter, if any."""

        button_id = self._parameter_buttons.checkedId()
        if button_id < 0 or button_id >= len(self._choices):
            return None
        return self._choices[button_id]

    def selected_parameter(self) -> tuple[int, int] | None:
        """Selected parameter's ports, if any."""

        choice = self.selected_choice()
        return None if choice is None else (choice.response_port, choice.source_port)

    def selected_format(self) -> SParameterFormat | None:
        """Selected display format, if any."""

        value = self.format_combo.currentData()
        return SParameterFormat(value) if value else None

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
        self.set_port_count(0)

    def _rebuild(self, choices: list[ParameterChoice], columns: int) -> None:
        for button in self._parameter_buttons.buttons():
            self._parameter_buttons.removeButton(button)
            button.setParent(None)
        while self._parameter_grid.count():
            item = self._parameter_grid.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.setParent(None)

        self._choices = choices
        self._columns = columns

        for index, choice in enumerate(choices):
            button = QToolButton(self.parameter_box)
            button.setText(choice.label)
            button.setCheckable(True)
            row, column = divmod(index, columns) if columns else (0, 0)
            self._parameter_grid.addWidget(button, row, column)
            self._parameter_buttons.addButton(button, index)
        for column in range(columns):
            self._parameter_grid.setColumnStretch(column, 1)

        first = self._parameter_buttons.button(0)
        if first is not None:
            first.setChecked(True)
        self._refresh_formats()
        self._set_enabled(bool(choices))

    def _set_enabled(self, enabled: bool) -> None:
        self.format_combo.setEnabled(enabled)
        self.add_button.setEnabled(enabled)
        self.new_plot_button.setEnabled(enabled)

    def _on_parameter_toggled(self, button_id: int, checked: bool) -> None:
        if checked:
            self._refresh_formats()

    def _refresh_formats(self) -> None:
        choice = self.selected_choice()
        self.format_combo.clear()
        if choice is None:
            return
        if choice.is_mixed_mode:
            assert choice.response_mode is not None
            assert choice.source_mode is not None
            formats = cartesian_formats_for_mixed_mode(
                choice.response_mode,
                choice.source_mode,
                choice.response_port,
                choice.source_port,
            )
        else:
            formats = cartesian_formats_for(choice.response_port, choice.source_port)
        for data_format in formats:
            self.format_combo.addItem(format_display_name(data_format), data_format.value)

    def _on_add_clicked(self) -> None:
        self._emit(self.add_trace_requested)

    def _on_new_plot_clicked(self) -> None:
        self._emit(self.new_plot_requested)

    def _emit(self, signal: pyqtBoundSignal) -> None:
        choice = self.selected_choice()
        data_format = self.selected_format()
        if choice is None or data_format is None:
            return
        signal.emit(choice, data_format.value)
