"""DUT Configuration dialog, reached from Import's "Change" button.

PLTS calls these Quick Topologies and picks them graphically, so each choice
shows its own schematic rather than only a name. Getting this wrong is a
silent error -- the mixed-mode parameters come out mapped to the wrong ports
without anything failing -- which is why it is an explicit step.

Single-ended is always offered and is always listed first: it asserts
nothing about how the ports connect, which is the honest state for a file
nobody has described yet. It is not the preselected one -- that is
``default_configuration``, what the file was actually imported as.

Port labels describe the DUT, not the topology picked for it, so the dialog
holds them once and applies them to whichever choice is selected. Switching
between wirings keeps what the user typed.

``configuration_choices`` and ``default_configuration`` are presentation
policy -- what to offer, and what to preselect -- so they live here rather
than in the domain model, and the Import dialog reads them from here so the
two cannot disagree about what a file opens as.
"""

from pathlib import Path

from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from interconnect_studio.algorithms.mixed_mode import (
    DEFAULT_FOUR_PORT_TOPOLOGY,
    FOUR_PORT_TOPOLOGIES,
)
from interconnect_studio.core import (
    DataFormatError,
    DutConfiguration,
    quick_topologies_for,
)
from interconnect_studio.io import (
    DUT_CONFIG_SUFFIX,
    read_dut_configuration,
    write_dut_configuration,
)
from interconnect_studio.ui.theme import DEFAULT_THEME, Theme
from interconnect_studio.ui.widgets import DutConfigurationView, PortLabelTable

_CHOICES_PER_ROW = 4
_FILE_FILTER = f"DUT Configuration (*{DUT_CONFIG_SUFFIX})"


def configuration_choices(n_ports: int) -> tuple[DutConfiguration, ...]:
    """Every configuration offered for a port count, in display order.

    Single-ended first, then the four-port through-path wirings, then the
    remaining Quick Topology presets.
    """

    choices = [DutConfiguration.single_ended(n_ports)]
    if n_ports == 4:
        choices.extend(topology.dut_configuration() for topology in FOUR_PORT_TOPOLOGIES)
    choices.extend(configuration for _, configuration in quick_topologies_for(n_ports))
    return tuple(choices)


def default_configuration(n_ports: int) -> DutConfiguration:
    """What a file of this port count opens as, and what Reset restores.

    PLTS opens four-port data as a differential pair; everything else stays
    single-ended until someone says otherwise.
    """

    if n_ports == 4:
        return DEFAULT_FOUR_PORT_TOPOLOGY.dut_configuration()
    return DutConfiguration.single_ended(n_ports)


