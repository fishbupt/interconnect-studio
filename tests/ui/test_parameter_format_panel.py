import pytest
from pytestqt.qtbot import QtBot

from interconnect_studio.algorithms.mixed_mode import DEFAULT_FOUR_PORT_TOPOLOGY
from interconnect_studio.algorithms.network import SParameterFormat
from interconnect_studio.core import DutConfiguration, Mode, quick_topology
from interconnect_studio.ui.panels import ParameterFormatPanel


def panel(qtbot: QtBot, n_ports: int = 2) -> ParameterFormatPanel:
    widget = ParameterFormatPanel()
    qtbot.addWidget(widget)
    widget.set_port_count(n_ports)
    return widget


def format_values(widget: ParameterFormatPanel) -> list[str]:
    combo = widget.format_combo
    return [combo.itemData(row) for row in range(combo.count())]


def test_panel_starts_empty_and_disabled(qtbot: QtBot) -> None:
    widget = ParameterFormatPanel()
    qtbot.addWidget(widget)

    assert widget.n_ports == 0
    assert widget.selected_parameter() is None
    assert widget.add_button.isEnabled() is False


@pytest.mark.parametrize(("n_ports", "expected"), [(1, 1), (2, 4), (4, 16)])
def test_grid_has_one_button_per_parameter(qtbot: QtBot, n_ports: int, expected: int) -> None:
    widget = panel(qtbot, n_ports)

    assert len(widget._parameter_buttons.buttons()) == expected


def test_buttons_are_labelled_with_one_based_ports(qtbot: QtBot) -> None:
    widget = panel(qtbot, 2)

    labels = [button.text() for button in widget._parameter_buttons.buttons()]
    assert set(labels) == {"S11", "S12", "S21", "S22"}


def test_first_parameter_is_selected_by_default(qtbot: QtBot) -> None:
    widget = panel(qtbot, 2)

    assert widget.selected_parameter() == (0, 0)


def test_selection_maps_to_zero_based_ports(qtbot: QtBot) -> None:
    widget = panel(qtbot, 2)

    widget._parameter_buttons.button(2).setChecked(True)

    assert widget.selected_parameter() == (1, 0)


def test_reflection_parameter_offers_impedance_formats(qtbot: QtBot) -> None:
    widget = panel(qtbot, 2)

    widget._parameter_buttons.button(0).setChecked(True)

    assert SParameterFormat.SWR.value in format_values(widget)


def test_transmission_parameter_hides_reflection_formats(qtbot: QtBot) -> None:
    widget = panel(qtbot, 2)

    widget._parameter_buttons.button(2).setChecked(True)

    values = format_values(widget)
    assert SParameterFormat.SWR.value not in values
    assert SParameterFormat.LOG_MAG.value in values


def test_add_button_emits_selection(qtbot: QtBot) -> None:
    widget = panel(qtbot, 2)
    widget._parameter_buttons.button(2).setChecked(True)

    with qtbot.waitSignal(widget.add_trace_requested) as blocker:
        widget.add_button.click()

    choice, data_format = blocker.args
    assert (choice.response_port, choice.source_port) == (1, 0)
    assert choice.is_mixed_mode is False
    assert data_format == SParameterFormat.LOG_MAG.value


def test_new_plot_button_emits_selection(qtbot: QtBot) -> None:
    widget = panel(qtbot, 2)

    with qtbot.waitSignal(widget.new_plot_requested) as blocker:
        widget.new_plot_button.click()

    choice, data_format = blocker.args
    assert (choice.response_port, choice.source_port) == (0, 0)
    assert data_format == SParameterFormat.LOG_MAG.value


def test_set_summary_only_updates_the_summary(qtbot: QtBot) -> None:
    """The grid shape follows the view type, so the summary must not guess it."""

    widget = panel(qtbot, 2)

    widget.set_summary("dut.s4p", 4, 201, 50.0)

    assert widget.ports_value.text() == "4"
    assert widget.n_ports == 2


def test_clear_resets_the_panel(qtbot: QtBot) -> None:
    widget = panel(qtbot, 2)
    widget.set_summary("dut.s2p", 2, 201, 50.0)

    widget.clear()

    assert widget.n_ports == 0
    assert widget.file_value.text() == "-"
    assert widget.add_button.isEnabled() is False


def test_mixed_mode_grid_is_the_block_matrix(qtbot: QtBot) -> None:
    widget = ParameterFormatPanel()
    qtbot.addWidget(widget)

    widget.set_mixed_mode(2)

    labels = [button.text() for button in widget._parameter_buttons.buttons()]
    assert widget.is_mixed_mode is True
    assert labels[:4] == ["SDD11", "SDD12", "SDC11", "SDC12"]
    assert labels[4:8] == ["SDD21", "SDD22", "SDC21", "SDC22"]
    assert labels[8:12] == ["SCD11", "SCD12", "SCC11", "SCC12"]
    assert labels[12:] == ["SCD21", "SCD22", "SCC21", "SCC22"]


