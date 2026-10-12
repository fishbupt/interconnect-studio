"""Collection edits preserve data and report where display state moved."""

import pytest

from interconnect_studio.core import InputValidationError, PlotModel, ViewLayout
from interconnect_studio.services.plot_layout import (
    delete_plot,
    insert_plot,
    move_plot,
    renamed_plot,
)


def test_insert_grows_without_losing_any_plot() -> None:
    original = tuple(PlotModel(title=str(i)) for i in range(4))
    edit = insert_plot(ViewLayout(2, 2, original), 0, PlotModel(title="new"))
    assert [p.title for p in edit.layout.plots] == ["0", "new", "1", "2", "3", ""]
    assert edit.origins == (0, None, 1, 2, 3, None)
    assert edit.current_index == 1


def test_full_window_reuses_empty_cell_and_rejects_overflow() -> None:
    layout = ViewLayout(12, 12, tuple(PlotModel(title=str(i)) for i in range(144)))
    with pytest.raises(InputValidationError, match="144"):
        insert_plot(layout, 0, PlotModel(title="new"))
    layout = layout.with_plot(11, 11, PlotModel())
    assert insert_plot(layout, 0, PlotModel(title="new")).layout.n_cells == 144


def test_delete_and_move_report_the_correct_origins() -> None:
    layout = ViewLayout(1, 3, tuple(PlotModel(title=str(i)) for i in range(3)))
    edit = move_plot(layout, 0, 2)
    assert edit.origins == (1, 2, 0)
    assert edit.layout.plots[2] is layout.plots[0]
    assert delete_plot(edit.layout, 1).origins == (0, 2, None)


@pytest.mark.parametrize("title", ["", " " * 3, "a" * 23])
def test_invalid_title_is_rejected(title: str) -> None:
    with pytest.raises(InputValidationError):
        renamed_plot(PlotModel(), title)
