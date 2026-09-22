from PyQt6.QtWidgets import QDialog
from pytestqt.qtbot import QtBot

from interconnect_studio.ui.dialogs import AddTraceDialog


def combo_values(dialog: AddTraceDialog) -> list[str]:
    return [
        str(dialog.format_combo.itemData(index))
        for index in range(dialog.format_combo.count())
    ]


def test_add_trace_dialog_lists_all_two_port_s_parameters(qtbot: QtBot) -> None:
    dialog = AddTraceDialog()
    qtbot.addWidget(dialog)

    assert [
        dialog.parameter_combo.itemText(index)
        for index in range(dialog.parameter_combo.count())
    ] == ["S11", "S21", "S12", "S22"]


def test_add_trace_dialog_reflection_parameter_includes_swr(qtbot: QtBot) -> None:
    dialog = AddTraceDialog()
    qtbot.addWidget(dialog)

    dialog.parameter_combo.setCurrentText("S11")

    assert "swr" in combo_values(dialog)
    assert "impedance_real" in combo_values(dialog)


def test_add_trace_dialog_transmission_parameter_hides_reflection_formats(
    qtbot: QtBot,
) -> None:
    dialog = AddTraceDialog()
    qtbot.addWidget(dialog)

    dialog.parameter_combo.setCurrentText("S21")

    values = combo_values(dialog)
    assert "swr" not in values
    assert "impedance_real" not in values
    assert "group_delay" in values
    assert "phase" in values


def test_add_trace_dialog_selection_returns_zero_based_ports(qtbot: QtBot) -> None:
    dialog = AddTraceDialog()
    qtbot.addWidget(dialog)

    dialog.parameter_combo.setCurrentText("S12")
    dialog.format_combo.setCurrentText("Phase")

    selection = dialog.selection()

    assert selection.response_port == 0
    assert selection.source_port == 1
    assert selection.data_format.value == "phase"
    assert dialog.result() == QDialog.DialogCode.Rejected
