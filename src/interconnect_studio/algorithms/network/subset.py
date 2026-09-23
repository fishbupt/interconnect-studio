"""Frequency range subset without resampling.

PLTS "Limit Data Range to Import: Subset" can also change the point count and
step, which requires interpolation. Interconnect Studio only narrows the
range: the measured points inside ``[start_hz, stop_hz]`` are kept unchanged,
so no interpolated data is ever produced.
"""

import numpy as np

from interconnect_studio.core import InputValidationError, Network


def subset_frequency_range(network: Network, start_hz: float, stop_hz: float) -> Network:
    """Keep the measured points with ``start_hz <= f <= stop_hz``.

    Parameters
    ----------
    network:
        Source network.
    start_hz, stop_hz:
        Inclusive range limits in Hz. The range must overlap the measured
        span and keep at least one point; it may not reach beyond the
        measurement (as in PLTS, a subset cannot be larger than the data).

    Returns
    -------
    Network
        A new Network with the selected points; ``z0`` and port names are
        unchanged.
    """

    if not np.isfinite(start_hz) or not np.isfinite(stop_hz):
        raise InputValidationError("Subset start and stop must be finite.")
    if start_hz > stop_hz:
        raise InputValidationError("Subset start must not exceed stop.")
    frequencies = network.frequencies_hz
    if start_hz < frequencies[0] or stop_hz > frequencies[-1]:
        raise InputValidationError(
            f"Subset {start_hz:g}-{stop_hz:g} Hz reaches beyond the measured range "
            f"{frequencies[0]:g}-{frequencies[-1]:g} Hz."
        )
    keep = (frequencies >= start_hz) & (frequencies <= stop_hz)
    if not np.any(keep):
        raise InputValidationError(
            f"No measured point lies within {start_hz:g}-{stop_hz:g} Hz."
        )
    return Network(
        frequencies_hz=frequencies[keep],
        s=network.s[keep],
        z0=network.z0,
        port_names=network.port_names,
    )


def subset_point_count(network: Network, start_hz: float, stop_hz: float) -> int:
    """Number of measured points ``subset_frequency_range`` would keep."""

    frequencies = network.frequencies_hz
    return int(np.count_nonzero((frequencies >= start_hz) & (frequencies <= stop_hz)))
