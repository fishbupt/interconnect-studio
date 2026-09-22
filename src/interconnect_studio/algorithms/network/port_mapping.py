"""Port mapping for Network objects."""

from collections.abc import Sequence

import numpy as np

from interconnect_studio.core import InputValidationError, Network


def remap_ports(network: Network, port_order: Sequence[int]) -> Network:
    """Return a new Network with ports reordered.

    Parameters
    ----------
    network:
        Source network.
    port_order:
        Zero-based permutation using ``new port -> old port`` semantics.
        For example, ``(2, 0, 3, 1)`` on a 4-port network means that new
        ports 0, 1, 2, 3 correspond to old ports 2, 0, 3, 1.

    Returns
    -------
    Network
        A new immutable Network whose S-parameter rows and columns, and
        optional port names, are reordered consistently.

    Raises
    ------
    InputValidationError
        If ``port_order`` is not a complete permutation of all source ports.
    """

    order = _validate_port_order(port_order, network.n_ports)
    indices = np.asarray(order, dtype=np.intp)

    remapped_s = network.s[:, indices, :][:, :, indices]
    remapped_names = (
        tuple(network.port_names[index] for index in order)
        if network.port_names is not None
        else None
    )

    return Network(
        frequencies_hz=network.frequencies_hz,
        s=remapped_s,
        z0=network.z0,
        port_names=remapped_names,
    )


def _validate_port_order(port_order: Sequence[int], n_ports: int) -> tuple[int, ...]:
    if isinstance(port_order, (str, bytes)):
        raise InputValidationError("port_order must be a sequence of integer port indices.")

    order = tuple(port_order)
    if len(order) != n_ports:
        raise InputValidationError(
            f"port_order must contain exactly {n_ports} entries, got {len(order)}."
        )
    if any(isinstance(index, bool) or not isinstance(index, int) for index in order):
        raise InputValidationError("port_order must contain only integer port indices.")
    if any(index < 0 or index >= n_ports for index in order):
        raise InputValidationError(
            f"port_order indices must be in the range [0, {n_ports - 1}]."
        )
    if len(set(order)) != n_ports:
        raise InputValidationError("port_order must contain each port exactly once.")

    return order
