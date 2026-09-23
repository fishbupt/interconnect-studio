"""Build one network from parameters of several files.

Mirrors PLTS "Import Multiple Files (Build a File)" for single-ended data:
every DUT parameter ``S[i, j]`` is copied from one parameter of one source
file. Assignments are made per parameter, or per port, where mapping file
ports ``(k, l)`` onto DUT ports ``(i, j)`` assigns every ``S[i, j]`` whose two
ports both come from that file. Later assignments overwrite earlier ones, as
in PLTS. The build succeeds only when every DUT parameter is assigned.

No resampling takes place: all sources must share one frequency grid and one
reference impedance.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np

from interconnect_studio.core import InputValidationError, Network

# Relative tolerance for treating two frequency grids as the same grid.
FREQUENCY_MATCH_RTOL = 1e-9


@dataclass(frozen=True, slots=True)
class ParameterAssignment:
    """Copy ``sources[source].s[:, source_row, source_col]`` into DUT ``S[row, col]``.

    All indices are 0-based.
    """

    row: int
    col: int
    source: int
    source_row: int
    source_col: int


def port_assignments(
    source: int,
    source_ports: Sequence[int],
    destination_ports: Sequence[int],
) -> tuple[ParameterAssignment, ...]:
    """Assignments for mapping file ports onto DUT ports (0-based, same order).

    Every pair of listed ports yields one assignment, so mapping ports
    ``(0, 1)`` of a 2-port file onto DUT ports ``(4, 5)`` assigns S55, S56,
    S65 and S66 (1-based).
    """

    if len(source_ports) != len(destination_ports):
        raise InputValidationError("Source and destination port lists differ in length.")
    if len(set(destination_ports)) != len(destination_ports):
        raise InputValidationError("Destination ports must be unique.")
    pairs = list(zip(source_ports, destination_ports, strict=True))
    return tuple(
        ParameterAssignment(row, col, source, source_row, source_col)
        for source_row, row in pairs
        for source_col, col in pairs
    )


def missing_parameters(
    n_ports: int, assignments: Iterable[ParameterAssignment]
) -> tuple[tuple[int, int], ...]:
    """DUT parameters (0-based row, col) no assignment covers, in row-major order."""

    covered = {(item.row, item.col) for item in assignments}
    return tuple(
        (row, col)
        for row in range(n_ports)
        for col in range(n_ports)
        if (row, col) not in covered
    )


def build_network(
    sources: Sequence[Network],
    n_ports: int,
    assignments: Sequence[ParameterAssignment],
) -> Network:
    """Assemble an ``n_ports`` network from source parameters.

    Raises ``InputValidationError`` when a parameter is unassigned, an index
    is out of range, or the sources do not share frequencies and ``z0``.
    """

    if n_ports < 1:
        raise InputValidationError("A built network needs at least one port.")
    if not sources:
        raise InputValidationError("A build needs at least one source file.")
    reference = sources[0]
    for index, network in enumerate(sources[1:], start=1):
        _check_compatible(reference, network, index)

    missing = missing_parameters(n_ports, assignments)
    if missing:
        names = ", ".join(f"S{row + 1},{col + 1}" for row, col in missing[:6])
        more = "" if len(missing) <= 6 else f" and {len(missing) - 6} more"
        raise InputValidationError(f"Unassigned DUT parameters: {names}{more}.")

    s = np.empty((reference.n_freq, n_ports, n_ports), dtype=np.complex128)
    for item in assignments:
        if not (0 <= item.row < n_ports and 0 <= item.col < n_ports):
            raise InputValidationError(
                f"DUT parameter S{item.row + 1},{item.col + 1} is outside {n_ports} ports."
            )
        if not 0 <= item.source < len(sources):
            raise InputValidationError(f"Source index {item.source} does not exist.")
        s[:, item.row, item.col] = sources[item.source].s_parameter(
            item.source_row, item.source_col
        )
    return Network(frequencies_hz=reference.frequencies_hz, s=s, z0=reference.z0)


def _check_compatible(reference: Network, network: Network, index: int) -> None:
    if network.n_freq != reference.n_freq or not np.allclose(
        network.frequencies_hz, reference.frequencies_hz, rtol=FREQUENCY_MATCH_RTOL, atol=0.0
    ):
        raise InputValidationError(
            f"Source {index + 1} has a different frequency grid; files built together "
            "must share their frequency points (no interpolation is performed)."
        )
    if network.z0 != reference.z0:
        raise InputValidationError(
            f"Source {index + 1} has reference impedance {network.z0}, "
            f"source 1 has {reference.z0}."
        )
