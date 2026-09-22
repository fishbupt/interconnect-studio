import pytest
from pytestqt.qtbot import QtBot

from interconnect_studio.algorithms.network import SParameterFormat
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

    assert blocker.args == [1, 0, SParameterFormat.LOG_MAG.value]


def test_new_plot_button_emits_selection(qtbot: QtBot) -> None:
    widget = panel(qtbot, 2)

    with qtbot.waitSignal(widget.new_plot_requested) as blocker:
        widget.new_plot_button.click()

    assert blocker.args == [0, 0, SParameterFormat.LOG_MAG.value]


def test_set_summary_rebuilds_the_grid_for_the_port_count(qtbot: QtBot) -> None:
    widget = panel(qtbot, 2)

    widget.set_summary("dut.s4p", 4, 201, 50.0)

    assert widget.n_ports == 4
    assert widget.ports_value.text() == "4"


def test_clear_resets_the_panel(qtbot: QtBot) -> None:
    widget = panel(qtbot, 2)
    widget.set_summary("dut.s2p", 2, 201, 50.0)

    widget.clear()

    assert widget.n_ports == 0
    assert widget.file_value.text() == "-"
    assert widget.add_button.isEnabled() is False
