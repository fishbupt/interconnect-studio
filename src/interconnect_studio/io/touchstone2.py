"""Touchstone 2.0 (``.ts``) S-parameter reader.

Implements the keyword subset needed for S-parameter network data:

- ``[Version] 2.0`` (must be the first keyword), option line ``# ...``
- ``[Number of Ports]``, ``[Two-Port Data Order]`` (required for 2 ports)
- ``[Number of Frequencies]``, ``[Reference]``, ``[Matrix Format]``
- ``[Network Data]`` ... ``[End]``; ``[Noise Data]`` ends network data
- ``[Begin Information]`` ... ``[End Information]`` is skipped

- ``[Mixed-Mode Order]``; see below

Per-port reference impedances must all be equal, because ``Network`` carries
one scalar ``z0`` (``DOMAIN_MODEL.md`` §5); PLTS rejects such files on import
as well.

Mixed-mode data
---------------
``[Mixed-Mode Order]`` lists one descriptor per matrix row: ``S<n>`` for a
single-ended port, ``D<n>,<m>`` and ``C<n>,<m>`` for the two modes of the
pair formed by ports n and m (1-based, as everywhere in the file).

Such a file is read back to a single-ended ``Network``, which makes it an
ordinary measurement everywhere downstream -- the Balanced view recomputes
the mixed-mode matrix from it, so nothing has to special-case where the data
came from. ``M`` is orthogonal, so the recovery is exact.

The declared pairing is returned alongside, as a ``PortGroup``: the file says
which ports form a pair and which conductor is positive, but **not** which
pairs are the two ends of one line, so each pair becomes a ``Line`` with no
far end rather than a guessed through path.

This module imports ``algorithms.mixed_mode`` for that recovery. It is the
one place ``io`` reaches into ``algorithms``; see ``ARCHITECTURE.md`` §3.
"""

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import numpy as np
from numpy.typing import NDArray

from interconnect_studio.algorithms.mixed_mode import to_single_ended
from interconnect_studio.core import (
    DataFormatError,
    InputValidationError,
    Line,
    MixedModeNetwork,
    Network,
    PortGroup,
)
from interconnect_studio.io.touchstone import (
    FREQUENCY_SCALE,
    TouchstoneOptions,
    pairs_to_complex,
    parse_numeric_tokens,
    parse_option_line,
    read_text_file,
)

_KEYWORD: Final[re.Pattern[str]] = re.compile(r"^\[(?P<name>[^\]]+)\](?P<rest>.*)$")
_MATRIX_FORMATS: Final[set[str]] = {"full", "lower", "upper"}
_DESCRIPTOR: Final[re.Pattern[str]] = re.compile(
    r"^(?P<kind>[SDC])(?P<first>\d+)(?:,(?P<second>\d+))?$", re.IGNORECASE
)


@dataclass(slots=True)
class _Header:
    version_seen: bool = False
    options: TouchstoneOptions | None = None
    n_ports: int | None = None
    two_port_order: str | None = None
    n_frequencies: int | None = None
    references: list[float] = field(default_factory=list)
    matrix_format: str = "full"
    mixed_mode_order: list[str] = field(default_factory=list)


def read_touchstone2(path: str | Path) -> Network:
    """Read a Touchstone 2.0 S-parameter file into a Network.

    A mixed-mode file is converted back to single-ended; use
    ``read_touchstone2_with_pairs`` when the declared pairing is wanted too.
    """

    network, _ = read_touchstone2_with_pairs(path)
    return network


