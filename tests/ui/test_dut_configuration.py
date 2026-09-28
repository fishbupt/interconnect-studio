from pytestqt.qtbot import QtBot

from interconnect_studio.algorithms.mixed_mode import (
    DEFAULT_FOUR_PORT_TOPOLOGY,
    FOUR_PORT_TOPOLOGIES,
    topology_by_id,
)
from interconnect_studio.core import DutConfiguration, quick_topology
from interconnect_studio.ui.dialogs import DutConfigurationDialog
from interconnect_studio.ui.dialogs.dut_configuration_dialog import configuration_choices
from interconnect_studio.ui.theme import Theme
from interconnect_studio.ui.widgets import DutConfigurationView


def test_four_port_offers_single_ended_and_every_through_wiring(qtbot: QtBot) -> None:
    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)

    names = [view.configuration.name for view in dialog.views]
    assert names[0] == "Single-Ended"
    assert [topology.name for topology in FOUR_PORT_TOPOLOGIES] == names[1:4]
    assert "4-Port SE-SE" in names


def test_two_port_offers_only_what_fits_it(qtbot: QtBot) -> None:
    dialog = DutConfigurationDialog(2)
    qtbot.addWidget(dialog)

    assert [view.configuration.name for view in dialog.views] == [
        "Single-Ended",
        "2-Port SE-SE",
        "2-Port Differential Reflection",
    ]


def test_an_unusual_port_count_still_offers_single_ended(qtbot: QtBot) -> None:
    """Five ports have no presets, so the dialog is not empty by accident."""

    assert [choice.name for choice in configuration_choices(5)] == ["Single-Ended"]


def test_dialog_defaults_to_single_ended(qtbot: QtBot) -> None:
    """Asserting nothing about the DUT is the honest starting point."""

    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)

    assert dialog.configuration().name == "Single-Ended"


def test_dialog_opens_on_the_given_configuration(qtbot: QtBot) -> None:
    crossed = topology_by_id("through_1_4_2_3").dut_configuration()
    dialog = DutConfigurationDialog(4, crossed)
    qtbot.addWidget(dialog)

    assert dialog.configuration().port_group == crossed.port_group


def test_selecting_a_choice_changes_the_configuration(qtbot: QtBot) -> None:
    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)

    dialog.set_configuration(topology_by_id("through_1_3_2_4").dut_configuration())

    assert dialog.configuration().port_group.lines[0].near == (0, 1)


def test_selection_matches_on_the_grouping_not_the_name(qtbot: QtBot) -> None:
    """A configuration loaded from a file carries the user's own name."""

    renamed = DEFAULT_FOUR_PORT_TOPOLOGY.dut_configuration().renamed("My fixture")
    dialog = DutConfigurationDialog(4, renamed)
    qtbot.addWidget(dialog)

    assert dialog.configuration().port_group == renamed.port_group


def test_view_renders_every_preset_shape(qtbot: QtBot) -> None:
    """Reflection-only, balun and through wirings all reach paintEvent."""

    for configuration in (
        DutConfiguration.single_ended(3),
        quick_topology("2_diff_reflection"),
        quick_topology("3_diff_se"),
        DEFAULT_FOUR_PORT_TOPOLOGY.dut_configuration(),
    ):
        view = DutConfigurationView(configuration)
        qtbot.addWidget(view)
        view.resize(200, 110)
        view.grab()  # paintEvent runs here


def test_view_can_switch_configuration_and_theme(qtbot: QtBot) -> None:
    view = DutConfigurationView(DEFAULT_FOUR_PORT_TOPOLOGY.dut_configuration())
    qtbot.addWidget(view)

    view.set_configuration(topology_by_id("through_1_4_2_3").dut_configuration())
    view.apply_theme(Theme.DARK)

    assert view.configuration.port_group.lines[0].far == (3, 2)
    view.grab()


def test_view_tooltip_names_the_configuration(qtbot: QtBot) -> None:
    view = DutConfigurationView(DEFAULT_FOUR_PORT_TOPOLOGY.dut_configuration())
    qtbot.addWidget(view)

    assert DEFAULT_FOUR_PORT_TOPOLOGY.name in view.toolTip()
    assert "Diff-Diff" in view.toolTip()
