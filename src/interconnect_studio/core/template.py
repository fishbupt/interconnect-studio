"""Saved analysis templates (PLTS "Template View").

A template records how a window is laid out so another data file can be
opened the same way: the plot grid, and for every plot its geometry, labels
and the recipes of its traces. It holds no measured data.

Markers, equations, limit lines and scale settings will join the template
as those features are implemented.
"""

from dataclasses import dataclass

from interconnect_studio.core.errors import InputValidationError
from interconnect_studio.core.hierarchy import ViewType
from interconnect_studio.core.layout import ViewLayout
from interconnect_studio.core.plot import PlotKind
from interconnect_studio.core.trace import TraceRecipe

FORBIDDEN_NAME_CHARACTERS = '/\\:*?"<>|'
"""Characters a template name cannot hold; the name is also its file name."""


@dataclass(frozen=True, slots=True)
class TemplatePlot:
    """One plot of a template.

    ``title`` is ``None`` when the plot was titled with its data file's name;
    it then takes the name of whichever file the template is applied to.
    """

    traces: tuple[TraceRecipe, ...] = ()
    kind: PlotKind = PlotKind.CARTESIAN
    title: str | None = None
    x_label: str = ""
    y_label: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.traces, tuple) or not all(
            isinstance(item, TraceRecipe) for item in self.traces
        ):
            raise InputValidationError("TemplatePlot traces must be a tuple of TraceRecipe.")
        if not isinstance(self.kind, PlotKind):
            raise InputValidationError("TemplatePlot kind must be a PlotKind.")

    def title_for(self, file_name: str) -> str:
        """Plot title when the template is applied to a file of this name."""

        return file_name if self.title is None else self.title


@dataclass(frozen=True, slots=True)
class ViewTemplate:
    """A saved window layout, listed under Template View.

    ``n_ports`` is the port count of the file the template was saved from and
    is shown as in PLTS ("USB3.0 Connector (12p)"). ``plots`` are in the
    row-major order of ``ViewLayout``, one per cell.
    """

    name: str
    view_type: ViewType
    n_ports: int
    rows: int
    cols: int
    plots: tuple[TemplatePlot, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise InputValidationError("Template name must be a non-empty string.")
        name = self.name.strip()
        if any(char in FORBIDDEN_NAME_CHARACTERS for char in name) or name.startswith("."):
            raise InputValidationError(
                f"Template name cannot start with '.' or contain {FORBIDDEN_NAME_CHARACTERS}."
            )
        object.__setattr__(self, "name", name)
        if not isinstance(self.view_type, ViewType):
            raise InputValidationError("Template view_type must be a ViewType.")
        if isinstance(self.n_ports, bool) or not isinstance(self.n_ports, int) or self.n_ports < 1:
            raise InputValidationError("Template n_ports must be a positive integer.")
        # ViewLayout validates the grid size.
        layout = ViewLayout(rows=self.rows, cols=self.cols)
        if not isinstance(self.plots, tuple) or len(self.plots) != layout.n_cells:
            raise InputValidationError(
                f"Template needs {layout.n_cells} plots for a {self.rows}x{self.cols} grid."
            )
        if not all(isinstance(plot, TemplatePlot) for plot in self.plots):
            raise InputValidationError("Template plots must be TemplatePlot objects.")
        if self.required_ports > self.n_ports:
            raise InputValidationError(
                f"Template traces use port {self.required_ports}, "
                f"but the template has {self.n_ports} ports."
            )

    @property
    def label(self) -> str:
        """Text shown in the browser, with the port count as in PLTS."""

        return f"{self.name} ({self.n_ports}p)"

    @property
    def required_ports(self) -> int:
        """Smallest port count a data file needs for every trace (0 if none)."""

        return max(
            (recipe.max_port + 1 for plot in self.plots for recipe in plot.traces), default=0
        )

    @classmethod
    def from_layout(
        cls,
        name: str,
        view_type: ViewType,
        n_ports: int,
        layout: ViewLayout,
        file_name: str,
    ) -> "ViewTemplate":
        """Capture a window's grid as a template.

        Plots titled ``file_name`` are stored as following the file name.
        Every trace must carry a recipe; one without cannot be recomputed.
        """

        plots = []
        for plot in layout.plots:
            recipes = []
            for trace in plot.traces:
                if trace.recipe is None:
                    raise InputValidationError(f"Trace {trace.name} cannot be saved in a template.")
                recipes.append(trace.recipe)
            plots.append(
                TemplatePlot(
                    traces=tuple(recipes),
                    kind=plot.kind,
                    title=None if plot.title == file_name else plot.title,
                    x_label=plot.x_label,
                    y_label=plot.y_label,
                )
            )
        return cls(name, view_type, n_ports, layout.rows, layout.cols, tuple(plots))