def read_touchstone2_with_pairs(
    path: str | Path,
) -> tuple[Network, PortGroup | None]:
    """Read a Touchstone 2.0 file, reporting any mixed-mode pairing.

    Returns
    -------
    tuple
        The single-ended network, and the ``PortGroup`` that
        ``[Mixed-Mode Order]`` declared, or ``None`` for a single-ended
        file. Each pair is a ``Line`` with no far end: the file states the
        pairing and the polarity, not which pairs face each other.
    """

    file_path = Path(path)
    text = read_text_file(file_path, "Touchstone 2.0")

    header = _Header()
    tokens: list[str] = []
    state = "header"  # header -> reference -> data -> done
    in_information = False

    for line_number, original_line in enumerate(text.splitlines(), start=1):
        line = original_line.split("!", maxsplit=1)[0].strip()
        if not line:
            continue

        keyword = _KEYWORD.match(line)
        if keyword is not None:
            name = " ".join(keyword.group("name").lower().split())
            rest = keyword.group("rest").strip()
            if in_information:
                in_information = name != "end information"
                continue
            if state == "done":
                break
            state = _apply_keyword(header, name, rest, line_number, state)
            if name == "begin information":
                in_information = True
            continue

        if in_information or state == "done":
            continue
        if line.startswith("#"):
            if not header.version_seen:
                raise DataFormatError("[Version] must precede the option line.")
            if header.options is not None:
                raise DataFormatError(f"Multiple option lines (line {line_number}).")
            header.options = parse_option_line(line, line_number)
            continue
        if state == "reference":
            header.references.extend(_parse_floats(line.split(), line_number))
            continue
        if state == "data":
            tokens.extend(line.split())
            continue
        raise DataFormatError(f"Unexpected content outside [Network Data] (line {line_number}).")

    if header.mixed_mode_order:
        return _build_from_mixed_mode(header, tokens)
    return _build_network(header, tokens), None


def _apply_keyword(header: _Header, name: str, rest: str, line_number: int, state: str) -> str:
    if not header.version_seen:
        if name != "version":
            raise DataFormatError("A Touchstone 2.0 file must start with [Version].")
        if rest.split()[:1] != ["2.0"]:
            raise DataFormatError(f"Unsupported Touchstone version '{rest}'.")
        header.version_seen = True
        return state

    if name == "number of ports":
        header.n_ports = _parse_positive_int(rest, name, line_number)
    elif name == "two-port data order":
        order = rest.strip()
        if order not in {"12_21", "21_12"}:
            raise DataFormatError(f"Invalid [Two-Port Data Order] '{rest}' (line {line_number}).")
        header.two_port_order = order
    elif name == "number of frequencies":
        header.n_frequencies = _parse_positive_int(rest, name, line_number)
    elif name == "number of noise frequencies":
        pass
    elif name == "reference":
        header.references.extend(_parse_floats(rest.split(), line_number))
        return "reference"
    elif name == "matrix format":
        matrix_format = rest.strip().lower()
        if matrix_format not in _MATRIX_FORMATS:
            raise DataFormatError(f"Invalid [Matrix Format] '{rest}' (line {line_number}).")
        header.matrix_format = matrix_format
    elif name == "mixed-mode order":
        if not rest:
            raise DataFormatError(f"[Mixed-Mode Order] lists no ports (line {line_number}).")
        header.mixed_mode_order.extend(rest.split())
    elif name == "network data":
        return "data"
    elif name in {"noise data", "end"}:
        return "done"
    elif name == "begin information":
        return state
    else:
        raise DataFormatError(f"Unsupported Touchstone 2.0 keyword [{name}] (line {line_number}).")
    return "header" if state == "reference" else state


def _build_network(header: _Header, tokens: list[str]) -> Network:
    if header.options is None:
        raise DataFormatError("Touchstone 2.0 file has no option line.")
    if header.n_ports is None:
        raise DataFormatError("Touchstone 2.0 file has no [Number of Ports].")
    if header.n_frequencies is None:
        raise DataFormatError("Touchstone 2.0 file has no [Number of Frequencies].")
    n_ports = header.n_ports
    if n_ports == 2 and header.two_port_order is None:
        raise DataFormatError("[Two-Port Data Order] is required for 2-port files.")
    if not tokens:
        raise DataFormatError("Touchstone 2.0 file contains no network data.")

    z0 = _reference_impedance(header.references, header.options, n_ports)
    positions = _matrix_positions(n_ports, header.matrix_format, header.two_port_order)
    values_per_point = 1 + 2 * len(positions)
    if len(tokens) != values_per_point * header.n_frequencies:
        raise DataFormatError(
            f"[Number of Frequencies] is {header.n_frequencies}, but the network data does "
            f"not hold that many complete records of {values_per_point} values."
        )

    records = parse_numeric_tokens(tokens).reshape((header.n_frequencies, values_per_point))
    frequencies_hz = records[:, 0] * FREQUENCY_SCALE[header.options.frequency_unit]
    pairs = records[:, 1:].reshape((header.n_frequencies, len(positions), 2))
    values = pairs_to_complex(pairs, header.options.data_format)

    s: NDArray[np.complex128] = np.zeros(
        (header.n_frequencies, n_ports, n_ports), dtype=np.complex128
    )
    for column, (row, col) in enumerate(positions):
        s[:, row, col] = values[:, column]
        if header.matrix_format != "full":
            s[:, col, row] = values[:, column]

    try:
        return Network(frequencies_hz=frequencies_hz, s=s, z0=z0)
    except ValueError as exc:
        raise DataFormatError(f"Touchstone 2.0 data violates Network invariants: {exc}") from exc


