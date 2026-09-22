"""Touchstone-to-plot application service."""

from dataclasses import dataclass
from pathlib import Path

from interconnect_studio.algorithms.network import (
    SParameterFormat,
    create_s_parameter_trace,
    plot_kind_for_s_parameter_format,
)
from interconnect_studio.algorithms.network.traces import format_display_name
from interconnect_studio.core import (
    InputValidationError,
    Network,
    PlotKind,
    PlotModel,
    PlotTrace,
)
from interconnect_studio.io import read_touchstone


@dataclass(frozen=True, slots=True)
class LoadedTouchstonePlot:
    """Result of loading a two-port Touchstone file for the default view."""

    path: Path
    network: Network
    plot: PlotModel


@dataclass(frozen=True, slots=True)
class TraceUpdate:
    """Result of adding a trace to the current plot."""

    loaded: LoadedTouchstonePlot
    replaced_plot: bool


class TouchstonePlotService:
    """Build and update two-port S-parameter plots."""

    def load_s2p(self, path: str | Path) -> LoadedTouchstonePlot:
        """Load a two-port Touchstone file and create its default plot."""

        file_path = Path(path)
        network = read_touchstone(file_path)

        if network.n_ports != 2:
            raise InputValidationError(
                f"The first UI workflow requires a 2-port network, got {network.n_ports} ports."
            )

        s11 = create_s_parameter_trace(network, 0, 0, "log_mag")
        s21 = create_s_parameter_trace(network, 1, 0, "log_mag")

        plot = PlotModel(
            entries=(PlotTrace(s11), PlotTrace(s21)),
            kind=PlotKind.CARTESIAN,
            title=file_path.name,
            x_label="Frequency",
            y_label_left="Log Magnitude",
        )
        return LoadedTouchstonePlot(path=file_path, network=network, plot=plot)

    def add_trace(
        self,
        loaded: LoadedTouchstonePlot,
        response_port: int,
        source_port: int,
        data_format: SParameterFormat | str,
    ) -> TraceUpdate:
        """Add a trace, replacing the plot when geometry or Y units are incompatible."""

        trace = create_s_parameter_trace(
            loaded.network,
            response_port,
            source_port,
            data_format,
        )
        if any(existing.name == trace.name for existing in loaded.plot.traces):
            raise InputValidationError(f"Trace already exists: {trace.name}.")

        fmt = (
            data_format
            if isinstance(data_format, SParameterFormat)
            else SParameterFormat(data_format)
        )
        kind = plot_kind_for_s_parameter_format(fmt)

        compatible = (
            loaded.plot.kind is kind
            and (
                not loaded.plot.traces
                or loaded.plot.traces[0].y_unit == trace.y_unit
            )
        )

        if compatible:
            plot = loaded.plot.add_trace(trace)
            replaced_plot = False
        else:
            plot = PlotModel(
                entries=(PlotTrace(trace),),
                kind=kind,
                title=loaded.path.name,
                x_label="Frequency",
                y_label_left=format_display_name(fmt),
            )
            replaced_plot = True

        return TraceUpdate(
            loaded=LoadedTouchstonePlot(
                path=loaded.path,
                network=loaded.network,
                plot=plot,
            ),
            replaced_plot=replaced_plot,
        )
