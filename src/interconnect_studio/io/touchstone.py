"""Touchstone 1.x reader."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np

from interconnect_studio.core import DataFormatError, Network

_TOUCHSTONE_SUFFIX: Final[re.Pattern[str]] = re.compile(r"^\\.s(?P<ports>\\d+)p$", re.IGNORECASE)

_FREQUENCY_SCALE: Final[dict[str, float]] = {
    "hz": 1.0,
    "khz": 1.0e3,
    "mhz": 1.0e6,
    "ghz": 1.0e9,
}

_SUPPORTED_FORMATS: Final[set[str]] = {"ri", "ma", "db"}
_SUPPORTED_PORT_COUNTS: Final[set[int]] = {1, 2, 4}


@dataclass(frozen=True, slots=True)
class _TouchstoneOptions:
    frequency_unit: str = "ghz"
    parameter: str = "s"
    data_format: str = "ma"
    reference_resistance: float = 50.0


def read_touchstone(path: str | Path) -> Network:
    """Read a Touchstone 1.x S-parameter file into a Network.

    Supported files are .s1p, .s2p and .s4p using RI, MA or DB data
    formats and Hz, kHz, MHz or GHz frequency units.
    """

    file_path = Path(path)
    n_ports = _port_count_from_suffix(file_path)
    if n_ports not in _SUPPORTED_PORT_COUNTS:
        raise DataFormatError(
            f"Touchstone reader currently supports 1, 2 or 4 ports, got {n_ports}."
        )

    try:
        text = file_path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise DataFormatError(f"Unable to read Touchstone file: {file_path}") from exc
    except UnicodeError as exc:
        raise DataFormatError(f"Touchstone file is not valid UTF-8 text: {file_path}") from exc

    options = _TouchstoneOptions()
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
            options = _parse_option_line(line, line_number)
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

    numeric_values = _parse_numeric_tokens(numeric_tokens)
    records = numeric_values.reshape((-1, values_per_point))

    frequency_scale = _FREQUENCY_SCALE[options.frequency_unit]
    frequencies_hz = records[:, 0] * frequency_scale

    n_freq = records.shape[0]
    s = np.empty((n_freq, n_ports, n_ports), dtype=np.complex128)

    pairs = records[:, 1:].reshape((n_freq, n_ports * n_ports, 2))
    complex_values = _pairs_to_complex(pairs, options.data_format)

    # Touchstone 1.x orders an N-port point as:
    # S11, S21, ... SN1, S12, S22, ... SN2, ...
    for column in range(n_ports):
        for row in range(n_ports):
            touchstone_index = column * n_ports + row
            s[:, row, column] = complex_values[:, touchstone_index]

    try:
        return Network(
            frequencies_hz=frequencies_hz,
            s=s,
            z0=complex(options.reference_resistance),
        )
    except ValueError as exc:
        raise DataFormatError(f"Touchstone data violates Network invariants: {exc}") from exc


def _port_count_from_suffix(path: Path) -> int:
    match = _TOUCHSTONE_SUFFIX.match(path.suffix)
    if match is None:
        raise DataFormatError(
            f"Expected a Touchstone S-parameter suffix such as .s1p, .s2p or .s4p: {path}"
        )
    return int(match.group("ports"))


def _parse_option_line(line: str, line_number: int) -> _TouchstoneOptions:
    tokens = line[1:].split()
    if len(tokens) < 3:
        raise DataFormatError(f"Incomplete Touchstone option line at line {line_number}.")

    frequency_unit = tokens[0].lower()
    parameter = tokens[1].lower()
    data_format = tokens[2].lower()

    if frequency_unit not in _FREQUENCY_SCALE:
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

    return _TouchstoneOptions(
        frequency_unit=frequency_unit,
        parameter=parameter,
        data_format=data_format,
        reference_resistance=reference_resistance,
    )


def _parse_numeric_tokens(tokens: list[str]) -> np.ndarray:
    try:
        return np.asarray([_parse_float(token) for token in tokens], dtype=np.float64)
    except ValueError as exc:
        raise DataFormatError(f"Invalid numeric token in Touchstone data: {exc}") from exc


def _parse_float(token: str) -> float:
    return float(token.replace("D", "E").replace("d", "e"))


def _pairs_to_complex(pairs: np.ndarray, data_format: str) -> np.ndarray:
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

    return magnitude * np.exp(1j * phase_rad)
