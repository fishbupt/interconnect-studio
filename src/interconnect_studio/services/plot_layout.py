"""Pure plot collection commands, with origins for remapping display state."""

from dataclasses import dataclass, replace

from interconnect_studio.core import InputValidationError, PlotModel, ViewLayout
from interconnect_studio.core.layout import MAX_PLOTS


@dataclass(frozen=True)
class LayoutEdit:
    """New layout, active cell and each cell's previous display-state origin."""

    layout: ViewLayout
    current_index: int
    origins: tuple[int | None, ...]


def _index(layout: ViewLayout, index: int) -> None:
    if type(index) is not int or not 0 <= index < layout.n_cells:
        raise InputValidationError("Invalid plot index.")


def insert_plot(layout: ViewLayout, index: int, plot: PlotModel) -> LayoutEdit:
    """Insert after the active plot, reusing an empty cell before growing rows."""

    _index(layout, index)
    values = list(layout.plots)
    origins: list[int | None] = list(range(layout.n_cells))
    if not values[index].traces and not values[index].title:
        values[index] = plot
        origins[index] = None
        return LayoutEdit(replace(layout, plots=tuple(values)), index, tuple(origins))
    empty = next(
        (i for i, value in enumerate(values) if not value.traces and not value.title), None
    )
    if empty is not None:
        values.pop(empty)
        origins.pop(empty)
        if empty < index:
            index -= 1
    elif layout.n_cells == MAX_PLOTS:
        raise InputValidationError("A window supports at most 144 plots.")
    index += 1
    values.insert(index, plot)
    origins.insert(index, None)
    cols = layout.cols
    rows = max(layout.rows, (len(values) + cols - 1) // cols)
    if rows * cols > MAX_PLOTS:
        cols, rows = 1, len(values)
    while len(values) < rows * cols:
        values.append(PlotModel())
        origins.append(None)
    return LayoutEdit(ViewLayout(rows, cols, tuple(values)), index, tuple(origins))


def delete_plot(layout: ViewLayout, index: int) -> LayoutEdit:
    """Remove one plot, compact the grid and keep one empty cell if necessary."""

    _index(layout, index)
    values = list(layout.plots)
    origins: list[int | None] = list(range(layout.n_cells))
    values.pop(index)
    origins.pop(index)
    values.append(PlotModel())
    origins.append(None)
    return LayoutEdit(
        replace(layout, plots=tuple(values)), min(index, len(values) - 1), tuple(origins)
    )


def move_plot(layout: ViewLayout, index: int, destination: int) -> LayoutEdit:
    """Move a whole plot, keeping its traces and marker references together."""

    _index(layout, index)
    _index(layout, destination)
    values = list(layout.plots)
    origins = list(range(layout.n_cells))
    values.insert(destination, values.pop(index))
    origins.insert(destination, origins.pop(index))
    return LayoutEdit(replace(layout, plots=tuple(values)), destination, tuple(origins))


def renamed_plot(plot: PlotModel, title: str) -> PlotModel:
    """Set a nonempty custom plot title, limited to 22 characters."""

    title = title.strip()
    if not title or len(title) > 22:
        raise InputValidationError("Plot name must contain 1–22 characters.")
    return replace(plot, title=title)
