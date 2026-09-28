"""DUT Configuration dialog, reached from Import's "Change" button.

PLTS calls these Quick Topologies and picks them graphically, so each choice
shows its own schematic rather than only a name. Getting this wrong is a
silent error -- the mixed-mode parameters come out mapped to the wrong ports
without anything failing -- which is why it is an explicit step.

Single-ended is always offered and is always first: it asserts nothing about
how the ports connect, which is the honest state for a file nobody has
described yet.
"""

from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from interconnect_studio.algorithms.mixed_mode import FOUR_PORT_TOPOLOGIES
from interconnect_studio.core import DutConfiguration, quick_topologies_for
from interconnect_studio.ui.theme import DEFAULT_THEME, Theme
from interconnect_studio.ui.widgets import DutConfigurationView

_CHOICES_PER_ROW = 4


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

        self._choices = configuration_choices(n_ports)
        self._buttons = QButtonGroup(self)
        self._buttons.setExclusive(True)
        self.views: list[DutConfigurationView] = []

        # A four-port file offers seven choices; one row of seven would
        # force the dialog wider than the screen.
        choices = QGridLayout()
        for index, choice in enumerate(self._choices):
            row, column = divmod(index, _CHOICES_PER_ROW)
            choices.addWidget(self._build_choice(choice, index, theme), row, column)

        dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        dialog_buttons.accepted.connect(self.accept)
        dialog_buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(choices)
        layout.addWidget(dialog_buttons)

        self.set_configuration(configuration or self._choices[0])

    def configuration(self) -> DutConfiguration:
        """Currently selected configuration."""

        return self._choices[self._buttons.checkedId()]

    def set_configuration(self, configuration: DutConfiguration) -> None:
        """Select the offered choice that matches, by its port grouping."""

        for index, choice in enumerate(self._choices):
            if choice.port_group == configuration.port_group:
                button = self._buttons.button(index)
                if button is not None:
                    button.setChecked(True)
                return

    def _build_choice(
        self,
        configuration: DutConfiguration,
        index: int,
        theme: Theme,
    ) -> QFrame:
        frame = QFrame(self)
        frame.setFrameShape(QFrame.Shape.StyledPanel)

        view = DutConfigurationView(configuration, frame, theme=theme)
        self.views.append(view)

        radio = QRadioButton(configuration.name, frame)
        radio.setToolTip(
            f"{configuration.topology_summary} — "
            f"{configuration.n_logical_ports} logical port(s); "
            f"{configuration.through_summary}"
        )
        self._buttons.addButton(radio, index)

        layout = QVBoxLayout(frame)
        layout.addWidget(view, 1)
        layout.addWidget(radio)
        return frame
