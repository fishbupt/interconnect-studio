"""DUT Configuration dialog, reached from Import's "Change" button.

PLTS calls these Quick Topologies and picks them graphically, so each choice
shows its own schematic rather than only a name. Getting this wrong is a
silent error -- the mixed-mode parameters come out mapped to the wrong ports
without anything failing -- which is why it is an explicit step.
"""

from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from interconnect_studio.algorithms.mixed_mode import (
    DEFAULT_FOUR_PORT_TOPOLOGY,
    FOUR_PORT_TOPOLOGIES,
    Topology,
)
from interconnect_studio.ui.theme import DEFAULT_THEME, Theme
from interconnect_studio.ui.widgets import TopologyView


class DutConfigurationDialog(QDialog):
    """Pick the DUT topology of a four-port measurement."""

    def __init__(
        self,
        topology: Topology = DEFAULT_FOUR_PORT_TOPOLOGY,
        parent: QWidget | None = None,
        theme: Theme = DEFAULT_THEME,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("DUT Configuration")

        self._buttons = QButtonGroup(self)
        self._buttons.setExclusive(True)
        self.views: list[TopologyView] = []

        choices = QHBoxLayout()
        for index, choice in enumerate(FOUR_PORT_TOPOLOGIES):
            choices.addWidget(self._build_choice(choice, index, theme))

        dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        dialog_buttons.accepted.connect(self.accept)
        dialog_buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(choices)
        layout.addWidget(dialog_buttons)

        self.set_topology(topology)

    def topology(self) -> Topology:
        """Currently selected topology."""

        return FOUR_PORT_TOPOLOGIES[self._buttons.checkedId()]

    def set_topology(self, topology: Topology) -> None:
        """Select a topology by value."""

        for index, choice in enumerate(FOUR_PORT_TOPOLOGIES):
            if choice.id == topology.id:
                button = self._buttons.button(index)
                if button is not None:
                    button.setChecked(True)
                return

    def _build_choice(self, topology: Topology, index: int, theme: Theme) -> QFrame:
        frame = QFrame(self)
        frame.setFrameShape(QFrame.Shape.StyledPanel)

        view = TopologyView(topology, frame, theme=theme)
        self.views.append(view)

        radio = QRadioButton(f"{topology.name}  ({topology.label()})", frame)
        radio.setToolTip(topology.description)
        self._buttons.addButton(radio, index)

        layout = QVBoxLayout(frame)
        layout.addWidget(view, 1)
        layout.addWidget(radio)
        return frame
