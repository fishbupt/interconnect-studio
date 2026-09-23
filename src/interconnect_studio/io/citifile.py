"""CITIfile S-parameter reader.

Follows the Keysight CITIfile definition (revisions A.01.00 / A.01.01), as
summarised in the PLTS help topic *CITIfile Format*:

- ``VAR FREQ MAG <n>`` declares the frequency variable, in Hz
- frequencies come from ``VAR_LIST_BEGIN`` ... ``VAR_LIST_END`` or from a
  single linear segment ``SEG_LIST_BEGIN`` / ``SEG start stop n`` /
  ``SEG_LIST_END``
- ``DATA S[i,j] RI`` declares one S-parameter array; the arrays follow as
  ``BEGIN`` ... ``END`` blocks of ``real,imag`` lines, in declaration order
- ``#`` device keywords, ``CONSTANT``, ``COMMENT`` and ``NAME`` are ignored;
  data arrays other than ``S`` (error terms and so on) are read and dropped

Only RI data exists in the CITIfile definition. The format has no reference
impedance field, so networks are built with an assumed ``z0 = 50`` ohms
(recorded as an open item in ``docs/PRODUCT.md`` FR-001). A file with several
packages is rejected.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import numpy as np
from numpy.typing import NDArray

from interconnect_studio.core import DataFormatError, Network
from interconnect_studio.io.touchstone import read_text_file

CITIFILE_Z0_OHM: Final[complex] = complex(50.0)

_S_NAME: Final[re.Pattern[str]] = re.compile(
    r"^S(?:\[(?P<row>\d+),(?P<col>\d+)\]|(?P<row1>\d)(?P<col1>\d))$", re.IGNORECASE
)


@dataclass(slots=True)
class _Package:
    n_points: int | None = None
    frequencies: list[float] = field(default_factory=list)
    arrays: list[tuple[str, str]] = field(default_factory=list)  # (name, format)
    blocks: list[list[complex]] = field(default_factory=list)


def read_citifile(path: str | Path) -> Network:
    """Read the S-parameters of a CITIfile into a Network."""

    file_path = Path(path)
    package = _parse(read_text_file(file_path, "CITIfile"))
    return _build_network(package)


def _parse(text: str) -> _Package:
    package = _Package()
    citifile_seen = False
    section: str | None = None  # "var_list", "seg_list", "data"

    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        keyword, _, rest = line.partition(" ")
        keyword = keyword.upper()
        rest = rest.strip()

        if section == "var_list":
            if keyword == "VAR_LIST_END":
                section = None
            else:
                package.frequencies.append(_float(line, line_number))
            continue
        if section == "seg_list":
            if keyword == "SEG_LIST_END":
                section = None
            elif keyword == "SEG":
                package.frequencies.extend(_segment(rest, line_number))
            else:
                raise DataFormatError(f"Unexpected line in SEG_LIST (line {line_number}).")
            continue
        if section == "data":
            if keyword == "END":
                section = None
            else:
                package.blocks[-1].append(_complex(line, line_number))
            continue

        if keyword == "CITIFILE":
            if citifile_seen:
                raise DataFormatError("CITIfiles with more than one package are not supported.")
            citifile_seen = True
        elif not citifile_seen:
            raise DataFormatError("A CITIfile must start with the CITIFILE keyword.")
        elif keyword == "VAR":
            package.n_points = _var(rest, line_number)
        elif keyword == "DATA":
            parts = rest.split()
            if len(parts) != 2:
                raise DataFormatError(f"DATA needs a name and a format (line {line_number}).")
            package.arrays.append((parts[0], parts[1].upper()))
        elif keyword == "VAR_LIST_BEGIN":
            section = "var_list"
        elif keyword == "SEG_LIST_BEGIN":
            section = "seg_list"
        elif keyword == "BEGIN":
            package.blocks.append([])
            section = "data"
        elif keyword in {"NAME", "CONSTANT", "COMMENT"} or keyword.startswith("#"):
            continue
        else:
            raise DataFormatError(f"Unsupported CITIfile keyword '{keyword}' (line {line_number}).")

    if section is not None:
        raise DataFormatError("CITIfile ends inside an unterminated list or data block.")
    if not citifile_seen:
        raise DataFormatError("A CITIfile must start with the CITIFILE keyword.")
    return package


def _build_network(package: _Package) -> Network:
    if package.n_points is None:
        raise DataFormatError("CITIfile has no VAR FREQ declaration.")
    if not package.frequencies:
        raise DataFormatError("CITIfile has no frequency list (VAR_LIST or SEG_LIST).")
    if len(package.frequencies) != package.n_points:
        raise DataFormatError(
            f"VAR declares {package.n_points} points but the frequency list has "
            f"{len(package.frequencies)}."
        )
    if len(package.blocks) != len(package.arrays):
        raise DataFormatError(
            f"CITIfile declares {len(package.arrays)} DATA arrays but has "
            f"{len(package.blocks)} BEGIN/END blocks."
        )

    parameters: dict[tuple[int, int], list[complex]] = {}
    for (name, data_format), block in zip(package.arrays, package.blocks, strict=True):
        position = _s_position(name)
        if position is None:
            continue
        if data_format != "RI":
            raise DataFormatError(f"DATA {name} uses format {data_format}; only RI is defined.")
        if len(block) != package.n_points:
            raise DataFormatError(
                f"DATA {name} has {len(block)} values, expected {package.n_points}."
            )
        if position in parameters:
            raise DataFormatError(f"DATA {name} is declared twice.")
        parameters[position] = block

    if not parameters:
        raise DataFormatError("CITIfile contains no S-parameter data.")
    n_ports = max(max(row, col) for row, col in parameters) + 1
    missing = [
        f"S[{row + 1},{col + 1}]"
        for row in range(n_ports)
        for col in range(n_ports)
        if (row, col) not in parameters
    ]
    if missing:
        raise DataFormatError(
            f"CITIfile S-parameter matrix is incomplete; missing {', '.join(missing)}."
        )

    s: NDArray[np.complex128] = np.empty((package.n_points, n_ports, n_ports), dtype=np.complex128)
    for (row, col), values in parameters.items():
        s[:, row, col] = values

    try:
        return Network(frequencies_hz=package.frequencies, s=s, z0=CITIFILE_Z0_OHM)
    except ValueError as exc:
        raise DataFormatError(f"CITIfile data violates Network invariants: {exc}") from exc


def _s_position(name: str) -> tuple[int, int] | None:
    match = _S_NAME.match(name)
    if match is None:
        return None
    row = int(match.group("row") or match.group("row1"))
    col = int(match.group("col") or match.group("col1"))
    if row < 1 or col < 1:
        raise DataFormatError(f"CITIfile array {name} uses a port number below 1.")
    return row - 1, col - 1


def _var(rest: str, line_number: int) -> int:
    parts = rest.split()
    if len(parts) != 3 or parts[0].upper() != "FREQ":
        raise DataFormatError(
            f"Only 'VAR FREQ MAG <points>' is supported, got 'VAR {rest}' (line {line_number})."
        )
    try:
        n_points = int(parts[2])
    except ValueError as exc:
        raise DataFormatError(f"Invalid point count in VAR (line {line_number}).") from exc
    if n_points < 1:
        raise DataFormatError(f"VAR point count must be positive (line {line_number}).")
    return n_points


def _segment(rest: str, line_number: int) -> list[float]:
    parts = rest.split()
    if len(parts) != 3:
        raise DataFormatError(f"SEG needs start, stop and points (line {line_number}).")
    start, stop = _float(parts[0], line_number), _float(parts[1], line_number)
    try:
        count = int(parts[2])
    except ValueError as exc:
        raise DataFormatError(f"Invalid SEG point count (line {line_number}).") from exc
    return [float(value) for value in np.linspace(start, stop, count)]


def _float(text: str, line_number: int) -> float:
    try:
        return float(text)
    except ValueError as exc:
        raise DataFormatError(f"Invalid number '{text}' (line {line_number}).") from exc


def _complex(line: str, line_number: int) -> complex:
    parts = [part for part in re.split(r"[,\s]+", line) if part]
    if len(parts) != 2:
        raise DataFormatError(f"Expected 'real,imag' in data block (line {line_number}).")
    return complex(_float(parts[0], line_number), _float(parts[1], line_number))
