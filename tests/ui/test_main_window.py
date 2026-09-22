from pathlib import Path

from PyQt6.QtWidgets import QMainWindow
from pytestqt.qtbot import QtBot

from interconnect_studio.ui import MainWindow

DATA_DIR = Path(__file__).parents[1] / "data" / "touchstone"


def test_main_window_can_be_created(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert isinstance(window, QMainWindow)
    assert window.windowTitle() == "Interconnect Studio"
    assert window.project_tree is not None
    assert window.plot_widget is not None
    assert window.property_panel is not None
    assert window.log_panel is not None


def test_main_window_loads_s2p_and_updates_all_primary_panels(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    loaded = window.load_touchstone_file(DATA_DIR / "valid_2port_ri.s2p")

    assert window.loaded_measurement is loaded
    assert window.plot_widget.model.n_traces == 2
    assert window.plot_widget.model.traces[0].name == "S11 Log Mag"
    assert window.plot_widget.model.traces[1].name == "S21 Log Mag"

    root = window.project_tree.topLevelItem(0)
    assert root is not None
    assert root.text(0) == "valid_2port_ri.s2p"
    assert root.childCount() == 2
    assert root.child(0).text(0) == "S11 Log Mag"
    assert root.child(1).text(0) == "S21 Log Mag"

    assert window.file_value.text() == "valid_2port_ri.s2p"
    assert window.ports_value.text() == "2"
    assert window.points_value.text() == "2"
    assert window.z0_value.text() == "75 Ω"
    assert "Loaded:" in window.log_panel.toPlainText()
    assert "S11 Log Mag, S21 Log Mag" in window.log_panel.toPlainText()


def test_main_window_enables_add_trace_after_loading(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.add_trace_action.isEnabled() is False

    window.load_touchstone_file(DATA_DIR / "valid_2port_ri.s2p")

    assert window.add_trace_action.isEnabled() is True


def test_main_window_adds_compatible_trace(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_touchstone_file(DATA_DIR / "valid_2port_ri.s2p")

    loaded = window.add_trace(0, 1, "log_mag")

    assert loaded.plot.n_traces == 3
    assert loaded.plot.traces[-1].name == "S12 Log Mag"
    root = window.project_tree.topLevelItem(0)
    assert root is not None
    assert root.childCount() == 3
    assert root.child(2).text(0) == "S12 Log Mag"
    assert "Added trace: S12 Log Mag" in window.log_panel.toPlainText()


def test_main_window_switches_plot_for_incompatible_format(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_touchstone_file(DATA_DIR / "valid_2port_ri.s2p")

    loaded = window.add_trace(1, 1, "phase")

    assert loaded.plot.n_traces == 1
    assert loaded.plot.traces[0].name == "S22 Phase"
    root = window.project_tree.topLevelItem(0)
    assert root is not None
    assert root.childCount() == 1
    assert root.child(0).text(0) == "S22 Phase"
    assert "Plot switched to: S22 Phase" in window.log_panel.toPlainText()
