"""UI-independent trace domain model."""

from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt

from interconnect_studio.core.errors import InputValidationError

TraceValues = npt.NDArray[np.float64] | npt.NDArray[np.complex128]


@dataclass(frozen=True, slots=True)
class TraceRecipe:
    """How a trace is computed from its source network.

    ``response_port`` and ``source_port`` are 0-based: the trace shows
    S[response_port + 1][source_port + 1]. ``data_format`` is the display
    format identifier (the value of ``SParameterFormat``); core does not
    interpret it.
    """

    response_port: int
    source_port: int
    data_format: str

    def __post_init__(self) -> None:
        for label, port in (
            ("response_port", self.response_port),
            ("source_port", self.source_port),
        ):
            if isinstance(port, bool) or not isinstance(port, int) or port < 0:
                raise InputValidationError(f"TraceRecipe {label} must be a non-negative integer.")
        if not isinstance(self.data_format, str) or not self.data_format:
            raise InputValidationError("TraceRecipe data_format must be a non-empty string.")

    @property
    def max_port(self) -> int:
        """Highest 0-based port the recipe reads."""

        return max(self.response_port, self.source_port)


@dataclass(frozen=True, slots=True, init=False)
class Trace:
    """Immutable one-dimensional data series ready for plotting.

    ``source_id`` identifies the ``DataFile`` this trace was derived from.
    It is empty for traces not attached to any file. ``recipe`` says how the
    trace was computed from that file, so it can be recomputed for another
    one (templates); it is ``None`` for traces not computed from a network.
    """

    name: str
    x: npt.NDArray[np.float64]
    y: TraceValues
    x_unit: str
    y_unit: str
    source_id: str
    recipe: TraceRecipe | None
    _n_points: int = field(repr=False)

    def __init__(
        self,
        name: str,
        x: npt.ArrayLike,
        y: npt.ArrayLike,
        *,
        x_unit: str = "",
        y_unit: str = "",
        source_id: str = "",
        recipe: TraceRecipe | None = None,
    ) -> None:
        if not isinstance(name, str) or not name.strip():
            raise InputValidationError("Trace name must be a non-empty string.")
        if not isinstance(x_unit, str) or not isinstance(y_unit, str):
            raise InputValidationError("Trace units must be strings.")
        if not isinstance(source_id, str):
            raise InputValidationError("Trace source_id must be a string.")
        if recipe is not None and not isinstance(recipe, TraceRecipe):
            raise InputValidationError("Trace recipe must be a TraceRecipe or None.")

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
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "recipe", recipe)
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
