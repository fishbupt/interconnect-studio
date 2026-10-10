"""Build independent A/B overlays from original networks without resampling."""

from interconnect_studio.algorithms.network import SParameterFormat, create_s_parameter_trace
from interconnect_studio.algorithms.network.traces import format_display_name
from interconnect_studio.core import DataFile, InputValidationError, PlotModel, ViewLayout
from interconnect_studio.services.frequency_analysis import renamed_trace


def comparison_layout(
    a: DataFile,
    b: DataFile,
    data_format: SParameterFormat,
    parameter: tuple[int, int] | None = None,
) -> ViewLayout:
    """Overlay A/B on their own frequency grids; ``None`` selects the two-port matrix.

    Port indices are zero-based. This is a presentation service, with no matching,
    interpolation, phase fitting, differences or acceptance decisions.
    """

    if a.id == b.id:
        raise InputValidationError("请选择两个不同的文件。")
    if parameter is None and min(a.network.n_ports, b.network.n_ports) < 2:
        raise InputValidationError("2×2 视图需要两侧至少有两个端口。")
    pairs = ((0, 0), (0, 1), (1, 0), (1, 1)) if parameter is None else (parameter,)
    plots = []
    for response, source in pairs:
        traces = tuple(
            renamed_trace(
                create_s_parameter_trace(item.network, response, source, data_format),
                f"{role} · {item.name}",
                item.id,
            )
            for role, item in (("A", a), ("B", b))
        )
        plots.append(
            PlotModel(
                traces=traces,
                title=f"S{response + 1}{source + 1}",
                x_label="Frequency",
                y_label=format_display_name(data_format),
            )
        )
    size = 2 if parameter is None else 1
    return ViewLayout(rows=size, cols=size, plots=tuple(plots))