def _build_from_mixed_mode(
    header: _Header,
    tokens: list[str],
) -> tuple[Network, PortGroup | None]:
    """Turn a mixed-mode file into the single-ended network it describes."""

    if header.n_ports is None:
        raise DataFormatError("Touchstone 2.0 file has no [Number of Ports].")
    port_group, order = _mixed_mode_layout(header.mixed_mode_order, header.n_ports)

    # Parsed exactly like a single-ended file: the layout keywords describe
    # the matrix, not what its rows mean. Only then are the rows permuted
    # from the file's declared order into the block order the domain model
    # uses, and the z0 read as the single-ended reference each mode is
    # derived from.
    as_read = _build_network(header, tokens)
    permuted = as_read.s[:, order, :][:, :, order]

    try:
        mixed = MixedModeNetwork(
            frequencies_hz=as_read.frequencies_hz,
            s=permuted,
            z0_differential=2.0 * as_read.z0,
            z0_common=as_read.z0 / 2.0,
            port_group=port_group,
        )
        return to_single_ended(mixed), port_group
    except InputValidationError as exc:
        raise DataFormatError(f"Mixed-mode data violates a domain invariant: {exc}") from exc


def _mixed_mode_layout(
    descriptors: list[str],
    n_ports: int,
) -> tuple[PortGroup, list[int]]:
    """Read ``[Mixed-Mode Order]`` into a port group and a row permutation.

    ``order[k]`` is the file row holding our block-order row ``k``: every
    differential mode first, in the order the pairs were declared, then
    every common mode in the same pair order.
    """

    if len(descriptors) != n_ports:
        raise DataFormatError(
            f"[Mixed-Mode Order] lists {len(descriptors)} entries for {n_ports} ports; "
            "a pair contributes one D and one C entry, a single-ended port one S entry."
        )

    pairs: dict[tuple[int, ...], dict[str, int]] = {}
    declared: dict[frozenset[int], tuple[int, ...]] = {}
    single_ended: list[int] = []
    seen: dict[int, str] = {}

    for index, descriptor in enumerate(descriptors):
        kind, ports = _parse_descriptor(descriptor)
        for port in ports:
            if port < 0 or port >= n_ports:
                raise DataFormatError(
                    f"[Mixed-Mode Order] entry {descriptor!r} names port {port + 1}, "
                    f"but the file has {n_ports} ports."
                )
        if kind == "S":
            single_ended.append(ports[0])
            _claim_ports(seen, ports, descriptor)
            continue
        ordered = declared.get(frozenset(ports))
        if ordered is None:
            _claim_ports(seen, ports, descriptor)
            ordered = ports
            declared[frozenset(ports)] = ports
        elif ordered != ports:
            raise DataFormatError(
                f"[Mixed-Mode Order] declares the same pair as "
                f"{ordered[0] + 1},{ordered[1] + 1} and {ports[0] + 1},{ports[1] + 1}; "
                "both modes must name the conductors in the same order, or which one "
                "is positive is ambiguous."
            )
        modes = pairs.setdefault(ordered, {})
        if kind in modes:
            raise DataFormatError(
                f"[Mixed-Mode Order] declares {kind}{ports[0] + 1},{ports[1] + 1} twice."
            )
        modes[kind] = index

    if single_ended:
        names = ", ".join(str(port + 1) for port in sorted(single_ended))
        raise DataFormatError(
            f"[Mixed-Mode Order] mixes single-ended ports ({names}) with differential "
            "pairs. A MixedModeNetwork needs every port paired "
            "(DOMAIN_MODEL.md §7.5), so this file cannot be read yet."
        )

    lines: list[Line] = []
    differential: list[int] = []
    common: list[int] = []
    for number, (ports, modes) in enumerate(pairs.items(), start=1):
        # Stated rather than inferred. The checks above already force both
        # modes to be present -- every pair claims two ports, the entry count
        # equals the port count, and no mode repeats -- but that is a counting
        # argument, and it should not be what keeps a malformed file out.
        missing = {"D", "C"} - set(modes)
        if missing:
            raise DataFormatError(
                f"[Mixed-Mode Order] pair {ports[0] + 1},{ports[1] + 1} has no "
                f"{'/'.join(sorted(missing))} entry; both modes are required."
            )
        lines.append(Line(name=f"Pair {number}", near=ports))
        differential.append(modes["D"])
        common.append(modes["C"])

    try:
        port_group = PortGroup(lines=tuple(lines))
        port_group.validate_covers(n_ports)
    except InputValidationError as exc:
        raise DataFormatError(f"[Mixed-Mode Order] is not a usable port grouping: {exc}") from exc

    return port_group, differential + common


