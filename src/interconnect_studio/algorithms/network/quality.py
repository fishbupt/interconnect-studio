"""Read-only data-quality checks on a Network.

Nothing here modifies data, corrects it, or leaves a quality mark on the
``Network``. Every check answers a question and hands back the numbers it
used; what to do about the answer belongs to the caller. Correction is a
separate, explicit algorithm (see ``ALGORITHM_GUIDE.md`` §12.5).

These checks are also how this project finds its own mistakes. A
de-embedding result whose largest singular value exceeds one is almost
always a bug in the algorithm or its input, not a discovery about the DUT.
"""

from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray

from interconnect_studio.core import InputValidationError, Network

# Round-off in a float64 SVD of a matrix this small lands around 1e-15, so
# 1e-9 is far above the arithmetic and far below anything a measurement can
# hide. This is the tolerance for checking our own algorithm output, which
# is the primary use of this module.
ARITHMETIC_TOLERANCE: Final[float] = 1.0e-9

# Calibrated measurements of a passive DUT routinely sit a few 1e-4 above
# unity, so checking one against ARITHMETIC_TOLERANCE reports every file.
# PROVISIONAL: this threshold is a placeholder, not a referenced figure. It
# needs to be set from real PLTS / PNA exports before any UI presents a
# pass or fail to a user.
MEASUREMENT_TOLERANCE: Final[float] = 1.0e-3

PASSIVITY: Final[str] = "passivity"
RECIPROCITY: Final[str] = "reciprocity"


@dataclass(frozen=True, slots=True)
class QualityResult:
    """One check's numbers, per frequency.

    Parameters
    ----------
    name:
        Which check produced this, one of ``PASSIVITY`` / ``RECIPROCITY``.
    frequencies_hz:
        Frequency vector in Hz, shape ``(n_freq,)``.
    metric:
        The checked quantity at each frequency, dimensionless, shape
        ``(n_freq,)``. Its meaning is the check's own: the largest
        singular value for passivity, the largest asymmetry for
        reciprocity.
    limit:
        The value ``metric`` may not exceed for ideal data.
    tolerance:
        How far past ``limit`` the metric may go before it counts as a
        violation.
    """

    name: str
    frequencies_hz: NDArray[np.float64]
    metric: NDArray[np.float64]
    limit: float
    tolerance: float

    @property
    def excess(self) -> NDArray[np.float64]:
        """How far the metric runs past the limit, shape ``(n_freq,)``.

        Negative where the data is inside the limit.
        """

        return self.metric - self.limit

    @property
    def violations(self) -> NDArray[np.intp]:
        """Indices of the frequencies that exceed limit plus tolerance."""

        return np.flatnonzero(self.excess > self.tolerance)

    @property
    def passed(self) -> bool:
        """True when no frequency exceeds limit plus tolerance."""

        return self.violations.size == 0

    @property
    def worst_index(self) -> int:
        """Index of the frequency with the largest metric."""

        return int(np.argmax(self.metric))

    @property
    def worst_metric(self) -> float:
        """Largest metric over frequency, dimensionless."""

        return float(self.metric[self.worst_index])

    @property
    def worst_frequency_hz(self) -> float:
        """Frequency in Hz at which the metric is largest."""

        return float(self.frequencies_hz[self.worst_index])

    def summary(self) -> str:
        """One line naming the outcome and where the data is worst."""

        verdict = "passed" if self.passed else f"failed at {self.violations.size} points"
        return (
            f"{self.name}: {verdict}; worst {self.worst_metric:.9g} "
            f"at {self.worst_frequency_hz:g} Hz (limit {self.limit:g}, "
            f"tolerance {self.tolerance:g})"
        )


def check_passivity(
    network: Network,
    *,
    tolerance: float = ARITHMETIC_TOLERANCE,
) -> QualityResult:
    """Check that the network cannot deliver more power than it receives.

    A passive network has ``sigma_max(S) <= 1`` at every frequency, where
    ``sigma_max`` is the largest singular value of the S matrix. The
    singular values bound the ratio of reflected to incident power over
    every possible excitation, so the test covers all of them at once and
    is stricter than looking at individual ``|S[i, j]|``.

    Parameters
    ----------
    network:
        Source network; it is read, never modified.
    tolerance:
        How far past unity the largest singular value may go. Must be
        finite and non-negative. See ``ARITHMETIC_TOLERANCE`` and
        ``MEASUREMENT_TOLERANCE``.

    Returns
    -------
    QualityResult
        ``metric`` holds ``sigma_max`` at each frequency, dimensionless,
        shape ``(n_freq,)``; ``limit`` is 1.

    Notes
    -----
    The test is invariant under a real orthogonal port transform, so a
    mixed-mode matrix built with the 1/sqrt(2) transform has the same
    singular values as the single-ended one it came from.
    """

    _validate_tolerance(tolerance)
    singular_values = np.linalg.svd(network.s, compute_uv=False)
    return QualityResult(
        name=PASSIVITY,
        frequencies_hz=network.frequencies_hz,
        metric=np.ascontiguousarray(singular_values.max(axis=1), dtype=np.float64),
        limit=1.0,
        tolerance=tolerance,
    )


def check_reciprocity(
    network: Network,
    *,
    tolerance: float = ARITHMETIC_TOLERANCE,
) -> QualityResult:
    """Check that the network transmits alike in both directions.

    A reciprocal network has ``S == S.T`` at every frequency. Media that
    break it are magnetized ferrites and active devices; ordinary
    interconnect does not, so an asymmetric measurement of a passive DUT
    points at the measurement or at the code that produced it.

    Parameters
    ----------
    network:
        Source network; it is read, never modified.
    tolerance:
        Largest ``|S[i, j] - S[j, i]|`` that still counts as reciprocal.
        Must be finite and non-negative.

    Returns
    -------
    QualityResult
        ``metric`` holds the largest asymmetry over the matrix at each
        frequency, dimensionless, shape ``(n_freq,)``; ``limit`` is 0.
        A one-port network is symmetric by construction and its metric is
        all zeros.
    """

    _validate_tolerance(tolerance)
    asymmetry = np.abs(network.s - network.s.transpose(0, 2, 1))
    return QualityResult(
        name=RECIPROCITY,
        frequencies_hz=network.frequencies_hz,
        metric=np.ascontiguousarray(asymmetry.max(axis=(1, 2)), dtype=np.float64),
        limit=0.0,
        tolerance=tolerance,
    )


def check_network(
    network: Network,
    *,
    tolerance: float = ARITHMETIC_TOLERANCE,
) -> tuple[QualityResult, ...]:
    """Run every implemented check against one network.

    Causality is specified in ``ALGORITHM_GUIDE.md`` §12.5 but is not
    implemented: its reference method is still undecided, so this returns
    passivity and reciprocity only.
    """

    return (
        check_passivity(network, tolerance=tolerance),
        check_reciprocity(network, tolerance=tolerance),
    )


def _validate_tolerance(tolerance: float) -> None:
    if not np.isfinite(tolerance) or tolerance < 0.0:
        raise InputValidationError(
            f"Quality check tolerance must be finite and non-negative, got {tolerance}."
        )
