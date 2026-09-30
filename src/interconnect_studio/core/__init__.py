"""Core domain models for Interconnect Studio."""

from interconnect_studio.core.dut import (
    QUICK_TOPOLOGIES,
    DutConfiguration,
    LogicalPort,
    quick_topologies_for,
    quick_topology,
)
from interconnect_studio.core.errors import DataFormatError, InputValidationError
from interconnect_studio.core.hierarchy import (
    BrowserCategory,
    DataBrowserTree,
    DataFile,
    ViewType,
    ViewWindow,
)
from interconnect_studio.core.layout import MAX_PLOTS, ViewLayout
from interconnect_studio.core.mixed_mode import MixedModeNetwork, Mode
from interconnect_studio.core.network import Network
from interconnect_studio.core.plot import PlotKind, PlotModel
from interconnect_studio.core.port_group import Line, PortGroup
from interconnect_studio.core.project import ProjectFile, ProjectSnapshot, ProjectWindow
from interconnect_studio.core.template import TemplatePlot, ViewTemplate
from interconnect_studio.core.trace import Trace, TraceRecipe

__all__ = [
    "MAX_PLOTS",
    "QUICK_TOPOLOGIES",
    "BrowserCategory",
    "DataBrowserTree",
    "DataFile",
    "DataFormatError",
    "DutConfiguration",
    "InputValidationError",
    "Line",
    "LogicalPort",
    "MixedModeNetwork",
    "Mode",
    "Network",
    "PlotKind",
    "PlotModel",
    "PortGroup",
    "ProjectFile",
    "ProjectSnapshot",
    "ProjectWindow",
    "TemplatePlot",
    "Trace",
    "TraceRecipe",
    "ViewLayout",
    "ViewTemplate",
    "ViewType",
    "ViewWindow",
    "quick_topologies_for",
    "quick_topology",
]
