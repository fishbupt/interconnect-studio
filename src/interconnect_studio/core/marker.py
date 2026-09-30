"""Measured-point markers, independent of the plotting toolkit."""

import math
from dataclasses import dataclass

from interconnect_studio.core.errors import InputValidationError


@dataclass(frozen=True, slots=True)
class Marker:
    """A numbered marker on a trace (0-based); x uses that trace's x unit.

    reference_id optionally selects an absolute marker for delta readout.
    Only x is stored; the measured y value is always evaluated from the trace.
    """

    number: int
    trace_index: int
    x: float
    reference_id: int | None = None

    def __post_init__(self) -> None:
        for name, value, minimum in (
            ("number", self.number, 1),
            ("trace_index", self.trace_index, 0),
        ):
            if type(value) is not int or value < minimum:
                raise InputValidationError(f"Marker {name} must be an integer >= {minimum}.")
        if (
            isinstance(self.x, bool)
            or not isinstance(self.x, (int, float))
            or not math.isfinite(self.x)
        ):
            raise InputValidationError("Marker x must be finite.")
        if self.reference_id is not None and (
            type(self.reference_id) is not int
            or self.reference_id < 1
            or self.reference_id == self.number
        ):
            raise InputValidationError("Delta reference must name another marker.")
