"""UI-independent trace domain model."""

from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt

from interconnect_studio.core.errors import InputValidationError

TraceValues = npt.NDArray[np.float64] | npt.NDArray[np.complex128]


@dataclass(frozen=True, slots=True, init=False)
class Trace:
    """Immutable one-dimensional data series ready for plotting."""

    name: str
    x: npt.NDArray[np.float64]
    y: TraceValues
    x_unit: str
    y_unit: str
    _n_points: int = field(repr=False)

    def __init__(
        self,
        name: str,
        x: npt.ArrayLike,
        y: npt.ArrayLike,
        *,
        x_unit: str = "",
        y_unit: str = "",
    ) -> None:
        if not isinstance(name, str) or not name.strip():
            raise InputValidationError("Trace name must be a non-empty string.")
        if not isinstance(x_unit, str) or not isinstance(y_unit, str):
            raise InputValidationError("Trace units must be strings.")

        x_values = np.asarray(x, dtype=np.float64)
        raw_y = np.asarray(y)
        y_values: TraceValues
        if np.iscomplexobj(raw_y):
            y_values = np.asarray(raw_y, dtype=np.complex128)
        else:
            y_values = np.asarray(raw_y, dtype=np.float64)

        self._validate_arrays(x_values, y_values)

        owned_x = x_values.copy()
        owned_y = y_values.copy()
        owned_x.flags.writeable = False
        owned_y.flags.writeable = False

        object.__setattr__(self, "name", name.strip())
        object.__setattr__(self, "x", owned_x)
        object.__setattr__(self, "y", owned_y)
        object.__setattr__(self, "x_unit", x_unit)
        object.__setattr__(self, "y_unit", y_unit)
        object.__setattr__(self, "_n_points", owned_x.size)

    @property
    def n_points(self) -> int:
        """Number of points in this trace."""

        return self._n_points

    @property
    def is_complex(self) -> bool:
        """Whether the y data is complex-valued."""

        return np.iscomplexobj(self.y)

    @staticmethod
    def _validate_arrays(x: npt.NDArray[np.float64], y: TraceValues) -> None:
        if x.ndim != 1:
            raise InputValidationError("Trace x must be one-dimensional.")
        if y.ndim != 1:
            raise InputValidationError("Trace y must be one-dimensional.")
        if x.size == 0:
            raise InputValidationError("Trace must contain at least one point.")
        if x.size != y.size:
            raise InputValidationError("Trace x and y must contain the same number of points.")
        if not np.all(np.isfinite(x)):
            raise InputValidationError("Trace x must contain only finite values.")
        if x.size > 1 and np.any(np.diff(x) <= 0.0):
            raise InputValidationError("Trace x must be strictly increasing.")
