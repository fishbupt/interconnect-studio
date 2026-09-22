import pytest
from pytestqt.qtbot import QtBot

from interconnect_studio.core import PlotModel, PlotTrace, Trace, ViewLayout
from interconnect_studio.ui.theme import Theme
from interconnect_studio.ui.views import PlotViewArea


def plot(name: str) -> PlotModel:
    trace = Trace(name, [1.0, 2.0], [1.0, 2.0], x_unit="Hz", y_unit="dB")
    return PlotModel(entries=(PlotTrace(trace),), title=name)


def test_defaults_to_single_cell(qtbot: QtBot) -> None:
    area = PlotViewArea()
    qtbot.addWidget(area)

    assert area.layout_model.n_cells == 1
    assert area.current_index == 0


def test_set_grid_creates_one_widget_per_cell(qtbot: QtBot) -> None:
    area = PlotViewArea()
    qtbot.addWidget(area)

    area.set_grid(2, 2)

    assert area.layout_model.n_cells == 4
    assert area.plot_widget_at(3) is not area.plot_widget_at(0)


def test_set_grid_preserves_plots_by_position(qtbot: QtBot) -> None:
    area = PlotViewArea()
    qtbot.addWidget(area)
    area.set_current_plot(plot("keep"))

    area.set_grid(2, 2)

    assert area.layout_model.plot_at(0, 0).title == "keep"
    assert area.plot_widget_at(0).model.title == "keep"
    assert area.layout_model.plot_at(1, 1).n_traces == 0


def test_shrinking_grid_clamps_current_index(qtbot: QtBot) -> None:
    area = PlotViewArea()
    qtbot.addWidget(area)
    area.set_grid(2, 2)
    area.set_current_index(3)

    area.set_grid(1, 1)

    assert area.current_index == 0


def test_set_current_plot_targets_the_selected_cell(qtbot: QtBot) -> None:
    area = PlotViewArea()
    qtbot.addWidget(area)
    area.set_grid(1, 2)
    area.set_current_index(1)

    area.set_current_plot(plot("second"))

    assert area.layout_model.plot_at(0, 1).title == "second"
    assert area.layout_model.plot_at(0, 0).n_traces == 0
    assert area.plot_widget_at(1).model.title == "second"


def test_set_current_index_emits_signal(qtbot: QtBot) -> None:
    area = PlotViewArea()
    qtbot.addWidget(area)
    area.set_grid(1, 2)

    with qtbot.waitSignal(area.current_index_changed) as blocker:
        area.set_current_index(1)

    assert blocker.args == [1]


def test_set_current_index_rejects_out_of_range(qtbot: QtBot) -> None:
    area = PlotViewArea()
    qtbot.addWidget(area)

    with pytest.raises(ValueError, match="Cell index"):
        area.set_current_index(1)


def test_set_layout_model_replaces_the_grid(qtbot: QtBot) -> None:
    area = PlotViewArea()
    qtbot.addWidget(area)

    area.set_layout_model(ViewLayout(rows=1, cols=3))

    assert area.layout_model.n_cells == 3


def test_apply_theme_reaches_every_cell(qtbot: QtBot) -> None:
    area = PlotViewArea()
    qtbot.addWidget(area)
    area.set_grid(2, 2)

    area.apply_theme(Theme.LIGHT)

    assert area.theme is Theme.LIGHT
    assert all(area.plot_widget_at(index).theme is Theme.LIGHT for index in range(4))
