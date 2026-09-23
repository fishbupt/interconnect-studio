"""Mixed-mode network domain model."""

from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np
from numpy.typing import ArrayLike, NDArray

from interconnect_studio.core.errors import InputValidationError
from interconnect_studio.core.port_group import PortGroup


class Mode(StrEnum):
    """Propagation mode of a mixed-mode port."""

    DIFFERENTIAL = "d"
    COMMON = "c"


@dataclass(frozen=True, slots=True, init=False)
class MixedModeNetwork:
    """Mixed-mode S-parameters of a differential DUT.

    Differential ports reference ``2 * z0`` and common ports ``z0 / 2``, so
    this cannot be a ``Network``, whose reference impedance is one scalar for
    every port.

    The matrix is in block order -- every differential port, then every
    common port -- giving the familiar form::

        [[Sdd, Sdc],
         [Scd, Scc]]

    Within each block, ports run line by line, near end before far end. For a
    single differential line that is D1 = near, D2 = far.
    """

    frequencies_hz: NDArray[np.float64]
    s: NDArray[np.complex128]
    z0_differential: complex
    z0_common: complex
    port_group: PortGroup
    _n_freq: int = field(repr=False)
    _n_mode_ports: int = field(repr=False)

    def __init__(
        self,
        frequencies_hz: ArrayLike,
        s: ArrayLike,
        z0_differential: complex,
        z0_common: complex,
        port_group: PortGroup,
    ) -> None:
        frequencies = np.asarray(frequencies_hz, dtype=np.float64)
        matrix = np.asarray(s, dtype=np.complex128)

        if frequencies.ndim != 1 or frequencies.size == 0:
            raise InputValidationError("frequencies_hz must be a non-empty one-dimensional array.")
        if matrix.ndim != 3 or matrix.shape[1] != matrix.shape[2]:
            raise InputValidationError("s must have shape (n_freq, n_port, n_port).")
        if matrix.shape[0] != frequencies.size:
            raise InputValidationError("s and frequencies_hz must agree on the frequency count.")
        if not isinstance(port_group, PortGroup):
            raise InputValidationError("port_group must be a PortGroup.")
        if not port_group.is_differential:
            raise InputValidationError("MixedModeNetwork requires every line to be differential.")
        if matrix.shape[1] != port_group.n_ports:
            raise InputValidationError(
                f"s has {matrix.shape[1]} ports but the port group covers {port_group.n_ports}."
            )
        if matrix.shape[1] % 2 != 0:
            raise InputValidationError("A mixed-mode matrix needs an even port count.")

        owned_frequencies = frequencies.copy()
        owned_s = matrix.copy()
        owned_frequencies.flags.writeable = False
        owned_s.flags.writeable = False

        object.__setattr__(self, "frequencies_hz", owned_frequencies)
        object.__setattr__(self, "s", owned_s)
        object.__setattr__(self, "z0_differential", complex(z0_differential))
        object.__setattr__(self, "z0_common", complex(z0_common))
        object.__setattr__(self, "port_group", port_group)
        object.__setattr__(self, "_n_freq", owned_frequencies.size)
        object.__setattr__(self, "_n_mode_ports", owned_s.shape[1] // 2)

    @property
    def n_freq(self) -> int:
        """Number of frequency points."""

        return self._n_freq

    @property
    def n_mode_ports(self) -> int:
        """Number of ports per mode, i.e. half the matrix size."""

        return self._n_mode_ports

    def mode_parameter(
        self,
        response_mode: Mode,
        source_mode: Mode,
        response_port: int,
        source_port: int,
    ) -> NDArray[np.complex128]:
        """Return one mixed-mode parameter, e.g. SDD21.

        Ports are 0-based within their mode, so engineering ``SDD21`` is
        ``mode_parameter(DIFFERENTIAL, DIFFERENTIAL, 1, 0)``.
        """

        row = self._index(response_mode, response_port, "response")
        column = self._index(source_mode, source_port, "source")
        return np.asarray(self.s[:, row, column], dtype=np.complex128)

    def _index(self, mode: Mode, port: int, label: str) -> int:
        if not isinstance(mode, Mode):
            raise InputValidationError(f"{label} mode must be a Mode.")
        if isinstance(port, bool) or not isinstance(port, int):
            raise InputValidationError(f"{label} port must be an integer.")
        if port < 0 or port >= self._n_mode_ports:
            raise InputValidationError(
                f"{label} port must be in [0, {self._n_mode_ports - 1}], got {port}."
            )
        offset = 0 if mode is Mode.DIFFERENTIAL else self._n_mode_ports
        return offset + port