class DutConfigurationDialog(QDialog):
    """Pick how a measurement's ports are grouped and addressed."""

    def __init__(
        self,
        n_ports: int,
        configuration: DutConfiguration | None = None,
        parent: QWidget | None = None,
        theme: Theme = DEFAULT_THEME,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("DUT Configuration")

        self._n_ports = n_ports
        self._theme = theme
        self._choices: list[DutConfiguration] = list(configuration_choices(n_ports))
        self._buttons = QButtonGroup(self)
        self._buttons.setExclusive(True)
        self.views: list[DutConfigurationView] = []

        # A four-port file offers seven choices; one row of seven would
        # force the dialog wider than the screen.
        self._grid = QGridLayout()
        for index, choice in enumerate(self._choices):
            self._place_choice(choice, index)

        self.labels = PortLabelTable(n_ports, self)
        label_box = QGroupBox("Port Labels", self)
        label_layout = QVBoxLayout(label_box)
        label_layout.addWidget(self.labels)
        self.error_label = QLabel(self)
        self.error_label.setWordWrap(True)
        # Matches the Import dialog's error styling.
        self.error_label.setStyleSheet("color: #c0392b;")

        self.reset_button = QPushButton("Reset", self)
        self.reset_button.setToolTip(
            f"Back to {default_configuration(n_ports).name}, what this file opens as."
        )
        self.save_button = QPushButton("Save As ...", self)
        self.load_button = QPushButton("Load ...", self)
        self.dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self.dialog_buttons.accepted.connect(self.accept)
        self.dialog_buttons.rejected.connect(self.reject)
        self.reset_button.clicked.connect(self.reset)
        self.save_button.clicked.connect(self.save_as)
        self.load_button.clicked.connect(self.load)

        # Laid out by hand rather than by button role: Qt's roles would
        # scatter Save As and Load between OK and Cancel. The three actions
        # that touch this dialog's own state belong together, away from the
        # two that close it.
        actions = QHBoxLayout()
        actions.addWidget(self.reset_button)
        actions.addWidget(self.save_button)
        actions.addWidget(self.load_button)
        actions.addStretch(1)
        actions.addWidget(self.dialog_buttons)

        body = QHBoxLayout()
        body.addLayout(self._grid, 1)
        body.addWidget(label_box)

        layout = QVBoxLayout(self)
        layout.addLayout(body)
        layout.addWidget(self.error_label)
        layout.addLayout(actions)

        self._buttons.idToggled.connect(self._on_choice_toggled)
        self.labels.labels_changed.connect(self._refresh_validity)

        # Not self._choices[0]: opening the dialog on a four-port file and
        # pressing OK untouched must not quietly demote it from the
        # differential pair it was imported as.
        self.set_configuration(configuration or default_configuration(n_ports))

    def configuration(self) -> DutConfiguration:
        """The selected wiring, carrying the labels currently typed in."""

        return self._choices[self._buttons.checkedId()].with_labels(self.labels.labels())

    def set_configuration(self, configuration: DutConfiguration) -> None:
        """Select a configuration, adding it as a choice if it is new.

        Labels come along and are adopted as the dialog's own, so matching
        ignores them: two choices differing only in labels are the same
        wiring. A different name or grouping is not, and becomes its own
        choice rather than being snapped to the nearest preset, which would
        throw away what the file said.
        """

        self.labels.set_labels(configuration.port_labels)
        for index, choice in enumerate(self._choices):
            if (
                choice.port_group == configuration.port_group
                and choice.name == configuration.name
            ):
                self._select(index)
                return
        self._choices.append(configuration)
        self._place_choice(configuration, len(self._choices) - 1)
        self._select(len(self._choices) - 1)

    def reset(self) -> None:
        """Back to what a file of this port count opens as."""

        self.set_configuration(default_configuration(self._n_ports))

    def save_as(self) -> None:
        """Write the selected configuration, labels included, to a file."""

        if not self.labels.is_valid():
            return
        configuration = self.configuration()
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save DUT Configuration",
            f"{configuration.name}{DUT_CONFIG_SUFFIX}",
            _FILE_FILTER,
        )
        if not file_name:
            return
        path = Path(file_name)
        if not path.suffix:
            path = path.with_suffix(DUT_CONFIG_SUFFIX)
        try:
            write_dut_configuration(configuration, path)
        except DataFormatError as exc:
            QMessageBox.warning(self, "Save DUT Configuration", str(exc))

    def load(self) -> None:
        """Read a ``.dutcfg`` file and select what it describes."""

        file_name, _ = QFileDialog.getOpenFileName(
            self, "Load DUT Configuration", "", _FILE_FILTER
        )
        if not file_name:
            return
        try:
            configuration = read_dut_configuration(file_name)
        except DataFormatError as exc:
            QMessageBox.warning(self, "Load DUT Configuration", str(exc))
            return
        if configuration.n_ports != self._n_ports:
            QMessageBox.warning(
                self,
                "Load DUT Configuration",
                f"{Path(file_name).name} describes a {configuration.n_ports}-port DUT, "
                f"but this measurement has {self._n_ports} ports.",
            )
            return
        self.set_configuration(configuration)

    def _select(self, index: int) -> None:
        button = self._buttons.button(index)
        if button is not None:
            button.setChecked(True)
        self._refresh_validity()

    def _on_choice_toggled(self, index: int, checked: bool) -> None:
        if checked:
            self._refresh_validity()

    def _refresh_validity(self) -> None:
        """A blank label cannot be saved or accepted, so say so and block it."""

        valid = self.labels.is_valid()
        self.error_label.setText(
            "" if valid else "Every port needs a label before this can be used."
        )
        for button in (
            self.dialog_buttons.button(QDialogButtonBox.StandardButton.Ok),
            self.save_button,
        ):
            if button is not None:
                button.setEnabled(valid)
        if valid:
            self.labels.show_logical_ports(self.configuration())

    def _place_choice(self, configuration: DutConfiguration, index: int) -> None:
        row, column = divmod(index, _CHOICES_PER_ROW)
        self._grid.addWidget(self._build_choice(configuration, index), row, column)

    def _build_choice(self, configuration: DutConfiguration, index: int) -> QFrame:
        frame = QFrame(self)
        frame.setFrameShape(QFrame.Shape.StyledPanel)

        view = DutConfigurationView(configuration, frame, theme=self._theme)
        self.views.append(view)

        radio = QRadioButton(configuration.name, frame)
        radio.setToolTip(
            f"{configuration.topology_summary} — "
            f"{configuration.n_logical_ports} logical port(s); "
            f"{configuration.port_summary}"
        )
        self._buttons.addButton(radio, index)

        layout = QVBoxLayout(frame)
        layout.addWidget(view, 1)
        layout.addWidget(radio)
        return frame
