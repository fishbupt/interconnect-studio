"""Touchstone-to-plot application service."""

from dataclasses import dataclass
from pathlib import Path

from interconnect_studio.algorithms.network import (
    SParameterFormat,
    create_s_parameter_trace,
    plot_kind_for_s_parameter_format,
)
from interconnect_studio.algorithms.network.traces import format_display_name
from interconnect_studio.core import InputValidationError, Network, PlotKind, PlotModel
from interconnect_studio.io import read_touchstone


@dataclass(frozen=True, slots=True)
class LoadedTouchstonePlot:
    """A network shown in the current plot.

    ``name`` is the display name (file name, or the name given to a built
    network); ``path`` is the source file, ``None`` for built networks.
    """

    name: str
    network: Network
    plot: PlotModel
    path: Path | None = None


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
        return self.show_network(network, file_path.name, file_path)

    def show_network(
        self, network: Network, name: str, path: Path | None = None
    ) -> LoadedTouchstonePlot:
        """Create the default plot for any network: S11, plus S21 when it has 2+ ports."""

        traces = [create_s_parameter_trace(network, 0, 0, "log_mag")]
        if network.n_ports >= 2:
            traces.append(create_s_parameter_trace(network, 1, 0, "log_mag"))

        plot = PlotModel(
            traces=tuple(traces),
            kind=PlotKind.CARTESIAN,
            title=name,
            x_label="Frequency",
            y_label="Log Magnitude",
        )
        return LoadedTouchstonePlot(name=name, network=network, plot=plot, path=path)

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
                traces=(trace,),
                kind=kind,
                title=loaded.name,
                x_label="Frequency",
                y_label=format_display_name(fmt),
            )
            replaced_plot = True

        return TraceUpdate(
            loaded=LoadedTouchstonePlot(
                name=loaded.name,
                network=loaded.network,
                plot=plot,
                path=loaded.path,
            ),
            replaced_plot=replaced_plot,
        )
