"""Tab- or comma-delimited text S-parameter reader.

PLTS imports "Text (tab delimited)" and "Text (comma delimited)" files but
its help only documents the time-domain layout of its text export. The
frequency-domain layout read here follows that export's conventions:

- lines starting with ``!`` are comments; ``! XDATA UNIT <unit>`` sets the
  frequency unit (Hz, kHz, MHz or GHz; Hz when absent)
- ``BEGIN`` and ``END`` lines are ignored
- one header line, optionally starting with ``%``, names the columns: the
  first is frequency (a unit in parentheses, e.g. ``freq(GHz)``, overrides
  ``XDATA UNIT``), the others are ``S21(real)`` / ``S21(imag)`` pairs; ports
  of 10 and above are written ``S[12,3](real)``
- every following line holds one frequency point

Columns may appear in any order, but each S-parameter needs both parts and
the matrix must be complete. Text has no reference impedance field, so the
reference impedance is passed in by the caller.
"""

import re
from pathlib import Path
from typing import Final, Literal

import numpy as np
from numpy.typing import NDArray

from interconnect_studio.core import DataFormatError, Network
from interconnect_studio.io.touchstone import FREQUENCY_SCALE, read_text_file

TextDelimiter = Literal["tab", "comma"]

_SEPARATORS: Final[dict[str, str]] = {"tab": "\t", "comma": ","}
_COLUMN: Final[re.Pattern[str]] = re.compile(
    r"^S(?:\[(?P<row>\d+),(?P<col>\d+)\]|(?P<row1>\d)(?P<col1>\d))\((?P<part>real|imag)\)$",
    re.IGNORECASE,
)
_FREQUENCY_COLUMN: Final[re.Pattern[str]] = re.compile(
    r"^freq(?:uency)?(?:\((?P<unit>[a-z]+)\))?$", re.IGNORECASE
)
_XDATA_UNIT: Final[re.Pattern[str]] = re.compile(r"^!\s*XDATA\s+UNIT\s+(?P<unit>\S+)", re.I)


def read_text_network(
    path: str | Path,
    delimiter: TextDelimiter,
    z0: complex = 50.0,
) -> Network:
    """Read a tab- or comma-delimited S-parameter table into a Network.

    ``z0`` is the reference impedance in ohms the data was measured in.
    """

    if delimiter not in _SEPARATORS:
        raise DataFormatError(f"Unsupported text delimiter '{delimiter}'.")
    file_path = Path(path)
    text = read_text_file(file_path, "Text")
    separator = _SEPARATORS[delimiter]

    unit = "hz"
    columns: list[tuple[int, int, str]] | None = None
    rows: list[list[float]] = []

    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("!"):
            match = _XDATA_UNIT.match(line)
            if match is not None:
                unit = _unit(match.group("unit"), line_number)
            continue
        if line.upper() in {"BEGIN", "END"}:
            continue

        fields = [field.strip() for field in line.lstrip("%").split(separator)]
        if columns is None:
            columns, header_unit = _header(fields, line_number, delimiter)
            unit = header_unit or unit
            continue
        if len(fields) != len(columns) + 1:
            raise DataFormatError(
                f"Line {line_number} has {len(fields)} {delimiter}-separated values, "
                f"expected {len(columns) + 1}."
            )
        rows.append([_float(value, line_number) for value in fields])

    if columns is None:
        raise DataFormatError("Text file has no column header line.")
    if not rows:
        raise DataFormatError("Text file contains no data rows.")
    return _build_network(np.asarray(rows, dtype=np.float64), columns, unit, z0)


def _header(
    fields: list[str], line_number: int, delimiter: str
) -> tuple[list[tuple[int, int, str]], str | None]:
    if len(fields) < 3:
        raise DataFormatError(
            f"Header at line {line_number} has fewer than three {delimiter}-separated "
            "columns; check the delimiter."
        )
    frequency = _FREQUENCY_COLUMN.match(fields[0].replace(" ", ""))
    if frequency is None:
        raise DataFormatError(
            f"First column must be frequency, got '{fields[0]}' (line {line_number})."
        )
    unit = frequency.group("unit")
    columns: list[tuple[int, int, str]] = []
    for name in fields[1:]:
        match = _COLUMN.match(name.replace(" ", ""))
        if match is None:
            raise DataFormatError(
                f"Column '{name}' is not of the form S21(real) / S21(imag) (line {line_number})."
            )
        row = int(match.group("row") or match.group("row1"))
        col = int(match.group("col") or match.group("col1"))
        if row < 1 or col < 1:
            raise DataFormatError(f"Column '{name}' uses a port number below 1.")
        columns.append((row - 1, col - 1, match.group("part").lower()))
    if len(set(columns)) != len(columns):
        raise DataFormatError(f"Duplicate S-parameter columns (line {line_number}).")
    return columns, _unit(unit, line_number) if unit else None


def _build_network(
    table: NDArray[np.float64],
    columns: list[tuple[int, int, str]],
    unit: str,
    z0: complex,
) -> Network:
    n_ports = max(max(row, col) for row, col, _ in columns) + 1
    parts = {(row, col, part): index + 1 for index, (row, col, part) in enumerate(columns)}
    missing = [
        f"S{row + 1}{col + 1}({part})"
        for row in range(n_ports)
        for col in range(n_ports)
        for part in ("real", "imag")
        if (row, col, part) not in parts
    ]
    if missing:
        raise DataFormatError(f"Text S-parameter matrix is incomplete; missing {missing[:4]}...")

    s: NDArray[np.complex128] = np.empty((table.shape[0], n_ports, n_ports), dtype=np.complex128)
    for row in range(n_ports):
        for col in range(n_ports):
            s[:, row, col] = table[:, parts[(row, col, "real")]] + 1j * table[
                :, parts[(row, col, "imag")]
            ]
    try:
        return Network(frequencies_hz=table[:, 0] * FREQUENCY_SCALE[unit], s=s, z0=z0)
    except ValueError as exc:
        raise DataFormatError(f"Text data violates Network invariants: {exc}") from exc


def _unit(text: str, line_number: int) -> str:
    unit = text.lower()
    if unit not in FREQUENCY_SCALE:
        raise DataFormatError(f"Unsupported frequency unit '{text}' (line {line_number}).")
    return unit


def _float(text: str, line_number: int) -> float:
    try:
        return float(text)
    except ValueError as exc:
        raise DataFormatError(f"Invalid number '{text}' (line {line_number}).") from exc
