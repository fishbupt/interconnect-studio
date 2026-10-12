"""Multi-window interaction routes commands to the window the user actually selected."""

from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from pytestqt.qtbot import QtBot

from interconnect_studio.core import ViewType
from interconnect_studio.services.frequency_analysis import add_marker
from interconnect_studio.ui import MainWindow
from interconnect_studio.ui.theme import Theme

S2P = Path(__file__).parents[1] / "data/import/2port.s2p"


def open_pair(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window.load_touchstone_file(S2P)
    window.load_touchstone_file(S2P)
    return window


def test_menu_activation_and_native_activation_keep_independent_plots(qtbot: QtBot) -> None:
    window = open_pair(qtbot)
    flow = window.window_flow
    first, second = flow.windows[1], flow.windows[2]
    assert first.area is not second.area
    original = first.area.current_plot_widget
    flow.window_actions[1].trigger()
    assert window.active_window == 1
    window.frequency_flow.apply(add_marker(window.view_area.current_plot, 0, 1e9))
    flow.mdi.setActiveSubWindow(second)
    qtbot.waitUntil(lambda: window.active_window == 2)
    assert not window.view_area.current_plot.markers
    assert flow.window_actions[2].isChecked()
    assert not flow.window_actions[1].isChecked()
    flow.window_actions[1].trigger()
    assert window.plot_widget is original
    assert window.view_area.current_plot.markers
    window.rename_file(window._active_file_id, "renamed")
    assert "renamed" in flow.window_actions[1].text()
    assert "renamed" in first.windowTitle()


def test_tile_cascade_resize_and_window_states(qtbot: QtBot) -> None:
    window = open_pair(qtbot)
    flow = window.window_flow
    flow.actions["tile"].trigger()
    qtbot.wait(30)
    first, second = flow.windows[1], flow.windows[2]
    assert not first.geometry().intersects(second.geometry())
    assert flow.mdi.viewport().rect().contains(first.geometry())
    assert flow.mdi.viewport().rect().contains(second.geometry())
    assert window.active_window == 2
    flow.actions["cascade"].trigger()
    assert first.pos() != second.pos()
    assert first.geometry().intersects(second.geometry())
    first.resize(550, 410)
    first.move(12, 14)
    assert first.size().width() == 550
    assert first.pos().x() == 12
    flow.actions["maximize"].trigger()
    assert second.isMaximized()
    flow.actions["restore"].trigger()
    assert not second.isMaximized()
    flow.actions["minimize"].trigger()
    assert second.isMinimized()
    flow.window_actions[2].trigger()
    assert not second.isMinimized()
    assert window.active_window == 2


def test_float_dock_and_arrange_keep_the_same_canvas(qtbot: QtBot) -> None:
    window = open_pair(qtbot)
    flow = window.window_flow
    frame = flow.windows[2]
    area = frame.area
    area.current_plot_widget.plot_widget.setYRange(-45, -5, padding=0)
    flow.actions["float"].trigger()
    assert frame.floating
    assert frame.surface.isWindow()
    assert frame.mdiArea() is None
    assert frame.area.parentWidget() is frame.surface
    frame.surface.resize(640, 480)
    window.workspace.axis.minimum.setText("-60")
    window.workspace.axis.maximum.setText("-10")
    window.workspace.axis.apply()
    assert area.plot_ranges()[0][2:] == pytest.approx((-60, -10))
    window.set_theme(Theme.DARK)
    assert all(item.area.theme is Theme.DARK for item in flow.windows.values())
    flow.actions["tile"].trigger()
    assert not frame.floating
    assert frame.mdiArea() is flow.mdi
    assert frame.area is area
    assert frame.area.parentWidget() is frame
    assert frame.area.isVisibleTo(frame)
    assert window.active_window == 2
    assert area.plot_ranges()[0][2:] == pytest.approx((-60, -10))


def test_native_close_and_close_menu_release_only_views(qtbot: QtBot) -> None:
    window = open_pair(qtbot)
    flow = window.window_flow
    assert len(window._files) == 2
    flow.windows[1].close()
    assert set(flow.windows) == {2}
    assert set(window._sessions) == {2}
    assert len(window._files) == 2
    flow.toggle_floating(2)
    flow.windows[2].surface.close()
    assert not flow.windows
    assert not window._sessions
    assert len(window._files) == 2
    assert not any(action.isEnabled() for action in flow.actions.values())
    window.open_view(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED)
    assert len(flow.windows) == 1
    flow.actions["close"].trigger()
    assert not flow.windows


def test_inactive_and_floating_scales_are_saved_and_all_views_recreated(
    qtbot: QtBot, tmp_path: Path
) -> None:
    window = open_pair(qtbot)
    flow = window.window_flow
    flow.windows[1].area.plot_widget_at(0).plot_widget.setYRange(-31, -7, padding=0)
    flow.toggle_floating(2)
    flow.windows[2].area.plot_widget_at(0).plot_widget.setYRange(-71, -27, padding=0)
    path = window.file_flow.save_project(tmp_path / "multi.icproj")
    window.file_flow.load_project(path)
    assert len(flow.windows) == 2
    assert len(flow.mdi.subWindowList()) == 2
    assert not any(frame.floating for frame in flow.windows.values())
    assert flow.windows[1].area.plot_ranges()[0][2:] == pytest.approx((-31, -7))
    assert flow.windows[2].area.plot_ranges()[0][2:] == pytest.approx((-71, -27))
    flow.actions["tile"].trigger()
    flow.window_actions[2].trigger()
    assert window.view_area is flow.windows[2].area
    assert window.workspace.axis.area is window.view_area
    assert len(window.view_area.current_plot.traces) == 1


def test_plot_commands_and_marker_drag_target_the_clicked_window(qtbot: QtBot) -> None:
    window = open_pair(qtbot)
    flow = window.window_flow
    window.frequency_flow.apply(add_marker(window.view_area.current_plot, 0, 1e9))
    second_plot = flow.windows[2].area.current_plot
    flow.actions["tile"].trigger()
    qtbot.mouseClick(flow.windows[1].area._cells[1], Qt.MouseButton.LeftButton)
    assert window.active_window == 1
    window.plot_flow.rename("first window plot")
    assert flow.windows[1].area.layout_model.plots[1].title == "first window plot"
    assert flow.windows[2].area.current_plot is second_plot
    flow.windows[2].area.marker_moved.emit(0, 1, 2e9)
    assert window.active_window == 2
    assert window.view_area.current_plot.markers[0].x == 2e9
    assert not flow.windows[1].area.current_plot.markers


def test_native_minimize_is_not_undone_by_activation_callbacks(qtbot: QtBot) -> None:
    window = open_pair(qtbot)
    flow = window.window_flow
    frame = flow.windows[2]
    frame.showMinimized()
    qtbot.wait(20)
    assert frame.isMinimized()
    flow.window_actions[2].trigger()
    assert not frame.isMinimized()
    frame.showMaximized()
    assert frame.isMaximized()
    flow.toggle_floating(2)
    frame.surface.showMinimized()
    qtbot.wait(20)
    assert frame.surface.isMinimized()
    flow.window_actions[2].trigger()
    assert not frame.surface.isMinimized()
    flow.actions["maximize"].trigger()
    assert frame.surface.isMaximized()
    flow.actions["restore"].trigger()
    assert not frame.surface.isMaximized()


def test_cancelled_exit_keeps_floating_windows_and_accepted_exit_closes_them(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = open_pair(qtbot)
    flow = window.window_flow
    flow.toggle_floating(2)
    surface = flow.windows[2].surface
    monkeypatch.setattr(window.file_flow, "confirm_discard", lambda: False)
    window.close()
    assert surface.isVisible()
    assert len(flow.windows) == 2
    monkeypatch.setattr(window.file_flow, "confirm_discard", lambda: True)
    window.close()
    assert not surface.isVisible()
    assert not flow.windows
