"""UI-independent plot domain model."""

from dataclasses import dataclass
from enum import StrEnum

from interconnect_studio.core.errors import InputValidationError
from interconnect_studio.core.trace import Trace


class PlotKind(StrEnum):
    """Geometry used to render a plot."""

    CARTESIAN = "cartesian"
    POLAR = "polar"
    SMITH = "smith"


@dataclass(frozen=True, slots=True)
class PlotModel:
    """Immutable description of one plot and its traces."""

    traces: tuple[Trace, ...] = ()
    kind: PlotKind = PlotKind.CARTESIAN
    title: str = ""
    x_label: str = ""
    y_label: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.kind, PlotKind):
            raise InputValidationError("kind must be a PlotKind.")
        if not all(isinstance(value, str) for value in (self.title, self.x_label, self.y_label)):
            raise InputValidationError("Plot title and axis labels must be strings.")
        if not isinstance(self.traces, tuple) or not all(
            isinstance(trace, Trace) for trace in self.traces
        ):
            raise InputValidationError("traces must be a tuple of Trace objects.")

        self._validate_trace_geometry()
        self._validate_trace_compatibility()

    @property
    def n_traces(self) -> int:
        """Number of traces in the plot."""

        return len(self.traces)

    def add_trace(self, trace: Trace) -> "PlotModel":
        """Return a new plot model containing one additional trace."""

        return PlotModel(
            traces=(*self.traces, trace),
            kind=self.kind,
            title=self.title,
            x_label=self.x_label,
            y_label=self.y_label,
        )

    def remove_trace(self, index: int) -> "PlotModel":
        """Return a new plot model with the selected trace removed."""

        if isinstance(index, bool) or not isinstance(index, int):
            raise InputValidationError("Trace index must be an integer.")
        if index < 0 or index >= self.n_traces:
            raise InputValidationError(
                f"Trace index must be in the range [0, {self.n_traces - 1}], got {index}."
            )
        traces = self.traces[:index] + self.traces[index + 1 :]
        return PlotModel(
            traces=traces,
            kind=self.kind,
            title=self.title,
            x_label=self.x_label,
            y_label=self.y_label,
        )

    def _validate_trace_geometry(self) -> None:
        if self.kind is PlotKind.CARTESIAN:
            if any(trace.is_complex for trace in self.traces):
                raise InputValidationError("Cartesian plots require real-valued trace y data.")
            return

        if any(not trace.is_complex for trace in self.traces):
            raise InputValidationError(
                f"{self.kind.value} plots require complex-valued trace y data."
            )

    def _validate_trace_compatibility(self) -> None:
        if not self.traces:
            return

        reference = self.traces[0]
        for trace in self.traces[1:]:
            if trace.x_unit != reference.x_unit:
                raise InputValidationError("All traces in a plot must use the same x unit.")
            if trace.y_unit != reference.y_unit:
                raise InputValidationError("All traces in a plot must use the same y unit.")
