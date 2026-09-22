"""UI-independent view layout model."""

from dataclasses import dataclass
from typing import Final

from interconnect_studio.core.errors import InputValidationError
from interconnect_studio.core.plot import PlotModel

MAX_PLOTS: Final[int] = 144
"""Upper bound on plots per window, matching PLTS."""


@dataclass(frozen=True, slots=True)
class ViewLayout:
    """Immutable fixed grid of plots filling one window.

    Plots are stored in row-major order, matching the Touchstone convention
    for three or more ports. Empty cells hold an empty ``PlotModel`` rather
    than ``None``, so callers never branch on absence.

    Passing no plots fills the grid with empty ones.
    """

    rows: int
    cols: int
    plots: tuple[PlotModel, ...] = ()

    def __post_init__(self) -> None:
        for name, value in (("rows", self.rows), ("cols", self.cols)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise InputValidationError(f"ViewLayout {name} must be an integer.")
            if value < 1:
                raise InputValidationError(f"ViewLayout {name} must be at least 1, got {value}.")

        n_cells = self.rows * self.cols
        if n_cells > MAX_PLOTS:
            raise InputValidationError(
                f"ViewLayout supports at most {MAX_PLOTS} plots, got {n_cells}."
            )

        if not isinstance(self.plots, tuple) or not all(
            isinstance(plot, PlotModel) for plot in self.plots
        ):
            raise InputValidationError("ViewLayout plots must be a tuple of PlotModel objects.")

        if not self.plots:
            object.__setattr__(self, "plots", tuple(PlotModel() for _ in range(n_cells)))
        elif len(self.plots) != n_cells:
            raise InputValidationError(
                f"ViewLayout {self.rows}x{self.cols} needs {n_cells} plots, got {len(self.plots)}."
            )

    @property
    def n_cells(self) -> int:
        """Number of grid cells."""

        return self.rows * self.cols

    def index_of(self, row: int, col: int) -> int:
        """Return the row-major index of a cell."""

        for name, value, limit in (("row", row, self.rows), ("col", col, self.cols)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise InputValidationError(f"ViewLayout {name} must be an integer.")
            if value < 0 or value >= limit:
                raise InputValidationError(
                    f"ViewLayout {name} must be in the range [0, {limit - 1}], got {value}."
                )
        return row * self.cols + col

    def plot_at(self, row: int, col: int) -> PlotModel:
        """Return the plot in the given cell."""

        return self.plots[self.index_of(row, col)]

    def with_plot(self, row: int, col: int, plot: PlotModel) -> "ViewLayout":
        """Return a new layout with one cell replaced."""

        if not isinstance(plot, PlotModel):
            raise InputValidationError("plot must be a PlotModel.")
        index = self.index_of(row, col)
        plots = self.plots[:index] + (plot,) + self.plots[index + 1 :]
        return ViewLayout(rows=self.rows, cols=self.cols, plots=plots)

    def resized(self, rows: int, cols: int) -> "ViewLayout":
        """Return a new layout of a different size, preserving plots by position.

        Cells that exist in both grids keep their plot; new cells are empty.
        """

        resized = ViewLayout(rows=rows, cols=cols)
        plots = list(resized.plots)
        for row in range(min(self.rows, resized.rows)):
            for col in range(min(self.cols, resized.cols)):
                plots[resized.index_of(row, col)] = self.plot_at(row, col)
        return ViewLayout(rows=rows, cols=cols, plots=tuple(plots))
