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


class YAxis(StrEnum):
    """Which of a plot's two y axes a trace is drawn against."""

    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True, slots=True)
class PlotTrace:
    """A trace together with the y axis it is drawn against.

    Axis placement is a property of the plot, not of the trace itself: the
    same trace may appear on different axes in different plots.
    """

    trace: Trace
    y_axis: YAxis = YAxis.LEFT

    def __post_init__(self) -> None:
        if not isinstance(self.trace, Trace):
            raise InputValidationError("PlotTrace.trace must be a Trace.")
        if not isinstance(self.y_axis, YAxis):
            raise InputValidationError("PlotTrace.y_axis must be a YAxis.")


@dataclass(frozen=True, slots=True)
class PlotModel:
    """Immutable description of one plot and its traces.

    A plot has a single x axis and up to two y axes. Traces sharing a y axis
    must share a y unit; traces on opposite axes need not.
    """

    entries: tuple[PlotTrace, ...] = ()
    kind: PlotKind = PlotKind.CARTESIAN
    title: str = ""
    x_label: str = ""
    y_label_left: str = ""
    y_label_right: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.kind, PlotKind):
            raise InputValidationError("kind must be a PlotKind.")
        labels = (self.title, self.x_label, self.y_label_left, self.y_label_right)
        if not all(isinstance(value, str) for value in labels):
            raise InputValidationError("Plot title and axis labels must be strings.")
        if not isinstance(self.entries, tuple) or not all(
            isinstance(entry, PlotTrace) for entry in self.entries
        ):
            raise InputValidationError("entries must be a tuple of PlotTrace objects.")

        self._validate_trace_geometry()
        self._validate_trace_compatibility()

    @property
    def traces(self) -> tuple[Trace, ...]:
        """Traces in insertion order, without their axis assignment."""

        return tuple(entry.trace for entry in self.entries)

    @property
    def n_traces(self) -> int:
        """Number of traces in the plot."""

        return len(self.entries)

    def traces_on(self, y_axis: YAxis) -> tuple[Trace, ...]:
        """Traces drawn against the given y axis, in insertion order."""

        if not isinstance(y_axis, YAxis):
            raise InputValidationError("y_axis must be a YAxis.")
        return tuple(entry.trace for entry in self.entries if entry.y_axis is y_axis)

    def add_trace(self, trace: Trace, y_axis: YAxis = YAxis.LEFT) -> "PlotModel":
        """Return a new plot model containing one additional trace."""

        return self._replace(entries=(*self.entries, PlotTrace(trace, y_axis)))

    def remove_trace(self, index: int) -> "PlotModel":
        """Return a new plot model with the selected trace removed."""

        if isinstance(index, bool) or not isinstance(index, int):
            raise InputValidationError("Trace index must be an integer.")
        if index < 0 or index >= self.n_traces:
            raise InputValidationError(
                f"Trace index must be in the range [0, {self.n_traces - 1}], got {index}."
            )
        return self._replace(entries=self.entries[:index] + self.entries[index + 1 :])

    def _replace(self, entries: tuple[PlotTrace, ...]) -> "PlotModel":
        return PlotModel(
            entries=entries,
            kind=self.kind,
            title=self.title,
            x_label=self.x_label,
            y_label_left=self.y_label_left,
            y_label_right=self.y_label_right,
        )

    def _validate_trace_geometry(self) -> None:
        traces = self.traces
        if self.kind is PlotKind.CARTESIAN:
            if any(trace.is_complex for trace in traces):
                raise InputValidationError("Cartesian plots require real-valued trace y data.")
            return

        if any(not trace.is_complex for trace in traces):
            raise InputValidationError(
                f"{self.kind.value} plots require complex-valued trace y data."
            )

    def _validate_trace_compatibility(self) -> None:
        if not self.entries:
            return

        x_unit = self.entries[0].trace.x_unit
        if any(entry.trace.x_unit != x_unit for entry in self.entries):
            raise InputValidationError("All traces in a plot must use the same x unit.")

        for axis in YAxis:
            on_axis = self.traces_on(axis)
            if not on_axis:
                continue
            y_unit = on_axis[0].y_unit
            if any(trace.y_unit != y_unit for trace in on_axis):
                raise InputValidationError(
                    f"All traces on the {axis.value} y axis must use the same y unit."
                )
