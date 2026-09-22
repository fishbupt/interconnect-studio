from pathlib import Path

from PyQt6.QtWidgets import QMainWindow
from pytestqt.qtbot import QtBot

from interconnect_studio.ui import MainWindow
from interconnect_studio.ui.theme import Theme

DATA_DIR = Path(__file__).parents[1] / "data" / "touchstone"
S2P = DATA_DIR / "valid_2port_ri.s2p"


def trace_names(window: MainWindow) -> list[str]:
    listing = window.parameter_format.trace_list
    return [listing.item(row).text() for row in range(listing.count())]


def test_main_window_can_be_created(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert isinstance(window, QMainWindow)
    assert window.windowTitle() == "Interconnect Studio"
    assert window.data_browser is not None
    assert window.parameter_format is not None
    assert window.plot_widget is not None


def test_view_area_is_central_and_panels_are_docks(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.centralWidget() is window.view_area
    assert window.plot_widget is window.view_area.current_plot_widget
    assert window.data_browser_dock.widget() is window.data_browser
    assert window.parameter_format_dock.widget() is window.parameter_format


def test_message_panel_is_collapsed_by_default(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.message_dock.isVisibleTo(window) is False
    assert window.messages_button.isChecked() is False


def test_messages_button_toggles_message_panel(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window.messages_button.setChecked(True)
    assert window.message_dock.isVisibleTo(window) is True

    window.messages_button.setChecked(False)
    assert window.message_dock.isVisibleTo(window) is False


def test_main_window_loads_s2p_and_updates_all_primary_panels(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    loaded = window.load_touchstone_file(S2P)

    assert window.loaded_measurement is loaded
    assert window.plot_widget.model.n_traces == 2
    assert trace_names(window) == ["S11 Log Mag", "S21 Log Mag"]

    assert window.parameter_format.file_value.text() == "valid_2port_ri.s2p"
    assert window.parameter_format.ports_value.text() == "2"
    assert window.parameter_format.points_value.text() == "2"
    assert window.parameter_format.z0_value.text() == "75 Ω"

    assert "Loaded:" in window.message_log.text()
    assert "S11 Log Mag, S21 Log Mag" in window.message_log.text()


def test_data_browser_shows_fixed_three_level_hierarchy(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window.load_touchstone_file(S2P)

    group = window.data_browser.tree.topLevelItem(0)
    assert group is not None
    assert group.text(0) == "Group 1"

    measurement = group.child(0)
    assert measurement.text(0) == "Measurement 1"

    data_file = measurement.child(0)
    assert data_file.text(0) == "valid_2port_ri.s2p"
    assert data_file.childCount() == 0


def test_main_window_enables_add_trace_after_loading(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.add_trace_action.isEnabled() is False

    window.load_touchstone_file(S2P)

    assert window.add_trace_action.isEnabled() is True


def test_main_window_adds_compatible_trace(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_touchstone_file(S2P)

    loaded = window.add_trace(0, 1, "log_mag")

    assert loaded.plot.n_traces == 3
    assert trace_names(window) == ["S11 Log Mag", "S21 Log Mag", "S12 Log Mag"]
    assert "Added trace: S12 Log Mag" in window.message_log.text()


def test_main_window_switches_plot_for_incompatible_format(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_touchstone_file(S2P)

    loaded = window.add_trace(1, 1, "phase")

    assert loaded.plot.n_traces == 1
    assert trace_names(window) == ["S22 Phase"]
    assert "Plot switched to: S22 Phase" in window.message_log.text()


def test_main_window_defaults_to_dark_theme(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.theme is Theme.DARK
    assert window.plot_widget.theme is Theme.DARK
    assert window.light_theme_action.isChecked() is False


def test_light_theme_action_switches_theme(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window.light_theme_action.setChecked(True)

    assert window.theme is Theme.LIGHT
    assert window.plot_widget.theme is Theme.LIGHT


def test_layout_menu_switches_grid(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_touchstone_file(S2P)

    window.set_grid(2, 2)

    assert window.view_area.layout_model.n_cells == 4
    assert window.layout_actions[(2, 2)].isChecked() is True
    assert window.layout_actions[(1, 1)].isChecked() is False
    assert window.view_area.plot_widget_at(0).model.n_traces == 2


def test_loading_targets_the_selected_cell(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_grid(1, 2)
    window.view_area.set_current_index(1)

    window.load_touchstone_file(S2P)

    assert window.view_area.plot_widget_at(1).model.n_traces == 2
    assert window.view_area.plot_widget_at(0).model.n_traces == 0
