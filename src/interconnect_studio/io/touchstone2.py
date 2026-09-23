"""Touchstone 2.0 (``.ts``) S-parameter reader.

Implements the keyword subset needed for S-parameter network data:

- ``[Version] 2.0`` (must be the first keyword), option line ``# ...``
- ``[Number of Ports]``, ``[Two-Port Data Order]`` (required for 2 ports)
- ``[Number of Frequencies]``, ``[Reference]``, ``[Matrix Format]``
- ``[Network Data]`` ... ``[End]``; ``[Noise Data]`` ends network data
- ``[Begin Information]`` ... ``[End Information]`` is skipped

Mixed-mode data (``[Mixed-Mode Order]``) is rejected: the result would not be
a single-ended ``Network``. Per-port reference impedances must all be equal,
because ``Network`` carries one scalar ``z0`` (``DOMAIN_MODEL.md`` §5); PLTS
rejects such files on import as well.
"""

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import numpy as np
from numpy.typing import NDArray

from interconnect_studio.core import DataFormatError, Network
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


@dataclass(slots=True)
class _Header:
    version_seen: bool = False
    options: TouchstoneOptions | None = None
    n_ports: int | None = None
    two_port_order: str | None = None
    n_frequencies: int | None = None
    references: list[float] = field(default_factory=list)
    matrix_format: str = "full"


def read_touchstone2(path: str | Path) -> Network:
    """Read a Touchstone 2.0 S-parameter file into a Network."""

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

    return _build_network(header, tokens)


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
        raise DataFormatError(
            "Mixed-mode Touchstone 2.0 data is not supported yet; import single-ended data."
        )
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