def test_mixed_mode_selection_carries_its_modes(qtbot: QtBot) -> None:
    widget = ParameterFormatPanel()
    qtbot.addWidget(widget)
    widget.set_mixed_mode(2)

    widget._parameter_buttons.button(4).setChecked(True)  # SDD21

    choice = widget.selected_choice()
    assert choice is not None
    assert choice.label == "SDD21"
    assert choice.response_mode is Mode.DIFFERENTIAL
    assert choice.source_mode is Mode.DIFFERENTIAL
    assert (choice.response_port, choice.source_port) == (1, 0)


def test_mixed_mode_reflection_offers_impedance_formats(qtbot: QtBot) -> None:
    widget = ParameterFormatPanel()
    qtbot.addWidget(widget)
    widget.set_mixed_mode(2)

    widget._parameter_buttons.button(0).setChecked(True)  # SDD11

    assert SParameterFormat.SWR.value in format_values(widget)


def test_mode_conversion_terms_hide_impedance_formats(qtbot: QtBot) -> None:
    """SDC11 sits on one port but relates two modes, so no single z0 applies."""

    widget = ParameterFormatPanel()
    qtbot.addWidget(widget)
    widget.set_mixed_mode(2)

    widget._parameter_buttons.button(2).setChecked(True)  # SDC11

    assert SParameterFormat.SWR.value not in format_values(widget)


def test_switching_back_to_single_ended_clears_mixed_mode(qtbot: QtBot) -> None:
    widget = ParameterFormatPanel()
    qtbot.addWidget(widget)
    widget.set_mixed_mode(2)

    widget.set_port_count(4)

    assert widget.is_mixed_mode is False
    assert widget._parameter_buttons.button(0).text() == "S11"


def labelled_four_port() -> DutConfiguration:
    return DEFAULT_FOUR_PORT_TOPOLOGY.dut_configuration().with_labels(
        ("TX+", "RX+", "TX-", "RX-")
    )


def tooltips(widget: ParameterFormatPanel) -> list[str]:
    return [button.toolTip() for button in widget._parameter_buttons.buttons()]


def test_tooltip_names_the_ports_without_a_configuration(qtbot: QtBot) -> None:
    """A 32-port grid of small buttons needs this even with no DUT labels."""

    widget = panel(qtbot, 2)

    assert tooltips(widget)[1] == "S12: response at port 1, source at port 2"


def test_tooltip_carries_the_dut_port_labels(qtbot: QtBot) -> None:
    widget = ParameterFormatPanel()
    qtbot.addWidget(widget)

    widget.set_port_count(4, labelled_four_port())

    assert tooltips(widget)[4] == "S21: response at port 2 (RX+), source at port 1 (TX+)"


def test_reflection_tooltip_names_one_port_only(qtbot: QtBot) -> None:
    widget = ParameterFormatPanel()
    qtbot.addWidget(widget)

    widget.set_port_count(4, labelled_four_port())

    assert tooltips(widget)[0] == "S11: reflection at port 1 (TX+)"


def test_mixed_mode_tooltip_names_the_logical_ports(qtbot: QtBot) -> None:
    """SDD21 relates the two ends of the pair, each a labelled pair of ports."""

    widget = ParameterFormatPanel()
    qtbot.addWidget(widget)

    widget.set_mixed_mode(2, labelled_four_port())

    assert tooltips(widget)[4] == (
        "SDD21: response at differential logical port 2 (RX+ / RX-), "
        "source at differential logical port 1 (TX+ / TX-)"
    )


def test_mode_conversion_tooltip_keeps_both_modes(qtbot: QtBot) -> None:
    """SDC11 sits on one port but relates two modes, so it is not a reflection."""

    widget = ParameterFormatPanel()
    qtbot.addWidget(widget)

    widget.set_mixed_mode(2, labelled_four_port())

    assert tooltips(widget)[2] == (
        "SDC11: response at differential logical port 1 (TX+ / TX-), "
        "source at common logical port 1 (TX+ / TX-)"
    )


def test_mixed_mode_reflection_tooltip_is_one_phrase(qtbot: QtBot) -> None:
    widget = ParameterFormatPanel()
    qtbot.addWidget(widget)

    widget.set_mixed_mode(2, labelled_four_port())

    assert tooltips(widget)[0] == (
        "SDD11: reflection at differential logical port 1 (TX+ / TX-)"
    )


def test_a_configuration_of_another_size_is_dropped_whole(qtbot: QtBot) -> None:
    """Labelling the first two ports and no others would read as fact."""

    widget = ParameterFormatPanel()
    qtbot.addWidget(widget)

    widget.set_port_count(4, DutConfiguration.single_ended(2).with_labels(("IN", "OUT")))

    assert tooltips(widget)[0] == "S11: reflection at port 1"
    assert tooltips(widget)[-1] == "S44: reflection at port 4"


def test_a_mixed_mode_configuration_of_another_size_is_dropped_too(qtbot: QtBot) -> None:
    widget = ParameterFormatPanel()
    qtbot.addWidget(widget)

    widget.set_mixed_mode(2, quick_topology("2_diff_reflection"))

    assert tooltips(widget)[0] == "SDD11: reflection at differential logical port 1"
