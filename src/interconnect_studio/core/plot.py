"""UI-independent plot domain model."""

from dataclasses import dataclass, replace
from enum import StrEnum

from interconnect_studio.core.errors import InputValidationError
from interconnect_studio.core.marker import Marker
from interconnect_studio.core.trace import Trace


class PlotKind(StrEnum):
    """Geometry used to render a plot."""

    CARTESIAN = "cartesian"
    POLAR = "polar"
    SMITH = "smith"


@dataclass(frozen=True, slots=True)
class PlotModel:
    """Immutable description of one plot and its traces.

    A plot has a single x axis and a single y axis: every trace in it shares
    one display format, matching PLTS. Comparing quantities of different
    units means separate plots, not a second y axis.
    """

    traces: tuple[Trace, ...] = ()
    kind: PlotKind = PlotKind.CARTESIAN
    title: str = ""
    x_label: str = ""
    y_label: str = ""
    markers: tuple[Marker, ...] = ()

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
        if not isinstance(self.markers, tuple) or not all(
            isinstance(m, Marker) for m in self.markers
        ):
            raise InputValidationError("markers must be a tuple of Marker objects.")
        by_number = {m.number: m for m in self.markers}
        if len(by_number) != len(self.markers):
            raise InputValidationError("Marker numbers must be unique within a plot.")
        for marker in self.markers:
            if self.kind is not PlotKind.CARTESIAN:
                raise InputValidationError("Markers currently require Cartesian plots.")
            if marker.trace_index >= len(self.traces):
                raise InputValidationError("Marker refers to a missing trace.")
            trace = self.traces[marker.trace_index]
            if not trace.x[0] <= marker.x <= trace.x[-1]:
                raise InputValidationError("Marker lies outside the trace span.")
            if marker.reference_id is not None:
                reference = by_number.get(marker.reference_id)
                if reference is None or reference.reference_id is not None:
                    raise InputValidationError(
                        "Delta reference must be an existing absolute marker."
                    )

    @property
    def n_traces(self) -> int:
        """Number of traces in the plot."""

        return len(self.traces)

    def add_trace(self, trace: Trace) -> "PlotModel":
        """Return a new plot model containing one additional trace."""

        return self._replace((*self.traces, trace))

    def remove_trace(self, index: int) -> "PlotModel":
        """Return a new plot model with the selected trace removed."""

        if isinstance(index, bool) or not isinstance(index, int):
            raise InputValidationError("Trace index must be an integer.")
        if index < 0 or index >= self.n_traces:
            raise InputValidationError(
                f"Trace index must be in the range [0, {self.n_traces - 1}], got {index}."
            )
        removed = {m.number for m in self.markers if m.trace_index == index}
        markers = tuple(
            replace(
                m,
                trace_index=m.trace_index - (m.trace_index > index),
                reference_id=None if m.reference_id in removed else m.reference_id,
            )
            for m in self.markers
            if m.trace_index != index
        )
        return replace(self, traces=self.traces[:index] + self.traces[index + 1 :], markers=markers)

    def _replace(self, traces: tuple[Trace, ...]) -> "PlotModel":
        return replace(self, traces=traces)

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
