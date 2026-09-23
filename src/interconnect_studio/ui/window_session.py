"""Per-window display state, so windows keep their plots when switched.

PLTS gives every window (one data file in one analysis view) its own grid of
plots. The view area shows one window at a time; this holds what the others
were showing: the network, the grid layout and the selected cell.
"""

from dataclasses import dataclass, replace

from interconnect_studio.core import InputValidationError, ViewLayout, ViewType
from interconnect_studio.services import LoadedTouchstonePlot


@dataclass(frozen=True, slots=True)
class WindowSession:
    """Display state of one open window.

    ``loaded`` names the window's network; its ``plot`` is not kept in sync
    and is taken from ``layout`` instead (``loaded_for_current_cell``).
    """

    number: int
    view_type: ViewType
    loaded: LoadedTouchstonePlot
    layout: ViewLayout
    current_index: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.current_index < self.layout.n_cells:
            raise InputValidationError(
                f"current_index {self.current_index} is outside the "
                f"{self.layout.rows}x{self.layout.cols} layout."
            )

    @property
    def title(self) -> str:
        """Window title in the PLTS style: file name, analysis view and number."""

        return f"{self.loaded.name} - {self.view_type.label} : {self.number}"

    def loaded_for_current_cell(self) -> LoadedTouchstonePlot:
        """The window's network paired with the plot of its selected cell."""

        return replace(self.loaded, plot=self.layout.plots[self.current_index])

    def renamed(self, name: str) -> "WindowSession":
        """The same window after its data file is renamed.

        Plots titled with the old file name take the new one.
        """

        old = self.loaded.name
        plots = tuple(
            replace(plot, title=name) if plot.title == old else plot for plot in self.layout.plots
        )
        return replace(
            self,
            loaded=replace(self.loaded, name=name),
            layout=replace(self.layout, plots=plots),
        )
