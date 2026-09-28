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

The transform runs both ways. ``M`` is orthogonal, so recovering the
single-ended matrix from a balanced one is ``M.T @ S_mm @ M`` -- no
inverse, no conditioning to worry about. That is what lets a file holding
only balanced parameters be read as an ordinary network.

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


def to_single_ended(mixed: MixedModeNetwork) -> Network:
    """Recover the single-ended network a mixed-mode matrix came from.

    Parameters
    ----------
    mixed:
        Balanced network. Its ``port_group`` says which single-ended ports
        each mode port is built from, so the answer is unique.

    Returns
    -------
    Network
        Same frequencies (Hz, shape ``(n_freq,)``) and matrix shape, with
        ``z0`` the single-ended reference the mode impedances imply.

    Raises
    ------
    InputValidationError
        If the two mode reference impedances do not describe one
        single-ended ``z0``.

    Notes
    -----
    ``M`` is orthogonal, so this is a transpose rather than an inverse and
    round-trips to machine precision. Port names are not recovered: a
    mixed-mode network never carried them.
    """

    if not isinstance(mixed, MixedModeNetwork):
        raise InputValidationError("mixed must be a MixedModeNetwork.")

    z0 = _single_ended_reference(mixed)
    n_ports = mixed.s.shape[1]
    mixed.port_group.validate_covers(n_ports)

    transform = _transform_matrix(mixed.port_group, n_ports)
    single_ended = transform.T @ mixed.s @ transform

    return Network(mixed.frequencies_hz, single_ended, z0=z0)


def _single_ended_reference(mixed: MixedModeNetwork) -> complex:
    """The ``z0`` implied by a pair of mode reference impedances.

    A differential port references ``2 * z0`` and a common port ``z0 / 2``,
    so the two must agree on one ``z0``. They can disagree only if the
    network was built by hand, and then there is no honest answer to pick.
    """

    from_differential = mixed.z0_differential / 2.0
    from_common = mixed.z0_common * 2.0
    if not np.isclose(from_differential, from_common, rtol=1e-12, atol=0.0):
        raise InputValidationError(
            "Mode reference impedances disagree on the single-ended z0: "
            f"{mixed.z0_differential} / 2 is {from_differential}, but "
            f"{mixed.z0_common} * 2 is {from_common}."
        )
    return complex(from_differential)


def _transform_matrix(port_group: PortGroup, n_ports: int) -> NDArray[np.float64]:
    """Build M so that ``M @ S @ M.T`` is the block-ordered mixed-mode matrix.

    Row ``k`` of M expresses mixed-mode port ``k`` as a combination of the
    single-ended ports it is built from.
    """

    n_mode_ports = n_ports // 2
    transform = np.zeros((n_ports, n_ports), dtype=np.float64)

    row = 0
    for line in port_group.lines:
        for end in line.ends:
            positive, negative = end
            # Differential rows occupy the first half, common rows the second,
            # keeping the matrix in [[Sdd, Sdc], [Scd, Scc]] block order.
            transform[row, positive] = _INV_SQRT2
            transform[row, negative] = -_INV_SQRT2
            transform[n_mode_ports + row, positive] = _INV_SQRT2
            transform[n_mode_ports + row, negative] = _INV_SQRT2
            row += 1

    return transform
