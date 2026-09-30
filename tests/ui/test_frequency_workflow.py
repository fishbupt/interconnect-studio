"""Frequency controls, provenance and project integration."""

import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
from PyQt6.QtCore import QItemSelectionModel
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox
from pytestqt.qtbot import QtBot

from interconnect_studio.core import InputValidationError
from interconnect_studio.io import read_project
from interconnect_studio.services.frequency_analysis import add_marker, marker_reading, set_delta
from interconnect_studio.ui import MainWindow
from interconnect_studio.ui.dialogs.trace_data_dialog import TraceDataDialog, TraceTableModel

DATA = Path(__file__).parents[1] / "data"


def window(qtbot: QtBot) -> MainWindow:
    result = MainWindow()
    qtbot.addWidget(result)
    result.load_touchstone_file(DATA / "import/2port.s2p")
    return result


def test_marker_controls_drag_readout_delete_and_reorder(qtbot: QtBot) -> None:
    app = window(qtbot)
    flow = app.frequency_flow
    panel = flow.panel
    flow._execute("add_marker")
    assert len(app.plot_widget.model.markers) == 1
    number = panel.marker_combo.currentData()
    panel.position_edit.setText("1000000000")
    flow._execute("move")
    assert "M1:" in panel.readout.text()
    assert app.file_flow.dirty
    line = app.plot_widget.marker_lines[number]
    line.setValue(2e9)
    line.sigPositionChangeFinished.emit(line)
    assert app.plot_widget.model.markers[0].x == 2e9
    panel.rename_edit.setText("参考曲线")
    flow._execute("rename")
    assert app.plot_widget.model.traces[0].name == "参考曲线"
    flow._execute("down")
    assert app.plot_widget.model.markers[0].trace_index == 1
    flow._execute("delete_trace")
    assert not app.plot_widget.model.markers


def test_delta_and_markers_restore_in_their_own_grid_cells(qtbot: QtBot, tmp_path: Path) -> None:
    app = window(qtbot)
    first = add_marker(add_marker(app.plot_widget.model, 0, 1e9), 1, 2e9)
    app.frequency_flow.apply(set_delta(first, 2, 1))
    expected = marker_reading(app.plot_widget.model, app.plot_widget.model.markers[1])
    app.set_grid(1, 2)
    app.view_area.set_current_index(1)
    app.new_plot(1, 0, "phase")
    app.frequency_flow._execute("add_marker")
    app.view_area.set_current_index(0)
    assert len(app.frequency_flow.panel._plot.markers) == 2
    path = app.file_flow.save_project(tmp_path / "markers.icproj")
    restored = MainWindow()
    qtbot.addWidget(restored)
    restored.file_flow.load_project(path)
    assert len(restored.plot_widget.model.markers) == 2
    assert (
        marker_reading(restored.plot_widget.model, restored.plot_widget.model.markers[1])
        == expected
    )
    restored.view_area.set_current_index(1)
    assert len(restored.plot_widget.model.markers) == 1
    assert not restored.file_flow.dirty


