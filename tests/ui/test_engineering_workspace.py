"""PLTS analysis controls, range restoration and removed comparison entry points."""

from pathlib import Path

import numpy as np
from PyQt6.QtWidgets import QPushButton, QTabWidget
from pytestqt.qtbot import QtBot

from interconnect_studio.ui import MainWindow
from interconnect_studio.ui.theme import Theme, palette_for

DATA = Path(__file__).parents[1] / "data"


def test_workspace_has_analysis_controls_without_file_comparison(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    assert not window.workspace.findChildren(QTabWidget)
    assert not hasattr(window.workspace, "open_comparison")
    assert "compare" not in window.frequency_flow.actions
    assert not hasattr(window.frequency_flow, "compare_from_window")
    assert all(
        "比较" not in button.text() and "对比" not in button.text()
        for button in window.findChildren(QPushButton)
    )
    window.load_touchstone_file(DATA / "import/2port.s2p")
    assert window.workspace.export_button.isEnabled()
    assert window.workspace.table_button.isEnabled()
    assert (window.view_area.layout_model.rows, window.view_area.layout_model.cols) == (2, 2)


def test_single_file_style_is_stable_after_theme_switch(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_touchstone_file(DATA / "import/2port.s2p")
    window.add_trace(1, 0, "log_mag")
    for theme in (Theme.LIGHT, Theme.DARK, Theme.LIGHT):
        window.set_theme(theme)
        widget = window.plot_widget
        assert widget._trace_style(0, palette_for(theme)) == widget._trace_style(
            1, palette_for(theme)
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
