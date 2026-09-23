from dataclasses import replace
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QInputDialog, QMainWindow, QMessageBox
from pytestqt.qtbot import QtBot

from interconnect_studio.algorithms.mixed_mode import DEFAULT_FOUR_PORT_TOPOLOGY
from interconnect_studio.core import (
    BrowserCategory,
    InputValidationError,
    Mode,
    TraceRecipe,
    ViewLayout,
    ViewType,
)
from interconnect_studio.io import ImportFileType
from interconnect_studio.services import ImportedNetwork, ImportService
from interconnect_studio.ui import MainWindow
from interconnect_studio.ui.panels.parameter_format import ParameterChoice
from interconnect_studio.ui.theme import Theme

DATA_DIR = Path(__file__).parents[1] / "data" / "touchstone"
S2P = DATA_DIR / "valid_2port_ri.s2p"
IMPORT_DIR = Path(__file__).parents[1] / "data" / "import"


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

    assert "Imported:" in window.message_log.text()
    assert "S11 Log Mag, S21 Log Mag" in window.message_log.text()


def test_loading_opens_a_frequency_domain_single_ended_window(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window.load_touchstone_file(S2P)

    windows = window.data_browser.browser_tree.windows
    assert len(windows) == 1
    assert windows[0].view_type is ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED
    assert windows[0].label == "valid_2port_ri.s2p : 1"


def test_loading_selects_the_new_data_file(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window.load_touchstone_file(S2P)

    current = window.data_browser.current_file()
    assert current is not None
    assert current.name == "valid_2port_ri.s2p"
    assert current.network.n_ports == 2


def test_loading_twice_opens_two_numbered_windows(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window.load_touchstone_file(S2P)
    window.load_touchstone_file(S2P)

    windows = window.data_browser.browser_tree.windows_of(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED)
    assert [item.number for item in windows] == [1, 2]
    assert windows[0].data_file.id != windows[1].data_file.id

    current = window.data_browser.current_window()
    assert current is not None
    assert current.number == 2


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


def test_main_window_defaults_to_light_theme(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.theme is Theme.LIGHT
    assert window.plot_widget.theme is Theme.LIGHT
    assert window.dark_theme_action.isChecked() is False


def test_dark_theme_action_switches_theme(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window.dark_theme_action.setChecked(True)

    assert window.theme is Theme.DARK
    assert window.plot_widget.theme is Theme.DARK

    window.dark_theme_action.setChecked(False)

    assert window.theme is Theme.LIGHT


def test_layout_menu_switches_grid(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_touchstone_file(S2P)

    window.set_grid(2, 2)

    assert window.view_area.layout_model.n_cells == 4
    assert window.layout_actions[(2, 2)].isChecked() is True
    assert window.layout_actions[(1, 1)].isChecked() is False
    assert window.view_area.plot_widget_at(0).model.n_traces == 2


def test_new_window_uses_the_displayed_grid_and_starts_in_its_first_cell(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_grid(1, 2)
    window.view_area.set_current_index(1)

    window.load_touchstone_file(S2P)

    assert window.view_area.layout_model.n_cells == 2
    assert window.view_area.current_index == 0
    assert window.view_area.plot_widget_at(0).model.n_traces == 2
    assert window.view_area.plot_widget_at(1).model.n_traces == 0


def test_panel_add_button_adds_a_trace(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_touchstone_file(S2P)
    panel = window.parameter_format
    panel._parameter_buttons.button(3).setChecked(True)  # S22

    panel.add_button.click()

    assert trace_names(window)[-1] == "S22 Log Mag"
    assert window.plot_widget.model.n_traces == 3


def test_panel_new_plot_button_replaces_the_plot(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_touchstone_file(S2P)
    panel = window.parameter_format
    panel._parameter_buttons.button(3).setChecked(True)

    panel.new_plot_button.click()

    assert trace_names(window) == ["S22 Log Mag"]
    assert window.plot_widget.model.n_traces == 1


def test_panel_grid_matches_the_loaded_port_count(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window.load_touchstone_file(S2P)

    assert window.parameter_format.n_ports == 2


def test_duplicate_trace_is_reported_not_raised(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_touchstone_file(S2P)
    panel = window.parameter_format

    panel.add_button.click()  # S11 Log Mag already present

    assert "Trace already exists" in window.message_log.text()


IMPORT_DIR = Path(__file__).parents[1] / "data" / "import"


def test_file_menu_offers_the_three_plts_import_entries(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.import_single_action.text() == "&Single File..."
    assert window.import_multiple_action.text() == "&Multiple Files (Build a File)..."
    assert window.build_config_action.text() == "Build with a &Config File..."


def test_importing_a_three_port_file_shows_all_nine_parameters(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window.load_touchstone_file(IMPORT_DIR / "three_port.s3p")

    assert window.parameter_format.n_ports == 3
    assert window.parameter_format.ports_value.text() == "3"
    loaded = window.add_trace(2, 0, "log_mag")
    assert loaded.plot.traces[-1].name == "S31 Log Mag"


def test_open_imported_places_a_built_network_in_the_chosen_view(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    imported = ImportService().build_from_config(IMPORT_DIR / "build_config.csv")

    window.open_imported(imported, ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED)

    current = window.data_browser.current_window()
    assert current is not None
    assert current.label == "build_config.s3p : 1"
    assert current.data_file.source_path is None
    assert "Imported: build_config.s3p" in window.message_log.text()


def test_load_touchstone_file_types_other_formats_by_name(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    loaded = window.load_touchstone_file(IMPORT_DIR / "two_port.cti")

    assert loaded.name == "two_port.cti"
    assert loaded.network.n_freq == 3


def two_windows(qtbot: QtBot) -> MainWindow:
    """Window 1 shows the 2-port fixture, window 2 (active) the 3-port one."""

    window = MainWindow()
    qtbot.addWidget(window)
    window.load_touchstone_file(S2P)
    window.load_touchstone_file(IMPORT_DIR / "three_port.s3p")
    return window


def test_selecting_a_window_in_the_browser_shows_its_data(qtbot: QtBot) -> None:
    window = two_windows(qtbot)
    assert window.active_window == 2

    window.data_browser.select_window(1)

    assert window.active_window == 1
    assert window.parameter_format.file_value.text() == "valid_2port_ri.s2p"
    assert window.parameter_format.ports_value.text() == "2"
    assert window.plot_widget.model.title == "valid_2port_ri.s2p"
    loaded = window.loaded_measurement
    assert loaded is not None and loaded.network.n_ports == 2
    assert window.windowTitle() == (
        "Interconnect Studio - [valid_2port_ri.s2p - Frequency Domain (Single-Ended) : 1]"
    )


def test_each_window_keeps_its_own_grid_and_traces(qtbot: QtBot) -> None:
    window = two_windows(qtbot)
    window.show_window(1)
    window.set_grid(2, 2)
    window.add_trace(0, 1, "log_mag")

    window.show_window(2)

    assert window.view_area.layout_model.n_cells == 1
    assert window.layout_actions[(1, 1)].isChecked() is True
    assert trace_names(window) == ["S11 Log Mag", "S21 Log Mag"]

    window.show_window(1)

    assert window.view_area.layout_model.n_cells == 4
    assert window.layout_actions[(2, 2)].isChecked() is True
    assert trace_names(window) == ["S11 Log Mag", "S21 Log Mag", "S12 Log Mag"]


def test_each_window_keeps_its_selected_cell(qtbot: QtBot) -> None:
    window = two_windows(qtbot)
    window.set_grid(1, 2)
    window.view_area.set_current_index(1)

    window.show_window(1)
    assert window.view_area.current_index == 0
    window.show_window(2)

    assert window.view_area.current_index == 1


def test_adding_a_trace_goes_to_the_selected_cell(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_touchstone_file(S2P)
    window.set_grid(1, 2)

    window.view_area.set_current_index(1)
    assert trace_names(window) == []
    window.add_trace(1, 0, "phase")

    assert window.view_area.plot_widget_at(1).model.n_traces == 1
    assert window.view_area.plot_widget_at(0).model.n_traces == 2


def test_showing_an_unknown_window_is_an_error(qtbot: QtBot) -> None:
    window = two_windows(qtbot)

    with pytest.raises(InputValidationError, match="not open"):
        window.show_window(9)


def test_clicking_a_window_row_switches_the_display(qtbot: QtBot) -> None:
    window = two_windows(qtbot)
    window.show()
    tree = window.data_browser.tree
    index = window.data_browser.model.index_of_window(1)
    viewport = tree.viewport()
    assert viewport is not None

    qtbot.mouseClick(viewport, Qt.MouseButton.LeftButton, pos=tree.visualRect(index).center())

    assert window.active_window == 1
    assert window.parameter_format.file_value.text() == "valid_2port_ri.s2p"


def test_close_view_of_the_active_window_shows_the_newest_left(qtbot: QtBot) -> None:
    window = two_windows(qtbot)
    window.load_touchstone_file(S2P)
    window.data_browser.select_window(2)

    window.close_view(2)

    assert [w.number for w in window.data_browser.browser_tree.windows] == [1, 3]
    assert window.active_window == 3
    assert window.data_browser.current_window().number == 3
    assert window.windowTitle().endswith(": 3]")


def test_close_view_of_another_window_keeps_the_active_one(qtbot: QtBot) -> None:
    window = two_windows(qtbot)

    window.close_view(1)

    assert window.active_window == 2
    assert window.data_browser.current_window().number == 2
    assert window.parameter_format.ports_value.text() == "3"


def test_closing_every_window_clears_the_view(qtbot: QtBot) -> None:
    window = two_windows(qtbot)
    file_id = window.data_browser.browser_tree.window(2).data_file.id

    window.close_file(file_id)
    window.close_view(1)

    assert window.data_browser.browser_tree.windows == ()
    assert window.active_window is None
    assert window.loaded_measurement is None
    assert window.windowTitle() == "Interconnect Studio"
    assert window.add_trace_action.isEnabled() is False
    assert window.view_area.current_plot.traces == ()
    with pytest.raises(InputValidationError, match="Import a file"):
        window.add_trace(0, 0, "log_mag")


def test_rename_file_updates_browser_title_summary_and_plot(qtbot: QtBot) -> None:
    window = two_windows(qtbot)
    file_id = window.data_browser.browser_tree.window(1).data_file.id

    window.rename_file(file_id, "channel")

    assert window.data_browser.browser_tree.window(1).label == "channel : 1"
    assert window.active_window == 2
    window.data_browser.select_window(1)
    assert window.parameter_format.file_value.text() == "channel"
    assert window.view_area.current_plot.title == "channel"
    assert "[channel - " in window.windowTitle()


def test_rename_file_of_the_active_window_keeps_added_traces(qtbot: QtBot) -> None:
    window = two_windows(qtbot)
    window.add_trace(2, 0, "log_mag")
    file_id = window.data_browser.browser_tree.window(2).data_file.id

    window.rename_file(file_id, "dut")

    assert window.parameter_format.file_value.text() == "dut"
    assert "S31" in " ".join(trace_names(window))
    assert window.data_browser.current_window().number == 2


def test_rename_file_rejects_an_empty_name(qtbot: QtBot) -> None:
    window = two_windows(qtbot)
    file_id = window.data_browser.browser_tree.window(1).data_file.id

    with pytest.raises(InputValidationError):
        window.rename_file(file_id, "  ")

    assert window.data_browser.browser_tree.window(1).data_file.name == "valid_2port_ri.s2p"


def test_browser_window_menu_requests_reach_the_main_window(qtbot: QtBot) -> None:
    window = two_windows(qtbot)
    browser = window.data_browser

    browser.close_view_requested.emit(1)

    assert [w.number for w in browser.browser_tree.windows] == [2]


def test_open_view_adds_a_blank_window_for_the_active_file(qtbot: QtBot) -> None:
    window = two_windows(qtbot)
    window.set_grid(1, 2)

    window.open_view(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED)

    tree = window.data_browser.browser_tree
    assert window.active_window == 3
    assert window.data_browser.current_window().number == 3
    assert tree.window(3).data_file.id == tree.window(2).data_file.id
    assert tree.window(3).label == "three_port.s3p : 3"
    assert window.view_area.layout_model.plots == ViewLayout(rows=1, cols=2).plots
    assert trace_names(window) == []
    assert window.parameter_format.ports_value.text() == "3"
    assert window.windowTitle().endswith("three_port.s3p - Frequency Domain (Single-Ended) : 3]")

    window.add_trace(0, 0, "log_mag")
    assert trace_names(window) == ["S11 Log Mag"]
    window.data_browser.select_window(2)
    assert trace_names(window) == ["S11 Log Mag", "S21 Log Mag"]


def test_file_operations_cover_windows_opened_from_a_view_type(qtbot: QtBot) -> None:
    window = two_windows(qtbot)
    window.open_view(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED)
    file_id = window.data_browser.browser_tree.window(2).data_file.id

    window.rename_file(file_id, "dut")
    assert [w.label for w in window.data_browser.browser_tree.windows] == [
        "valid_2port_ri.s2p : 1",
        "dut : 2",
        "dut : 3",
    ]

    window.close_file(file_id)
    assert [w.number for w in window.data_browser.browser_tree.windows] == [1]
    assert window.active_window == 1


def test_open_view_needs_an_active_file(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    with pytest.raises(InputValidationError, match="Import a file"):
        window.open_view(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED)


def test_open_view_rejects_unavailable_view_types(qtbot: QtBot) -> None:
    window = two_windows(qtbot)

    with pytest.raises(InputValidationError, match="not available"):
        window.open_view(ViewType.TIME_DOMAIN_SINGLE_ENDED)

    assert len(window.data_browser.browser_tree.windows) == 2


def test_clicking_a_view_type_in_the_browser_opens_a_window(qtbot: QtBot) -> None:
    window = two_windows(qtbot)
    window.show()
    qtbot.waitExposed(window)
    browser = window.data_browser
    index = browser.model.index_of_view_type(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED)
    viewport = browser.tree.viewport()
    assert viewport is not None

    qtbot.mouseClick(
        viewport, Qt.MouseButton.LeftButton, pos=browser.tree.visualRect(index).center()
    )

    assert window.active_window == 3
    assert browser.current_window().number == 3


def test_saved_templates_are_listed_under_template_view(qtbot: QtBot) -> None:
    window = two_windows(qtbot)
    window.add_trace(2, 0, "log_mag")

    template = window.save_template(2, "three port")

    model = window.data_browser.model
    index = model.index_of_template("three port")
    assert index.isValid()
    assert model.data(index) == "three port (3p)"
    assert model.parent(index) == model.index_of_category(BrowserCategory.TEMPLATE_VIEW)
    assert model.flags(model.index_of_category(BrowserCategory.TEMPLATE_VIEW))
    assert template.plots[0].traces[-1] == TraceRecipe(2, 0, "log_mag")
    assert window.active_window == 2
    assert window.data_browser.current_window().number == 2


def test_templates_saved_earlier_are_listed_at_start(
    qtbot: QtBot, template_directory: Path
) -> None:
    first = two_windows(qtbot)
    first.save_template(1, "two port")

    second = MainWindow()
    qtbot.addWidget(second)

    assert [t.name for t in second.data_browser.model.templates] == ["two port"]
    assert (template_directory / "two port.json").is_file()


def test_saving_over_an_existing_template_needs_overwrite(qtbot: QtBot) -> None:
    window = two_windows(qtbot)
    window.save_template(1, "t")

    with pytest.raises(InputValidationError, match="already exists"):
        window.save_template(2, "t")
    window.save_template(2, "t", overwrite=True)

    assert window.data_browser.model.templates[0].n_ports == 3


def test_open_template_lays_the_active_file_out_like_the_template(qtbot: QtBot) -> None:
    window = two_windows(qtbot)
    window.set_grid(1, 2)
    window.add_trace(2, 0, "log_mag")
    window.save_template(2, "layout")
    window.load_touchstone_file(IMPORT_DIR / "4port.s4p")

    template = window.data_browser.model.templates[0]
    window.open_template(template)

    tree = window.data_browser.browser_tree
    assert window.active_window == 4
    assert tree.window(4).template == "layout"
    assert tree.window(4).data_file.id == tree.window(3).data_file.id
    assert tree.windows_of_template("layout") == (tree.window(4),)
    model = window.data_browser.model
    assert model.parent(model.index_of_window(4)) == model.index_of_template("layout")
    assert window.view_area.layout_model.cols == 2
    assert trace_names(window) == ["S11 Log Mag", "S21 Log Mag", "S31 Log Mag"]
    assert window.view_area.current_plot.title == "4port.s4p"
    assert window.windowTitle().endswith("[4port.s4p - layout : 4]")


def test_open_template_needs_the_ports_it_uses(qtbot: QtBot) -> None:
    window = two_windows(qtbot)
    window.add_trace(2, 0, "log_mag")
    window.save_template(2, "three port")
    window.data_browser.select_window(1)

    with pytest.raises(InputValidationError, match="needs 3 ports"):
        window.open_template(window.data_browser.model.templates[0])

    assert len(window.data_browser.browser_tree.windows) == 2


def test_open_template_needs_an_active_file(qtbot: QtBot) -> None:
    window = two_windows(qtbot)
    window.save_template(1, "t")
    template = window.data_browser.model.templates[0]
    window.close_view(1)
    window.close_view(2)

    with pytest.raises(InputValidationError, match="Import a file"):
        window.open_template(template)


def test_clicking_a_template_in_the_browser_opens_it(qtbot: QtBot) -> None:
    window = two_windows(qtbot)
    window.save_template(2, "t")
    window.show()
    qtbot.waitExposed(window)
    browser = window.data_browser
    index = browser.model.index_of_template("t")
    browser.tree.scrollTo(index)
    viewport = browser.tree.viewport()
    assert viewport is not None

    qtbot.mouseClick(
        viewport, Qt.MouseButton.LeftButton, pos=browser.tree.visualRect(index).center()
    )

    assert window.active_window == 3
    assert browser.browser_tree.window(3).template == "t"


def test_save_template_request_from_the_window_menu(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = two_windows(qtbot)
    monkeypatch.setattr(QInputDialog, "getText", lambda *args: ("from menu", True))
    menu = window.data_browser.window_menu(window.data_browser.browser_tree.window(1))
    action = menu.findChild(QAction, "save_template_as")
    assert action is not None

    action.trigger()

    assert [t.name for t in window.data_browser.model.templates] == ["from menu"]
    assert window.data_browser.model.templates[0].n_ports == 2


def test_replacing_a_template_from_the_menu_asks_first(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = two_windows(qtbot)
    window.save_template(1, "t")
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.No)

    window.data_browser.save_template_requested.emit(2, "t")

    assert window.data_browser.model.templates[0].n_ports == 2


def _balanced_import() -> ImportedNetwork:
    imported = ImportService().import_single(
        IMPORT_DIR / "4port.s4p", ImportFileType.TOUCHSTONE
    )
    return replace(imported, port_group=DEFAULT_FOUR_PORT_TOPOLOGY.port_group)


def test_balanced_view_shows_the_mixed_mode_grid(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window.open_imported(_balanced_import(), ViewType.FREQUENCY_DOMAIN_BALANCED)

    panel = window.parameter_format
    assert panel.is_mixed_mode is True
    labels = [button.text() for button in panel._parameter_buttons.buttons()]
    assert labels[:4] == ["SDD11", "SDD12", "SDC11", "SDC12"]


def test_single_ended_view_keeps_the_plain_grid(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window.open_imported(_balanced_import(), ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED)

    assert window.parameter_format.is_mixed_mode is False
    assert window.parameter_format.n_ports == 4


def test_balanced_view_adds_a_mixed_mode_trace(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.open_imported(_balanced_import(), ViewType.FREQUENCY_DOMAIN_BALANCED)
    panel = window.parameter_format
    index = [choice.label for choice in panel._choices].index("SCD21")
    panel._parameter_buttons.button(index).setChecked(True)

    panel.add_button.click()

    assert window.plot_widget.model.traces[-1].name == "SCD21 Log Mag"


def test_mixed_mode_without_a_topology_is_reported(qtbot: QtBot) -> None:
    """Without a DUT configuration there is no way to know which ports pair up."""

    window = MainWindow()
    qtbot.addWidget(window)
    imported = ImportService().import_single(
        IMPORT_DIR / "4port.s4p", ImportFileType.TOUCHSTONE
    )
    window.open_imported(imported, ViewType.FREQUENCY_DOMAIN_BALANCED)
    choice = ParameterChoice("SDD21", 1, 0, Mode.DIFFERENTIAL, Mode.DIFFERENTIAL)

    window._on_add_trace_requested(choice, "log_mag")

    assert "DUT configuration" in window.message_log.text()
