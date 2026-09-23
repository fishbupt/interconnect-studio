"""Touchstone 1.x reader and writer (any port count).

Touchstone 2.0 is read by ``interconnect_studio.io.touchstone2``, which
shares the option-line and number parsing helpers defined here.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

import numpy as np
from numpy.typing import NDArray

from interconnect_studio.core import DataFormatError, Network

_TOUCHSTONE_SUFFIX: Final[re.Pattern[str]] = re.compile(r"^\.s(?P<ports>\d+)p$", re.IGNORECASE)

FREQUENCY_SCALE: Final[dict[str, float]] = {
    "hz": 1.0,
    "khz": 1.0e3,
    "mhz": 1.0e6,
    "ghz": 1.0e9,
}

_SUPPORTED_FORMATS: Final[set[str]] = {"ri", "ma", "db"}
_TOUCHSTONE2_SUFFIX: Final[str] = ".ts"


@dataclass(frozen=True, slots=True)
class TouchstoneOptions:
    frequency_unit: str = "ghz"
    parameter: str = "s"
    data_format: str = "ma"
    reference_resistance: float = 50.0


def read_touchstone(path: str | Path) -> Network:
    """Read a Touchstone 1.x S-parameter file (``.sNp``) into a Network.

    Any port count is accepted. Data formats RI, MA and DB and frequency
    units Hz, kHz, MHz and GHz are supported. Touchstone 2.0 ``.ts`` files
    are read by ``read_touchstone2``.
    """

    file_path = Path(path)
    if file_path.suffix.lower() == _TOUCHSTONE2_SUFFIX:
        raise DataFormatError(
            f"{file_path.name} is a Touchstone 2.0 file; read it with read_touchstone2."
        )

    n_ports = _port_count_from_suffix(file_path)
    if n_ports < 1:
        raise DataFormatError(f"Touchstone port count must be at least 1, got {n_ports}.")
    text = read_text_file(file_path, "Touchstone")

    options = TouchstoneOptions()
    option_seen = False
    numeric_tokens: list[str] = []

    for line_number, original_line in enumerate(text.splitlines(), start=1):
        line = original_line.split("!", maxsplit=1)[0].strip()
        if not line:
            continue

        if line.startswith("["):
            raise DataFormatError(
                f"Touchstone 2.0 keyword syntax is not supported (line {line_number})."
            )

        if line.startswith("#"):
            if option_seen:
                raise DataFormatError(
                    f"Multiple Touchstone option lines are not supported (line {line_number})."
                )
            options = parse_option_line(line, line_number)
            option_seen = True
            continue

        numeric_tokens.extend(line.split())

    values_per_point = 1 + 2 * n_ports * n_ports
    if not numeric_tokens:
        raise DataFormatError("Touchstone file contains no network data.")
    if len(numeric_tokens) % values_per_point != 0:
        raise DataFormatError(
            "Touchstone numeric data does not contain a complete number of frequency records."
        )

    numeric_values = parse_numeric_tokens(numeric_tokens)
    records = numeric_values.reshape((-1, values_per_point))

    frequency_scale = FREQUENCY_SCALE[options.frequency_unit]
    frequencies_hz = records[:, 0] * frequency_scale

    n_freq = records.shape[0]

    pairs = records[:, 1:].reshape((n_freq, n_ports * n_ports, 2))
    complex_values = pairs_to_complex(pairs, options.data_format)

    # Touchstone 1.x orders each data point as:
    #   2 ports:  S11 S21 S12 S22   -- column-major, the only special case
    #   others:   S11 S12 S13 ...   -- row-major, one matrix row per line
    s = complex_values.reshape((n_freq, n_ports, n_ports))
    if n_ports == 2:
        s = s.transpose(0, 2, 1)
    s = np.ascontiguousarray(s)

    try:
        return Network(
            frequencies_hz=frequencies_hz,
            s=s,
            z0=complex(options.reference_resistance),
        )
    except ValueError as exc:
        raise DataFormatError(f"Touchstone data violates Network invariants: {exc}") from exc


def read_text_file(path: Path, kind: str) -> str:
    """Read a text data file, raising ``DataFormatError`` on IO or decoding errors."""

    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise DataFormatError(f"Unable to read {kind} file: {path}") from exc
    except UnicodeError as exc:
        raise DataFormatError(f"{kind} file is not valid UTF-8 text: {path}") from exc


def _port_count_from_suffix(path: Path) -> int:
    match = _TOUCHSTONE_SUFFIX.match(path.suffix)
    if match is None:
        raise DataFormatError(
            f"Expected a Touchstone S-parameter suffix such as .s1p, .s2p or .s4p: {path}"
        )
    return int(match.group("ports"))


def parse_option_line(line: str, line_number: int) -> TouchstoneOptions:
    tokens = line[1:].split()
    if len(tokens) < 3:
        raise DataFormatError(f"Incomplete Touchstone option line at line {line_number}.")

    frequency_unit = tokens[0].lower()
    parameter = tokens[1].lower()
    data_format = tokens[2].lower()

    if frequency_unit not in FREQUENCY_SCALE:
        raise DataFormatError(
            f"Unsupported frequency unit '{tokens[0]}' at line {line_number}."
        )
    if parameter != "s":
        raise DataFormatError(
            f"Only S-parameters are supported, got '{tokens[1]}' at line {line_number}."
        )
    if data_format not in _SUPPORTED_FORMATS:
        raise DataFormatError(
            f"Unsupported Touchstone data format '{tokens[2]}' at line {line_number}."
        )

    reference_resistance = 50.0
    remaining = tokens[3:]
    if remaining:
        if len(remaining) != 2 or remaining[0].lower() != "r":
            raise DataFormatError(f"Invalid Touchstone option line at line {line_number}.")
        try:
            reference_resistance = _parse_float(remaining[1])
        except ValueError as exc:
            raise DataFormatError(
                f"Invalid reference resistance at line {line_number}."
            ) from exc

    if not math.isfinite(reference_resistance) or reference_resistance <= 0.0:
        raise DataFormatError(
            f"Reference resistance must be finite and positive at line {line_number}."
        )

    return TouchstoneOptions(
        frequency_unit=frequency_unit,
        parameter=parameter,
        data_format=data_format,
        reference_resistance=reference_resistance,
    )


def parse_numeric_tokens(tokens: list[str]) -> NDArray[np.float64]:
    try:
        return np.asarray([_parse_float(token) for token in tokens], dtype=np.float64)
    except ValueError as exc:
        raise DataFormatError(f"Invalid numeric token in Touchstone data: {exc}") from exc


def _parse_float(token: str) -> float:
    return float(token.replace("D", "E").replace("d", "e"))


def pairs_to_complex(
    pairs: NDArray[np.float64],
    data_format: str,
) -> NDArray[np.complex128]:
    first = pairs[:, :, 0]
    second = pairs[:, :, 1]

    if data_format == "ri":
        return first + 1j * second

    phase_rad = np.deg2rad(second)
    if data_format == "ma":
        magnitude = first
    elif data_format == "db":
        magnitude = np.power(10.0, first / 20.0)
    else:
        raise DataFormatError(f"Unsupported Touchstone data format: {data_format}")

    return np.asarray(magnitude * np.exp(1j * phase_rad), dtype=np.complex128)

TouchstoneFormat = Literal["ri", "ma", "db"]
TouchstoneFrequencyUnit = Literal["hz", "khz", "mhz", "ghz"]


def write_touchstone(
    network: Network,
    path: str | Path,
    *,
    data_format: TouchstoneFormat = "ri",
    frequency_unit: TouchstoneFrequencyUnit = "hz",
    precision: int = 16,
) -> None:
    """Write a Network as a Touchstone 1.x S-parameter file.

    The destination suffix must match the network port count.
    """

    file_path = Path(path)
    suffix_ports = _port_count_from_suffix(file_path)
    if suffix_ports != network.n_ports:
        raise DataFormatError(
            f"Touchstone suffix declares {suffix_ports} ports but Network has "
            f"{network.n_ports} ports."
        )

    fmt = data_format.lower()
    unit = frequency_unit.lower()
    if fmt not in _SUPPORTED_FORMATS:
        raise DataFormatError(f"Unsupported Touchstone data format '{data_format}'.")
    if unit not in FREQUENCY_SCALE:
        raise DataFormatError(f"Unsupported frequency unit '{frequency_unit}'.")
    if precision < 1:
        raise DataFormatError("precision must be at least 1.")

    if network.z0.imag != 0.0:
        raise DataFormatError(
            "Touchstone 1.x writer requires a real scalar reference impedance."
        )
    z0 = float(network.z0.real)
    if not math.isfinite(z0) or z0 <= 0.0:
        raise DataFormatError(
            "Touchstone 1.x writer requires a finite positive reference impedance."
        )

    scale = FREQUENCY_SCALE[unit]
    option_line = f"# {unit.upper()} S {fmt.upper()} R {_format_float(z0, precision)}"

    output_lines = ["! Generated by Interconnect Studio", option_line]
    for freq_index in range(network.n_freq):
        values = [_format_float(network.frequencies_hz[freq_index] / scale, precision)]
        for row, column in _parameter_order(network.n_ports):
            first, second = _complex_to_pair(network.s[freq_index, row, column], fmt)
            values.append(_format_float(first, precision))
            values.append(_format_float(second, precision))
        output_lines.append(" ".join(values))

    try:
        file_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    except OSError as exc:
        raise DataFormatError(f"Unable to write Touchstone file: {file_path}") from exc


def _parameter_order(n_ports: int) -> tuple[tuple[int, int], ...]:
    """Return (row, column) indices in Touchstone 1.x write order.

    Two-port files are the documented special case and use column-major
    order (S11 S21 S12 S22); every other port count is row-major.
    """

    if n_ports == 2:
        return ((0, 0), (1, 0), (0, 1), (1, 1))
    return tuple((row, column) for row in range(n_ports) for column in range(n_ports))


def _complex_to_pair(value: complex, data_format: str) -> tuple[float, float]:
    if data_format == "ri":
        return float(value.real), float(value.imag)

    magnitude = abs(value)
    phase_deg = math.degrees(math.atan2(value.imag, value.real))

    if data_format == "ma":
        return magnitude, phase_deg
    if data_format == "db":
        db_value = -math.inf if magnitude == 0.0 else 20.0 * math.log10(magnitude)
        return db_value, phase_deg

    raise DataFormatError(f"Unsupported Touchstone data format: {data_format}")


def _format_float(value: float, precision: int) -> str:
    if math.isinf(value):
        return "-inf" if value < 0.0 else "inf"
    return format(value, f".{precision}g")
