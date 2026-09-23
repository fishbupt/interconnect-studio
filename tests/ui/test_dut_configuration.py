from pytestqt.qtbot import QtBot

from interconnect_studio.algorithms.mixed_mode import (
    DEFAULT_FOUR_PORT_TOPOLOGY,
    FOUR_PORT_TOPOLOGIES,
    topology_by_id,
)
from interconnect_studio.ui.dialogs import DutConfigurationDialog
from interconnect_studio.ui.theme import Theme
from interconnect_studio.ui.widgets import TopologyView


def test_dialog_offers_every_four_port_topology(qtbot: QtBot) -> None:
    dialog = DutConfigurationDialog()
    qtbot.addWidget(dialog)

    assert len(dialog.views) == len(FOUR_PORT_TOPOLOGIES)
    assert [view.topology.id for view in dialog.views] == [t.id for t in FOUR_PORT_TOPOLOGIES]


def test_dialog_defaults_to_the_plts_topology(qtbot: QtBot) -> None:
    dialog = DutConfigurationDialog()
    qtbot.addWidget(dialog)

    assert dialog.topology().id == DEFAULT_FOUR_PORT_TOPOLOGY.id


def test_dialog_opens_on_the_given_topology(qtbot: QtBot) -> None:
    crossed = topology_by_id("through_1_4_2_3")
    dialog = DutConfigurationDialog(crossed)
    qtbot.addWidget(dialog)

    assert dialog.topology().id == crossed.id


def test_selecting_a_choice_changes_the_topology(qtbot: QtBot) -> None:
    dialog = DutConfigurationDialog()
    qtbot.addWidget(dialog)

    dialog.set_topology(topology_by_id("through_1_3_2_4"))

    assert dialog.topology().id == "through_1_3_2_4"


def test_topology_view_renders_without_error(qtbot: QtBot) -> None:
    view = TopologyView(DEFAULT_FOUR_PORT_TOPOLOGY)
    qtbot.addWidget(view)
    view.resize(200, 110)

    view.grab()  # paintEvent runs here


def test_topology_view_can_switch_topology_and_theme(qtbot: QtBot) -> None:
    view = TopologyView(DEFAULT_FOUR_PORT_TOPOLOGY)
    qtbot.addWidget(view)

    view.set_topology(topology_by_id("through_1_4_2_3"))
    view.apply_theme(Theme.DARK)

    assert view.topology.id == "through_1_4_2_3"
    view.grab()


def test_topology_view_tooltip_names_the_topology(qtbot: QtBot) -> None:
    view = TopologyView(DEFAULT_FOUR_PORT_TOPOLOGY)
    qtbot.addWidget(view)

    assert DEFAULT_FOUR_PORT_TOPOLOGY.name in view.toolTip()