def _parse_descriptor(descriptor: str) -> tuple[str, tuple[int, ...]]:
    """Split one entry into its kind and its 0-based ports."""

    match = _DESCRIPTOR.match(descriptor)
    if match is None:
        raise DataFormatError(
            f"Invalid [Mixed-Mode Order] entry {descriptor!r}; expected S<n>, "
            "D<n>,<m> or C<n>,<m>."
        )
    kind = match.group("kind").upper()
    second = match.group("second")
    if kind == "S":
        if second is not None:
            raise DataFormatError(f"[Mixed-Mode Order] entry {descriptor!r} names two ports.")
        return kind, (int(match.group("first")) - 1,)
    if second is None:
        raise DataFormatError(
            f"[Mixed-Mode Order] entry {descriptor!r} names one port; a mode needs a pair."
        )
    return kind, (int(match.group("first")) - 1, int(second) - 1)


def _claim_ports(seen: dict[int, str], ports: tuple[int, ...], descriptor: str) -> None:
    """Each physical port may appear in one descriptor group only."""

    for port in ports:
        if port in seen:
            raise DataFormatError(
                f"[Mixed-Mode Order] uses port {port + 1} in both {seen[port]!r} "
                f"and {descriptor!r}."
            )
        seen[port] = descriptor


def _reference_impedance(
    references: list[float], options: TouchstoneOptions, n_ports: int
) -> complex:
    if not references:
        return complex(options.reference_resistance)
    if len(references) != n_ports:
        raise DataFormatError(f"[Reference] lists {len(references)} values for {n_ports} ports.")
    first = references[0]
    if any(not math.isclose(value, first) for value in references):
        raise DataFormatError(
            "Port reference impedances differ; a Network needs one reference impedance "
            f"for all ports, got {references}."
        )
    if not math.isfinite(first) or first <= 0.0:
        raise DataFormatError("Reference impedance must be finite and positive.")
    return complex(first)


def _matrix_positions(
    n_ports: int, matrix_format: str, two_port_order: str | None
) -> list[tuple[int, int]]:
    """(row, column) of each value pair in one frequency record."""

    if n_ports == 2 and matrix_format == "full" and two_port_order == "21_12":
        return [(0, 0), (1, 0), (0, 1), (1, 1)]
    if matrix_format == "lower":
        return [(row, col) for row in range(n_ports) for col in range(row + 1)]
    if matrix_format == "upper":
        return [(row, col) for row in range(n_ports) for col in range(row, n_ports)]
    return [(row, col) for row in range(n_ports) for col in range(n_ports)]


def _parse_positive_int(text: str, name: str, line_number: int) -> int:
    try:
        value = int(text.split()[0])
    except (IndexError, ValueError) as exc:
        raise DataFormatError(f"[{name}] needs an integer (line {line_number}).") from exc
    if value < 1:
        raise DataFormatError(f"[{name}] must be positive (line {line_number}).")
    return value


def _parse_floats(tokens: list[str], line_number: int) -> list[float]:
    try:
        return [float(token) for token in tokens]
    except ValueError as exc:
        raise DataFormatError(f"Invalid number in [Reference] (line {line_number}).") from exc
