"""Single-ended to mixed-mode S-parameter conversion.

Convention
----------
Power-invariant transform with 1/sqrt(2) factors::

    a_d = (a_p - a_n) / sqrt(2)
    a_c = (a_p + a_n) / sqrt(2)

The transform matrix M is orthogonal, so ``S_mm = M @ S @ M.T``. Differential
ports then reference ``2 * z0`` and common ports ``z0 / 2``.

Output ports are in block order -- every differential port, then every common
port -- so the result reads as ``[[Sdd, Sdc], [Scd, Scc]]``. Within a block,
ports run line by line, near end before far end.

Reference: Bockelman & Eisenstadt, "Combined differential and common-mode
scattering parameters", IEEE MTT 43(7), 1995.
"""

import numpy as np
from numpy.typing import NDArray

from interconnect_studio.core import (
    InputValidationError,
    MixedModeNetwork,
    Network,
    PortGroup,
)

_INV_SQRT2 = 1.0 / np.sqrt(2.0)


def to_mixed_mode(network: Network, port_group: PortGroup) -> MixedModeNetwork:
    """Convert a single-ended network to mixed-mode.

    Parameters
    ----------
    network:
        Single-ended network. Its port count must match ``port_group``.
    port_group:
        Which ports pair up, and with what polarity. Every line must be
        differential; tuple order within a line sets the positive conductor.

    Returns
    -------
    MixedModeNetwork
        Shape ``(n_freq, n_port, n_port)`` in block order.
    """

    if not isinstance(port_group, PortGroup):
        raise InputValidationError("port_group must be a PortGroup.")
    if not port_group.is_differential:
        raise InputValidationError(
            "Mixed-mode conversion requires every line to be differential."
        )
    port_group.validate_covers(network.n_ports)

    transform = _transform_matrix(port_group, network.n_ports)
    mixed = transform @ network.s @ transform.T

    return MixedModeNetwork(
        frequencies_hz=network.frequencies_hz,
        s=mixed,
        z0_differential=2.0 * network.z0,
        z0_common=network.z0 / 2.0,
        port_group=port_group,
    )


def _transform_matrix(port_group: PortGroup, n_ports: int) -> NDArray[np.float64]:
    """Build M so that ``M @ S @ M.T`` is the block-ordered mixed-mode matrix.

    Row ``k`` of M expresses mixed-mode port ``k`` as a combination of the
    single-ended ports it is built from.
    """

    n_mode_ports = n_ports // 2
    transform = np.zeros((n_ports, n_ports), dtype=np.float64)

    row = 0
    for line in port_group.lines:
        for end in (line.near, line.far):
            positive, negative = end
            # Differential rows occupy the first half, common rows the second,
            # keeping the matrix in [[Sdd, Sdc], [Scd, Scc]] block order.
            transform[row, positive] = _INV_SQRT2
            transform[row, negative] = -_INV_SQRT2
            transform[n_mode_ports + row, positive] = _INV_SQRT2
            transform[n_mode_ports + row, negative] = _INV_SQRT2
            row += 1

    return transform
