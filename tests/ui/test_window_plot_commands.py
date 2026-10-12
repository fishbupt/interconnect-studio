"""Window and plot lifecycle, including files with no open views."""

from pathlib import Path

import pytest
from PyQt6 import sip
from PyQt6.QtCore import QEvent, QMimeData, QPoint, QPointF, Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from interconnect_studio.core import InputValidationError, ViewType
from interconnect_studio.services.frequency_analysis import add_marker
from interconnect_studio.ui.main_window import MainWindow

S2P = Path(__file__).parents[1] / "data/import/2port.s2p"


def test_last_view_keeps_file_export_and_reopen_after_recall(qtbot: QtBot, tmp_path: Path) -> None:
    app = MainWindow()
    qtbot.addWidget(app)
    app.load_touchstone_file(S2P)
    file_id = app._active_file_id
    app.file_flow.request_close_view(1)
    assert app.active_window is None
    assert file_id in app._files
    assert app.file_flow.export_action.isEnabled()
    assert app.workspace.open_view_button.isEnabled()
    path = app.file_flow.save_project(tmp_path / "no-windows.icproj")
    app.file_flow.load_project(path)
    assert app.active_window is None
    assert app._active_file_id == file_id
    app.open_view(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED)
    assert app.data_browser.browser_tree.window(app.active_window).data_file.id == file_id
    app.file_flow.request_close_view(app.active_window)
    app.file_flow.close_current_file()
    assert not app.file_flow.snapshot().files
    assert not app.workspace.open_view_button.isEnabled()


def test_copy_move_rename_restore_keep_marker_and_scale(qtbot: QtBot, tmp_path: Path) -> None:
    app = MainWindow()
    qtbot.addWidget(app)
    app.load_touchstone_file(S2P)
    plot = add_marker(app.view_area.current_plot, 0, 1e9)
    app.frequency_flow.apply(plot)
    app.plot_widget.plot_widget.setYRange(-20, 5, padding=0)
    app.plot_flow.copy()
    assert app.view_area.current_plot.markers == plot.markers
    assert app.plot_widget.plot_widget.viewRange()[1] == pytest.approx([-20, 5])
    app.plot_flow.rename("copy")
    app.plot_flow.move(2)
    assert app.view_area.current_index == 3
    path = app.file_flow.save_project(tmp_path / "plots.icproj")
    app.file_flow.load_project(path)
    assert app.view_area.layout_model.plots[3].title == "copy"
    assert app.view_area.layout_model.plots[3].markers == plot.markers
    app.view_area.set_current_index(3)
    app.plot_flow.delete()
    assert not any(p.title == "copy" for p in app.view_area.layout_model.plots)
    app.plot_flow.clear()
    assert not any(p.traces for p in app.view_area.layout_model.plots)


def test_failed_new_plot_and_shrink_leave_existing_plots(qtbot: QtBot) -> None:
    app = MainWindow()
    qtbot.addWidget(app)
    app.load_touchstone_file(S2P)
    original = app.view_area.layout_model
    with pytest.raises(InputValidationError):
        app.new_plot(20, 0, "log_mag")
    assert app.view_area.layout_model is original
    with pytest.raises(InputValidationError):
        app.new_plot(0, 0, "smith")
    with pytest.raises(InputValidationError):
        app.replace_plot(0, 0, "smith")
    assert app.view_area.layout_model is original
    with pytest.raises(InputValidationError):
        app.set_grid(1, 1)
    assert app.view_area.layout_model is original


def test_header_double_click_and_reorder_preserve_grid(qtbot: QtBot) -> None:
    app = MainWindow()
    qtbot.addWidget(app)
    app.load_touchstone_file(S2P)
    area = app.view_area
    original = area.layout_model
    qtbot.mouseDClick(area._cells[0], Qt.MouseButton.LeftButton)
    assert area._maximized
    assert area.layout_model is original
    area.toggle_maximized()
    mime = QMimeData()
    mime.setData("application/x-interconnect-plot", b"0")
    enter = QDragEnterEvent(
        QPoint(2, 2),
        Qt.DropAction.MoveAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(area._cells[3], enter)
    assert enter.isAccepted()
    drop = QDropEvent(
        QPointF(2, 2),
        Qt.DropAction.MoveAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(area._cells[3], drop)
    assert drop.isAccepted()
    assert area.layout_model.plots[3] is original.plots[0]


def test_resize_remaps_scale_and_selection_by_grid_position(qtbot: QtBot) -> None:
    app = MainWindow()
    qtbot.addWidget(app)
    app.load_touchstone_file(S2P)
    # Remove the right column deliberately before shrinking.
    app.view_area.set_current_index(3)
    app.plot_flow.delete()
    app.view_area.set_current_index(1)
    app.plot_flow.delete()
    # Compaction leaves two plots in the first row; enlarge before moving one down.
    app.plot_flow.reorder(1, 2)
    app.view_area.set_current_index(2)
    app.plot_widget.plot_widget.setYRange(-42, -5, padding=0)
    app.set_grid(2, 1)
    assert app.view_area.current_index == 1
    assert app.plot_widget.plot_widget.viewRange()[1] == pytest.approx([-42, -5])


def test_rebuild_keeps_old_cells_owned_and_deleted_filters_are_safe(qtbot: QtBot) -> None:
    from interconnect_studio.ui.views import PlotViewArea

    area = PlotViewArea()
    qtbot.addWidget(area)
    old_frame = area._cells[0]
    area.set_grid(2, 2)
    assert old_frame.parent() is area
    sip.delete(area)
    assert sip.isdeleted(old_frame)
    assert not area.eventFilter(None, QEvent(QEvent.Type.User))
