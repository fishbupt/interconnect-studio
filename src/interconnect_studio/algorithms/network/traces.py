"""Bridge between S-parameter formatting and plot domain models."""

from interconnect_studio.algorithms.network.formats import SParameterFormat, format_s_parameter
from interconnect_studio.core import Network, PlotKind, Trace, TraceRecipe

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


def create_s_parameter_trace(
    network: Network,
    response_port: int,
    source_port: int,
    data_format: SParameterFormat | str,
) -> Trace:
    """Create a plot-ready Trace for one formatted S-parameter."""

    fmt = (
        data_format
        if isinstance(data_format, SParameterFormat)
        else SParameterFormat(data_format)
    )
    values = format_s_parameter(network, response_port, source_port, fmt)
    parameter_name = f"S{response_port + 1}{source_port + 1}"
    name = f"{parameter_name} {format_display_name(fmt)}"
    return Trace(
        name=name,
        x=network.frequencies_hz,
        y=values,
        x_unit="Hz",
        y_unit=_Y_UNITS[fmt],
        recipe=TraceRecipe(response_port, source_port, fmt.value),
    )


def plot_kind_for_s_parameter_format(
    data_format: SParameterFormat | str,
) -> PlotKind:
    """Return the required plot geometry for an S-parameter format."""

    fmt = (
        data_format
        if isinstance(data_format, SParameterFormat)
        else SParameterFormat(data_format)
    )
    if fmt is SParameterFormat.SMITH:
        return PlotKind.SMITH
    if fmt is SParameterFormat.POLAR:
        return PlotKind.POLAR
    return PlotKind.CARTESIAN


def format_display_name(data_format: SParameterFormat) -> str:
    """Return a stable user-facing display name for a format."""

    return {
        SParameterFormat.LOG_MAG: "Log Mag",
        SParameterFormat.LINEAR_MAG: "Linear Mag",
        SParameterFormat.PHASE: "Phase",
        SParameterFormat.UNWRAPPED_PHASE: "Unwrapped Phase",
        SParameterFormat.GROUP_DELAY: "Group Delay",
        SParameterFormat.REAL: "Real",
        SParameterFormat.IMAGINARY: "Imaginary",
        SParameterFormat.SWR: "SWR",
        SParameterFormat.SMITH: "Smith",
        SParameterFormat.POLAR: "Polar",
        SParameterFormat.IMPEDANCE_REAL: "Impedance Real",
        SParameterFormat.IMPEDANCE_IMAGINARY: "Impedance Imaginary",
        SParameterFormat.IMPEDANCE_MAGNITUDE: "Impedance Magnitude",
        SParameterFormat.IMPEDANCE_IMAGINARY_MAGNITUDE: "Impedance Imaginary Magnitude",
        SParameterFormat.IMPEDANCE_ANGLE: "Impedance Angle",
        SParameterFormat.QUALITY_FACTOR: "Quality Factor",
        SParameterFormat.DISSIPATION_FACTOR: "Dissipation Factor",
    }[data_format]
