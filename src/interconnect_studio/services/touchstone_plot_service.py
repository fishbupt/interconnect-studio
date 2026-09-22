"""Touchstone-to-plot application service."""

from dataclasses import dataclass
from pathlib import Path

from interconnect_studio.algorithms.network import create_s_parameter_trace
from interconnect_studio.core import InputValidationError, Network, PlotKind, PlotModel
from interconnect_studio.io import read_touchstone


@dataclass(frozen=True, slots=True)
class LoadedTouchstonePlot:
    """Result of loading a two-port Touchstone file for the default view."""

    path: Path
    network: Network
    plot: PlotModel


class TouchstonePlotService:
    """Build the default S11/S21 LogMag plot for a two-port Touchstone file."""

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
            traces=(s11, s21),
            kind=PlotKind.CARTESIAN,
            title=file_path.name,
            x_label="Frequency",
            y_label="Log Magnitude",
        )
        return LoadedTouchstonePlot(path=file_path, network=network, plot=plot)
