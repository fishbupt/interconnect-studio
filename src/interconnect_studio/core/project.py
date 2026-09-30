"""Portable workspace state, independent of Qt and source file locations."""

import math
from dataclasses import dataclass

from interconnect_studio.core.dut import DutConfiguration
from interconnect_studio.core.errors import InputValidationError
from interconnect_studio.core.hierarchy import DataFile, ViewType
from interconnect_studio.core.layout import ViewLayout


@dataclass(frozen=True, slots=True)
class ProjectFile:
    """An embedded measurement and its optional DUT configuration."""

    data_file: DataFile
    dut_configuration: DutConfiguration | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.data_file, DataFile):
            raise InputValidationError("Project measurement must be a DataFile.")
        if self.dut_configuration is not None:
            if not isinstance(self.dut_configuration, DutConfiguration):
                raise InputValidationError("Project DUT configuration is invalid.")
            if self.dut_configuration.n_ports != self.data_file.network.n_ports:
                raise InputValidationError("Project DUT configuration has a different port count.")


@dataclass(frozen=True, slots=True)
class ProjectWindow:
    """One window's plots and optional axis bounds (xmin, xmax, ymin, ymax).

    The current selection is deliberately not persisted, per UI_DESIGN.md.
    """

    number: int
    file_id: str
    view_type: ViewType
    layout: ViewLayout
    template: str = ""
    plot_ranges: tuple[tuple[float, float, float, float] | None, ...] = ()
    plot_autorange: tuple[tuple[bool, bool], ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.number, bool) or not isinstance(self.number, int) or self.number < 1:
            raise InputValidationError("Project window number must be a positive integer.")
        if not isinstance(self.view_type, ViewType) or not isinstance(self.layout, ViewLayout):
            raise InputValidationError("Project window requires a view type and layout.")
        if not isinstance(self.file_id, str) or not self.file_id:
            raise InputValidationError("Project window file id must be non-empty.")
        if not isinstance(self.template, str):
            raise InputValidationError("Project template name must be a string.")
        if self.plot_ranges and len(self.plot_ranges) != self.layout.n_cells:
            raise InputValidationError("Project plot ranges must match the grid.")
        if self.plot_autorange and (
            len(self.plot_autorange) != self.layout.n_cells
            or any(
                len(axes) != 2 or any(type(axis) is not bool for axis in axes)
                for axes in self.plot_autorange
            )
        ):
            raise InputValidationError("Project auto-range flags must match the grid.")
        for bounds in self.plot_ranges:
            if bounds is not None and (
                len(bounds) != 4
                or not all(math.isfinite(value) for value in bounds)
                or bounds[0] >= bounds[1]
                or bounds[2] >= bounds[3]
            ):
                raise InputValidationError("Project plot bounds must be finite, increasing ranges.")


@dataclass(frozen=True, slots=True)
class ProjectSnapshot:
    """All open measurements/windows plus Qt's opaque dock and geometry bytes."""

    files: tuple[ProjectFile, ...] = ()
    windows: tuple[ProjectWindow, ...] = ()
    geometry: bytes = b""
    dock_state: bytes = b""

    def __post_init__(self) -> None:
        if not isinstance(self.files, tuple) or not all(
            isinstance(item, ProjectFile) for item in self.files
        ):
            raise InputValidationError("Project files must be a tuple of ProjectFile.")
        if not isinstance(self.windows, tuple) or not all(
            isinstance(item, ProjectWindow) for item in self.windows
        ):
            raise InputValidationError("Project windows must be a tuple of ProjectWindow.")
        ids = [item.data_file.id for item in self.files]
        numbers = [window.number for window in self.windows]
        if len(set(ids)) != len(ids) or len(set(numbers)) != len(numbers):
            raise InputValidationError("Project file ids and window numbers must be unique.")
        for window in self.windows:
            if window.file_id not in ids:
                raise InputValidationError("Project window refers to a missing data file.")
            for plot in window.layout.plots:
                for trace in plot.traces:
                    if trace.source_id and trace.source_id != window.file_id:
                        raise InputValidationError("Project trace refers to another data file.")
        if not isinstance(self.geometry, bytes) or not isinstance(self.dock_state, bytes):
            raise InputValidationError("Project geometry and dock state must be bytes.")
