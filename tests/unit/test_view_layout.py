import pytest

from interconnect_studio.core import MAX_PLOTS, InputValidationError, PlotModel, Trace, ViewLayout


def plot(name: str) -> PlotModel:
    trace = Trace(name, [1.0, 2.0], [1.0, 2.0], x_unit="Hz", y_unit="dB")
    return PlotModel(title=name).add_trace(trace)


def test_view_layout_fills_empty_plots_by_default() -> None:
    layout = ViewLayout(rows=2, cols=2)

    assert layout.n_cells == 4
    assert len(layout.plots) == 4
    assert all(cell.n_traces == 0 for cell in layout.plots)


def test_view_layout_is_row_major() -> None:
    layout = ViewLayout(rows=2, cols=3).with_plot(1, 2, plot("last"))

    assert layout.index_of(1, 2) == 5
    assert layout.plots[5].title == "last"
    assert layout.plot_at(1, 2).title == "last"


def test_with_plot_returns_new_layout() -> None:
    layout = ViewLayout(rows=1, cols=2)

    updated = layout.with_plot(0, 0, plot("S11"))

    assert layout.plot_at(0, 0).n_traces == 0
    assert updated.plot_at(0, 0).title == "S11"


def test_view_layout_rejects_plot_count_mismatch() -> None:
    with pytest.raises(InputValidationError, match="needs 4 plots"):
        ViewLayout(rows=2, cols=2, plots=(PlotModel(),))


@pytest.mark.parametrize(("rows", "cols"), [(0, 1), (1, 0), (-1, 2)])
def test_view_layout_rejects_non_positive_dimensions(rows: int, cols: int) -> None:
    with pytest.raises(InputValidationError, match="at least 1"):
        ViewLayout(rows=rows, cols=cols)


def test_view_layout_accepts_maximum_grid() -> None:
    layout = ViewLayout(rows=12, cols=12)

    assert layout.n_cells == MAX_PLOTS


def test_view_layout_rejects_grid_above_maximum() -> None:
    with pytest.raises(InputValidationError, match="at most 144"):
        ViewLayout(rows=12, cols=13)


def test_index_of_rejects_out_of_range_cell() -> None:
    layout = ViewLayout(rows=2, cols=2)

    with pytest.raises(InputValidationError, match="range"):
        layout.plot_at(2, 0)


def test_resized_preserves_plots_by_position() -> None:
    layout = ViewLayout(rows=2, cols=2).with_plot(0, 0, plot("keep")).with_plot(1, 1, plot("drop"))

    smaller = layout.resized(1, 1)

    assert smaller.n_cells == 1
    assert smaller.plot_at(0, 0).title == "keep"


def test_resized_leaves_new_cells_empty() -> None:
    layout = ViewLayout(rows=1, cols=1).with_plot(0, 0, plot("keep"))

    larger = layout.resized(2, 2)

    assert larger.plot_at(0, 0).title == "keep"
    assert larger.plot_at(1, 1).n_traces == 0
