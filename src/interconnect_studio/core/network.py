"""Core network domain model."""

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import ArrayLike, NDArray

from interconnect_studio.core.errors import InputValidationError


@dataclass(frozen=True, slots=True, init=False)
class Network:
    """Frequency-domain S-parameter network.

    Parameters
    ----------
    frequencies_hz:
        One-dimensional frequency vector in Hz. Values must be finite,
        non-negative, and strictly increasing.
    s:
        S-parameter matrix with shape (n_freq, n_port, n_port).
    z0:
        Single scalar reference impedance in ohms for the entire network.
        The value must be finite and non-zero.
    port_names:
        Optional tuple of unique, non-empty display names. Its length must
        equal the number of ports.

    Notes
    -----
    Network owns copies of the frequency and S-parameter arrays. These
    internal arrays are read-only so that a constructed network behaves as an
    immutable domain object.
    """

    frequencies_hz: NDArray[np.float64]
    s: NDArray[np.complex128]
    z0: complex
    port_names: tuple[str, ...] | None
    _n_freq: int = field(repr=False)
    _n_ports: int = field(repr=False)

    def __init__(
        self,
        frequencies_hz: ArrayLike,
        s: ArrayLike,
        z0: complex,
        port_names: tuple[str, ...] | None = None,
    ) -> None:
        frequencies = np.asarray(frequencies_hz, dtype=np.float64)
        s_parameters = np.asarray(s, dtype=np.complex128)

        self._validate_frequencies(frequencies)
        self._validate_s(s_parameters, frequencies.size)
        z0_value = self._validate_z0(z0)
        normalized_port_names = self._validate_port_names(
            port_names,
            s_parameters.shape[1],
        )

        owned_frequencies = frequencies.copy()
        owned_s = s_parameters.copy()
        owned_frequencies.flags.writeable = False
        owned_s.flags.writeable = False

        object.__setattr__(self, "frequencies_hz", owned_frequencies)
        object.__setattr__(self, "s", owned_s)
        object.__setattr__(self, "z0", z0_value)
        object.__setattr__(self, "port_names", normalized_port_names)
        object.__setattr__(self, "_n_freq", owned_frequencies.size)
        object.__setattr__(self, "_n_ports", owned_s.shape[1])

    @property
    def n_freq(self) -> int:
        """Number of frequency points."""

        return self._n_freq

    @property
    def n_ports(self) -> int:
        """Number of network ports."""

        return self._n_ports

    @staticmethod
    def _validate_frequencies(frequencies_hz: NDArray[np.float64]) -> None:
        if frequencies_hz.ndim != 1:
            raise InputValidationError("frequencies_hz must be a one-dimensional array.")
        if frequencies_hz.size == 0:
            raise InputValidationError("frequencies_hz must contain at least one point.")
        if not np.all(np.isfinite(frequencies_hz)):
            raise InputValidationError("frequencies_hz must contain only finite values.")
        if np.any(frequencies_hz < 0.0):
            raise InputValidationError("frequencies_hz must not contain negative values.")
        if frequencies_hz.size > 1 and np.any(np.diff(frequencies_hz) <= 0.0):
            raise InputValidationError("frequencies_hz must be strictly increasing.")

    @staticmethod
    def _validate_s(s: NDArray[np.complex128], n_freq: int) -> None:
        if s.ndim != 3:
            raise InputValidationError("s must have shape (n_freq, n_port, n_port).")
        if s.shape[0] != n_freq:
            raise InputValidationError("s frequency dimension must match frequencies_hz.")
        if s.shape[1] == 0 or s.shape[2] == 0:
            raise InputValidationError("s must contain at least one port.")
        if s.shape[1] != s.shape[2]:
            raise InputValidationError("s port dimensions must form a square matrix.")
        if not np.all(np.isfinite(s)):
            raise InputValidationError("s must contain only finite complex values.")

    @staticmethod
    def _validate_z0(z0: complex) -> complex:
        if isinstance(z0, np.ndarray) or not np.isscalar(z0):
            raise InputValidationError("z0 must be a scalar reference impedance.")

        try:
            z0_value = complex(z0)
        except (TypeError, ValueError) as exc:
            raise InputValidationError("z0 must be convertible to a complex scalar.") from exc

        if not np.isfinite(z0_value.real) or not np.isfinite(z0_value.imag):
            raise InputValidationError("z0 must be finite.")
        if z0_value == 0:
            raise InputValidationError("z0 must be non-zero.")

        return z0_value

    @staticmethod
    def _validate_port_names(
        port_names: tuple[str, ...] | None,
        n_ports: int,
    ) -> tuple[str, ...] | None:
        if port_names is None:
            return None
        if not isinstance(port_names, tuple):
            raise InputValidationError("port_names must be a tuple of strings or None.")
        if len(port_names) != n_ports:
            raise InputValidationError("port_names length must equal the number of ports.")
        if any(not isinstance(name, str) or not name.strip() for name in port_names):
            raise InputValidationError("port_names must contain only non-empty strings.")
        if len(set(port_names)) != len(port_names):
            raise InputValidationError("port_names must be unique.")

        return port_names