def test_legacy_version_one_project_without_markers_still_opens(
    qtbot: QtBot, tmp_path: Path
) -> None:
    app = window(qtbot)
    path = app.file_flow.save_project(tmp_path / "legacy.icproj")
    with zipfile.ZipFile(path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    document = json.loads(entries["manifest.json"])
    document["version"] = 1
    for saved in document["windows"]:
        for plot in saved["plots"]:
            plot.pop("markers")
    entries["manifest.json"] = json.dumps(document).encode()
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    app.file_flow.load_project(path)
    assert app.plot_widget.model.traces and not app.plot_widget.model.markers


def test_cross_file_overlay_survives_recall_and_source_closing_removes_dependants(
    qtbot: QtBot, tmp_path: Path
) -> None:
    app = window(qtbot)
    first_id = app.data_browser.browser_tree.window(1).data_file.id
    before = app.plot_widget.model.traces[1].y.copy()
    app.load_touchstone_file(DATA / "touchstone/valid_2port_ri.s2p")
    app.frequency_flow.compare_from_window(1, 1)
    overlay = app.plot_widget.model.traces[-1]
    assert overlay.source_id == first_id
    np.testing.assert_array_equal(overlay.y, before)
    app.frequency_flow.panel.trace_combo.setCurrentIndex(2)
    app.frequency_flow._execute("add_marker")
    path = app.file_flow.save_project(tmp_path / "compare.icproj")
    snapshot = read_project(path)
    assert len(snapshot.files) == 2
    restored = MainWindow()
    qtbot.addWidget(restored)
    restored.file_flow.load_project(path)
    restored.show_window(2)
    assert restored.plot_widget.model.traces[-1].source_id == first_id
    with pytest.raises(InputValidationError):
        restored.save_template(2, "comparison")
    restored.close_file(first_id)
    assert restored.active_window == 2
    assert len(restored.plot_widget.model.traces) == 2
    assert not restored.plot_widget.model.markers
    restored.file_flow.save_project(tmp_path / "after_close.icproj")


def test_compare_rejects_different_formats_without_replacing_plot(qtbot: QtBot) -> None:
    app = window(qtbot)
    app.new_plot(0, 0, "phase")
    app.load_touchstone_file(DATA / "touchstone/valid_2port_ri.s2p")
    previous = app.plot_widget.model
    with pytest.raises(InputValidationError):
        app.frequency_flow.compare_from_window(1, 0)
    assert app.plot_widget.model is previous


def test_data_table_is_virtual_and_copy_selection_has_correct_cells(qtbot: QtBot) -> None:
    app = window(qtbot)
    dialog = TraceDataDialog(app.plot_widget.model, app.frequency_flow.sources())
    qtbot.addWidget(dialog)
    model = dialog.model
    assert model.rowCount() == sum(t.n_points for t in app.plot_widget.model.traces)
    second_start = app.plot_widget.model.traces[0].n_points
    assert model.data(model.index(second_start, 0)) == "S21 Log Mag"
    selection = dialog.table.selectionModel()
    selection.select(model.index(0, 2), QItemSelectionModel.SelectionFlag.Select)
    selection.select(model.index(0, 4), QItemSelectionModel.SelectionFlag.Select)
    dialog.copy_selection()
    clipboard = QApplication.clipboard()
    assert clipboard.text().split("\t") == [
        model.data(model.index(0, 2)),
        "",
        model.data(model.index(0, 4)),
    ]
    assert TraceTableModel(app.plot_widget.model, {}).plot is app.plot_widget.model


def test_csv_export_runs_background_and_does_not_mark_project_dirty(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = window(qtbot)
    app.file_flow.save_project(tmp_path / "saved.icproj")
    output = tmp_path / "traces.csv"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_args: (str(output), ""))
    app.frequency_flow._execute("csv")
    assert output.read_text(encoding="utf-8-sig").startswith("Trace,Source ID,Source")
    assert not app.file_flow.dirty
    assert app.tasks.wait_for_done()


def test_actual_csv_suffix_overwrite_refusal_keeps_original(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = window(qtbot)
    output = tmp_path / "traces.csv"
    output.write_text("old")
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *_args: (str(output.with_suffix(".txt")), "")
    )
    monkeypatch.setattr(QMessageBox, "question", lambda *_args: QMessageBox.StandardButton.No)
    app.frequency_flow._execute("csv")
    assert output.read_text() == "old"


def test_plot_png_has_requested_resolution_and_clipboard_image(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = window(qtbot)
    app.show()
    qtbot.waitExposed(app)
    app.frequency_flow._execute("add_marker")
    image = app.plot_widget.image(960)
    assert not image.isNull() and image.width() == 960
    output = tmp_path / "plot.png"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_args: (str(output), ""))
    monkeypatch.setattr(QInputDialog, "getInt", lambda *_args: (640, True))
    app.frequency_flow._execute("image")
    assert QImage(str(output)).width() == 640
    app.frequency_flow._execute("copy_image")
    assert not QApplication.clipboard().image().isNull()


def test_autoscale_all_enables_both_axes_and_empty_workspace_actions_disable(qtbot: QtBot) -> None:
    app = window(qtbot)
    app.set_grid(1, 2)
    for cell in (0, 1):
        app.view_area.plot_widget_at(cell).plot_widget.setRange(xRange=(1, 2), yRange=(0, 1))
    app.frequency_flow._execute("autoscale_all")
    assert app.view_area.plot_autorange() == ((True, True), (True, True))
    app.file_flow.close_all()
    assert all(not action.isEnabled() for action in app.frequency_flow.actions.values())


def test_marker_keyboard_moves_one_measured_point(qtbot: QtBot) -> None:
    from PyQt6.QtCore import Qt

    app = window(qtbot)
    app.show()
    app.frequency_flow._execute("add_marker")
    panel = app.frequency_flow.panel
    panel.position_edit.setText("1000000000")
    app.frequency_flow._execute("move")
    panel.marker_combo.setFocus()
    qtbot.waitUntil(panel.marker_combo.hasFocus)
    qtbot.keyClick(panel.marker_combo, Qt.Key.Key_Right)
    assert app.plot_widget.model.markers[0].x == 2e9
    qtbot.keyClick(panel.marker_combo, Qt.Key.Key_Left)
    assert app.plot_widget.model.markers[0].x == 1e9


def test_closing_source_marks_inactive_comparison_dirty_and_cancel_preserves_it(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = window(qtbot)
    source_id = app.data_browser.browser_tree.window(1).data_file.id
    app.load_touchstone_file(DATA / "touchstone/valid_2port_ri.s2p")
    comparison_id = app.data_browser.browser_tree.window(2).data_file.id
    app.frequency_flow.compare_from_window(1, 1)
    app.load_touchstone_file(DATA / "import/2port.s2p")
    app.file_flow.save_project(tmp_path / "three.icproj")
    app.close_file(source_id)
    assert app.active_window == 3
    monkeypatch.setattr(QMessageBox, "question", lambda *_args: QMessageBox.StandardButton.Cancel)
    app.file_flow.request_close_file(comparison_id)
    assert len(app.data_browser.browser_tree.windows_of_file(comparison_id)) == 1
    monkeypatch.setattr(QMessageBox, "question", lambda *_args: QMessageBox.StandardButton.Discard)


def test_closing_one_source_view_retains_comparison_until_last_view_closes(qtbot: QtBot) -> None:
    from interconnect_studio.core import ViewType

    app = window(qtbot)
    source_id = app.data_browser.browser_tree.window(1).data_file.id
    app.open_view(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED)
    app.load_touchstone_file(DATA / "touchstone/valid_2port_ri.s2p")
    app.frequency_flow.compare_from_window(1, 1)
    app.close_view(1)
    assert len(app.plot_widget.model.traces) == 3
    assert app.plot_widget.model.traces[-1].source_id == source_id
    app.close_view(2)
    assert len(app.plot_widget.model.traces) == 2
