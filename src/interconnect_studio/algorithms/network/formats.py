"""S-parameter display format conversions."""

from enum import StrEnum

import numpy as np
from numpy.typing import NDArray

from interconnect_studio.core import InputValidationError, Network


class SParameterFormat(StrEnum):
    """Supported frequency-domain display formats."""

    LOG_MAG = "log_mag"
    LINEAR_MAG = "linear_mag"
    PHASE = "phase"
    UNWRAPPED_PHASE = "unwrapped_phase"
    GROUP_DELAY = "group_delay"
    REAL = "real"
    IMAGINARY = "imaginary"
    SWR = "swr"
    SMITH = "smith"
    POLAR = "polar"
    IMPEDANCE_REAL = "impedance_real"
    IMPEDANCE_IMAGINARY = "impedance_imaginary"
    IMPEDANCE_MAGNITUDE = "impedance_magnitude"
    IMPEDANCE_IMAGINARY_MAGNITUDE = "impedance_imaginary_magnitude"
    IMPEDANCE_ANGLE = "impedance_angle"
    QUALITY_FACTOR = "quality_factor"
    DISSIPATION_FACTOR = "dissipation_factor"


FormattedSParameter = NDArray[np.float64] | NDArray[np.complex128]


def format_s_parameter(
    network: Network,
    response_port: int,
    source_port: int,
    data_format: SParameterFormat | str,
) -> FormattedSParameter:
    """Convert one S-parameter trace into a display format.

    Ports use zero-based response/source semantics. Scalar formats return
    float64 arrays. Smith and Polar return complex128 coefficient arrays.
    """

    trace = network.s_parameter(response_port, source_port)
    fmt = _coerce_format(data_format)

    if fmt is SParameterFormat.LOG_MAG:
        return _log_magnitude_db(trace)
    if fmt is SParameterFormat.LINEAR_MAG:
        return np.asarray(np.abs(trace), dtype=np.float64)
    if fmt is SParameterFormat.PHASE:
        return np.asarray(np.angle(trace, deg=True), dtype=np.float64)
    if fmt is SParameterFormat.UNWRAPPED_PHASE:
        return np.asarray(np.rad2deg(np.unwrap(np.angle(trace))), dtype=np.float64)
    if fmt is SParameterFormat.GROUP_DELAY:
        return _group_delay_seconds(network.frequencies_hz, trace)
    if fmt is SParameterFormat.REAL:
        return np.asarray(trace.real, dtype=np.float64)
    if fmt is SParameterFormat.IMAGINARY:
        return np.asarray(trace.imag, dtype=np.float64)
    if fmt in (SParameterFormat.SMITH, SParameterFormat.POLAR):
        return np.asarray(trace, dtype=np.complex128).copy()

    _require_reflection(response_port, source_port, fmt)

    if fmt is SParameterFormat.SWR:
        return _swr(trace)

    impedance = _reflection_to_impedance(trace, network.z0)
    if fmt is SParameterFormat.IMPEDANCE_REAL:
        return np.asarray(impedance.real, dtype=np.float64)
    if fmt is SParameterFormat.IMPEDANCE_IMAGINARY:
        return np.asarray(impedance.imag, dtype=np.float64)
    if fmt is SParameterFormat.IMPEDANCE_MAGNITUDE:
        return np.asarray(np.abs(impedance), dtype=np.float64)
    if fmt is SParameterFormat.IMPEDANCE_IMAGINARY_MAGNITUDE:
        return np.asarray(np.abs(impedance.imag), dtype=np.float64)
    if fmt is SParameterFormat.IMPEDANCE_ANGLE:
        return np.asarray(np.angle(impedance, deg=True), dtype=np.float64)
    if fmt is SParameterFormat.QUALITY_FACTOR:
        return _quality_factor(impedance)
    if fmt is SParameterFormat.DISSIPATION_FACTOR:
        return _dissipation_factor(impedance)

    raise InputValidationError(f"Unsupported S-parameter format: {fmt}")


def _coerce_format(data_format: SParameterFormat | str) -> SParameterFormat:
    if isinstance(data_format, SParameterFormat):
        return data_format
    try:
        return SParameterFormat(data_format)
    except ValueError as exc:
        raise InputValidationError(
            f"Unsupported S-parameter format: {data_format!r}."
        ) from exc


def _log_magnitude_db(trace: NDArray[np.complex128]) -> NDArray[np.float64]:
    magnitude = np.abs(trace)
    with np.errstate(divide="ignore"):
        result = 20.0 * np.log10(magnitude)
    return np.asarray(result, dtype=np.float64)


def _group_delay_seconds(
    frequencies_hz: NDArray[np.float64],
    trace: NDArray[np.complex128],
) -> NDArray[np.float64]:
    if frequencies_hz.size < 2:
        raise InputValidationError("Group delay requires at least two frequency points.")

    unwrapped_phase_rad = np.unwrap(np.angle(trace))
    derivative = np.gradient(unwrapped_phase_rad, frequencies_hz)
    return np.asarray(-derivative / (2.0 * np.pi), dtype=np.float64)


def _require_reflection(
    response_port: int,
    source_port: int,
    data_format: SParameterFormat,
) -> None:
    if response_port != source_port:
        raise InputValidationError(
            f"{data_format.value} is valid only for reflection parameters Sii."
        )


def _swr(trace: NDArray[np.complex128]) -> NDArray[np.float64]:
    magnitude = np.abs(trace)
    with np.errstate(divide="ignore", invalid="ignore"):
        result = (1.0 + magnitude) / (1.0 - magnitude)
    return np.asarray(result, dtype=np.float64)


def _reflection_to_impedance(
    reflection: NDArray[np.complex128],
    z0: complex,
) -> NDArray[np.complex128]:
    with np.errstate(divide="ignore", invalid="ignore"):
        impedance = z0 * (1.0 + reflection) / (1.0 - reflection)
    return np.asarray(impedance, dtype=np.complex128)


def _quality_factor(impedance: NDArray[np.complex128]) -> NDArray[np.float64]:
    resistance = impedance.real
    reactance_magnitude = np.abs(impedance.imag)
    with np.errstate(divide="ignore", invalid="ignore"):
        result = reactance_magnitude / resistance
    return np.asarray(result, dtype=np.float64)


def _dissipation_factor(
    impedance: NDArray[np.complex128],
) -> NDArray[np.float64]:
    resistance = impedance.real
    reactance_magnitude = np.abs(impedance.imag)
    with np.errstate(divide="ignore", invalid="ignore"):
        result = resistance / reactance_magnitude
    return np.asarray(result, dtype=np.float64)
