"""Mixed-mode (differential / common) analysis."""

from interconnect_studio.algorithms.mixed_mode.topology import (
    DEFAULT_FOUR_PORT_TOPOLOGY,
    FOUR_PORT_TOPOLOGIES,
    Topology,
    topology_by_id,
)
from interconnect_studio.algorithms.mixed_mode.traces import (
    cartesian_formats_for_mixed_mode,
    create_mixed_mode_trace,
    format_mixed_mode_parameter,
    is_mixed_mode_reflection,
    mixed_mode_parameter_name,
)
from interconnect_studio.algorithms.mixed_mode.transform import to_mixed_mode

__all__ = [
    "DEFAULT_FOUR_PORT_TOPOLOGY",
    "FOUR_PORT_TOPOLOGIES",
    "Topology",
    "cartesian_formats_for_mixed_mode",
    "create_mixed_mode_trace",
    "format_mixed_mode_parameter",
    "is_mixed_mode_reflection",
    "mixed_mode_parameter_name",
    "to_mixed_mode",
    "topology_by_id",
]
