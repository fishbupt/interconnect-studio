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
