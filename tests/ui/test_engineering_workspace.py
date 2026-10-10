"""Viewer/comparison independence, input invalidation and display range state."""

from pathlib import Path

import numpy as np
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog
from pytestqt.qtbot import QtBot

from interconnect_studio.ui import MainWindow
from interconnect_studio.ui.theme import Theme, palette_for

DATA = Path(__file__).parents[1] / "data"


def compared_window(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_touchstone_file(DATA / "touchstone/valid_2port_ri.s2p")
    window.load_touchstone_file(DATA / "import/2port.s2p")
    window.show_window(1)
    window.workspace.open_comparison()
    page = window.workspace.comparison
    assert page.a_combo.currentData() == "file-1"
    assert page.b_combo.currentData() is None
    page.b_combo.setCurrentIndex(page.b_combo.findData("file-2"))
    page.show_comparison()
    return window


def test_comparison_does_not_change_viewer_and_survives_unrelated_files(qtbot: QtBot) -> None:
    window = compared_window(qtbot)
    page = window.workspace.comparison
    before = window.view_area.layout_model
    overlay = page.area.layout_model
    assert all(plot.n_traces == 2 for plot in overlay.plots)
    assert all(plot.n_traces == 1 for plot in before.plots)
    window.workspace.tabs.setCurrentIndex(0)
    window.load_touchstone_file(DATA / "import/2port.s2p")
    window.close_file("file-3")
    assert page.area.layout_model is overlay
    assert (page.a_combo.currentData(), page.b_combo.currentData()) == ("file-1", "file-2")
    window.show_window(1)
    assert window.view_area.layout_model.plots[0].traces[0].name == "S11 Log Mag"
    window.close_file("file-2")
    assert page.b_combo.currentData() is None
    assert not page.area.current_plot.traces
    assert not page.csv_button.isEnabled()


def test_same_source_is_rejected_and_swap_invalidates_old_export(qtbot: QtBot) -> None:
    window = compared_window(qtbot)
    page = window.workspace.comparison
    assert page.csv_button.isEnabled()
    page.swap()
    assert (page.a_combo.currentData(), page.b_combo.currentData()) == ("file-2", "file-1")
    assert not page.csv_button.isEnabled()
    assert not page.area.current_plot.traces
    page.b_combo.setCurrentIndex(page.b_combo.findData("file-2"))
    assert not page.compare_button.isEnabled()
    page.show_comparison()
    assert "不同" in page.note.text()


def test_comparison_ranges_are_per_format_and_menu_export_uses_comparison(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = compared_window(qtbot)
    page = window.workspace.comparison
    page.area.current_plot_widget.plot_widget.setYRange(-40, 0, padding=0)
    page.format_combo.setCurrentIndex(page.format_combo.findData("phase"))
    assert not page.csv_button.isEnabled()
    page.show_comparison()
    page.area.current_plot_widget.plot_widget.setYRange(-180, 180, padding=0)
    page.format_combo.setCurrentIndex(page.format_combo.findData("log_mag"))
    page.show_comparison()
    np.testing.assert_allclose(page.area.plot_ranges()[0][2:], [-40, 0])
    destination = tmp_path / "overlay.csv"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_: (str(destination), ""))
    window.frequency_flow._execute("csv")
    content = destination.read_text(encoding="utf-8-sig")
    assert "file-1" in content and "file-2" in content


def test_single_file_style_and_comparison_roles_are_stable_after_theme_switch(qtbot: QtBot) -> None:
    window = compared_window(qtbot)
    page = window.workspace.comparison
    for theme in (Theme.LIGHT, Theme.DARK, Theme.LIGHT):
        window.set_theme(theme)
        styles = [
            page.area.current_plot_widget._trace_style(i, palette_for(theme)) for i in range(2)
        ]
        assert styles[0][1] is Qt.PenStyle.SolidLine
        assert styles[1][1] is Qt.PenStyle.DashLine
        assert styles[0][0] != styles[1][0]
    window.workspace.tabs.setCurrentIndex(0)
    window.add_trace(1, 0, "log_mag")
    widget = window.plot_widget
    assert widget._trace_style(0, palette_for(Theme.LIGHT)) == widget._trace_style(
        1, palette_for(Theme.LIGHT)
    )


def test_manual_y_bounds_reject_nonfinite_and_viewer_formats_recover_own_range(
    qtbot: QtBot,
) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_touchstone_file(DATA / "import/2port.s2p")
    axis = window.workspace.axis
    before = window.view_area.plot_ranges()[0]
    axis.minimum.setText("nan")
    axis.maximum.setText("10")
    axis.apply()
    assert "有限" in axis.error.text()
    assert window.view_area.plot_ranges()[0] == before
    window.plot_widget.plot_widget.setYRange(-50, 0, padding=0)
    window.new_plot(0, 0, "phase")
    window.plot_widget.plot_widget.setYRange(-180, 180, padding=0)
    window.new_plot(0, 0, "log_mag")
    np.testing.assert_allclose(window.view_area.plot_ranges()[0][2:], [-50, 0])
    window.load_touchstone_file(DATA / "touchstone/valid_2port_ri.s2p")
    window.show_window(1)
    window.new_plot(0, 0, "phase")
    np.testing.assert_allclose(window.view_area.plot_ranges()[0][2:], [-180, 180])


def test_saving_while_comparing_recalls_viewer_docks_and_original_plots(
    qtbot: QtBot, tmp_path: Path
) -> None:
    window = compared_window(qtbot)
    assert window.parameter_format_dock.isHidden()
    path = window.file_flow.save_project(tmp_path / "viewer.icproj")
    restored = MainWindow()
    qtbot.addWidget(restored)
    restored.file_flow.load_project(path)
    assert restored.workspace.tabs.currentIndex() == 0
    assert not restored.parameter_format_dock.isHidden()
    assert not restored.data_browser_dock.isHidden()
    assert all(plot.n_traces == 1 for plot in restored.view_area.layout_model.plots)
    assert restored.workspace._comparison is None


def test_rename_updates_comparison_labels_without_rebuilding_data(qtbot: QtBot) -> None:
    window = compared_window(qtbot)
    page = window.workspace.comparison
    values = page.area.current_plot.traces[0].y.copy()
    window.rename_file("file-1", "reference.s2p")
    assert page.csv_button.isEnabled()
    assert page.area.current_plot.traces[0].name == "A · reference.s2p"
    np.testing.assert_array_equal(page.area.current_plot.traces[0].y, values)
