"""Mixed-mode parameter formatting and plot-ready traces.

Formatting reuses ``format_coefficient`` from the single-ended path, so the
two can never drift apart. Only the reference impedance differs: a
differential port references ``2 * z0``, a common port ``z0 / 2``.
"""

from interconnect_studio.algorithms.network.formats import (
    REFLECTION_ONLY_FORMATS,
    FormattedSParameter,
    SParameterFormat,
    format_coefficient,
)
from interconnect_studio.algorithms.network.traces import format_display_name
from interconnect_studio.core import InputValidationError, MixedModeNetwork, Mode, Trace

_Y_UNITS: dict[SParameterFormat, str] = {
    SParameterFormat.LOG_MAG: "dB",
    SParameterFormat.LINEAR_MAG: "",
    SParameterFormat.PHASE: "degree",
    SParameterFormat.UNWRAPPED_PHASE: "degree",
    SParameterFormat.GROUP_DELAY: "s",
    SParameterFormat.REAL: "",
    SParameterFormat.IMAGINARY: "",
    SParameterFormat.SWR: "",
    SParameterFormat.SMITH: "",
    SParameterFormat.POLAR: "",
    SParameterFormat.IMPEDANCE_REAL: "ohm",
    SParameterFormat.IMPEDANCE_IMAGINARY: "ohm",
    SParameterFormat.IMPEDANCE_MAGNITUDE: "ohm",
    SParameterFormat.IMPEDANCE_IMAGINARY_MAGNITUDE: "ohm",
    SParameterFormat.IMPEDANCE_ANGLE: "degree",
    SParameterFormat.QUALITY_FACTOR: "",
    SParameterFormat.DISSIPATION_FACTOR: "",
}

_CARTESIAN_TRANSMISSION_FORMATS: tuple[SParameterFormat, ...] = (
    SParameterFormat.LOG_MAG,
    SParameterFormat.LINEAR_MAG,
    SParameterFormat.PHASE,
    SParameterFormat.UNWRAPPED_PHASE,
    SParameterFormat.GROUP_DELAY,
    SParameterFormat.REAL,
    SParameterFormat.IMAGINARY,
)


def mixed_mode_parameter_name(
    response_mode: Mode,
    source_mode: Mode,
    response_port: int,
    source_port: int,
) -> str:
    """Engineering name of a mixed-mode parameter, e.g. ``SDD21``.

    Modes are written response-first, matching ``SDC`` meaning a differential
    response to a common stimulus. Ports are shown 1-based.
    """

    modes = f"{response_mode.value}{source_mode.value}".upper()
    return f"S{modes}{response_port + 1}{source_port + 1}"


def is_mixed_mode_reflection(
    response_mode: Mode,
    source_mode: Mode,
    response_port: int,
    source_port: int,
) -> bool:
    """Whether a mixed-mode parameter is a reflection of one mode.

    Mode-conversion terms such as SDC11 sit on one port but relate different
    modes, so no single reference impedance describes them and the
    impedance-derived formats do not apply.
    """

    return response_mode is source_mode and response_port == source_port


def cartesian_formats_for_mixed_mode(
    response_mode: Mode,
    source_mode: Mode,
    response_port: int,
    source_port: int,
) -> tuple[SParameterFormat, ...]:
    """Cartesian formats valid for one mixed-mode parameter."""

    if is_mixed_mode_reflection(response_mode, source_mode, response_port, source_port):
        return (*_CARTESIAN_TRANSMISSION_FORMATS, *REFLECTION_ONLY_FORMATS)
    return _CARTESIAN_TRANSMISSION_FORMATS


def format_mixed_mode_parameter(
    network: MixedModeNetwork,
    response_mode: Mode,
    source_mode: Mode,
    response_port: int,
    source_port: int,
    data_format: SParameterFormat | str,
) -> FormattedSParameter:
    """Convert one mixed-mode parameter into a display format."""

    coefficient = network.mode_parameter(
        response_mode, source_mode, response_port, source_port
    )
    reflection = is_mixed_mode_reflection(
        response_mode, source_mode, response_port, source_port
    )
    z0 = (
        network.z0_differential
        if response_mode is Mode.DIFFERENTIAL
        else network.z0_common
    )
    return format_coefficient(
        coefficient,
        network.frequencies_hz,
        z0,
        data_format,
        is_reflection=reflection,
    )


def create_mixed_mode_trace(
    network: MixedModeNetwork,
    response_mode: Mode,
    source_mode: Mode,
    response_port: int,
    source_port: int,
    data_format: SParameterFormat | str,
) -> Trace:
    """Create a plot-ready Trace for one formatted mixed-mode parameter."""

    fmt = (
        data_format
        if isinstance(data_format, SParameterFormat)
        else SParameterFormat(data_format)
    )
    if fmt not in _Y_UNITS:
        raise InputValidationError(f"Unsupported S-parameter format: {fmt}")

    values = format_mixed_mode_parameter(
        network, response_mode, source_mode, response_port, source_port, fmt
    )
    parameter = mixed_mode_parameter_name(
        response_mode, source_mode, response_port, source_port
    )
    return Trace(
        name=f"{parameter} {format_display_name(fmt)}",
        x=network.frequencies_hz,
        y=values,
        x_unit="Hz",
        y_unit=_Y_UNITS[fmt],
    )
