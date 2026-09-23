"""DUT topology presets for four-port differential measurements.

A topology says which ports are connected through the DUT. The differential
pairing follows from it: the near ends of the two lines form one differential
port, the far ends the other. Choosing a topology is therefore the same act as
choosing a mixed-mode pair mapping, and the two can never disagree.
"""

from dataclasses import dataclass
from typing import Final

from interconnect_studio.core import InputValidationError, Line, PortGroup


@dataclass(frozen=True, slots=True)
class Topology:
    """A named DUT wiring, defined by its through paths.

    ``through`` holds one ``(near, far)`` port pair per transmission line,
    using 0-based ports. The first line's conductors are the positive side of
    the differential pair.
    """

    id: str
    name: str
    description: str
    through: tuple[tuple[int, int], ...]

    def __post_init__(self) -> None:
        if len(self.through) != 2:
            raise InputValidationError("A four-port topology needs exactly two through paths.")
        ports = [port for path in self.through for port in path]
        if sorted(ports) != [0, 1, 2, 3]:
            raise InputValidationError(
                f"A four-port topology must use ports 0..3 exactly once, got {sorted(ports)}."
            )

    @property
    def port_group(self) -> PortGroup:
        """The port grouping this topology implies."""

        (near_p, far_p), (near_n, far_n) = self.through
        return PortGroup(
            lines=(
                Line(name="Pair 1", near=(near_p, near_n), far=(far_p, far_n)),
            )
        )

    def label(self) -> str:
        """One-line through-path summary using 1-based display ports."""

        return " , ".join(f"{a + 1}→{b + 1}" for a, b in self.through)


THROUGH_1_2_3_4: Final[Topology] = Topology(
    id="through_1_2_3_4",
    name="Through 1-2, 3-4",
    description="Ports 1 and 3 on the left, 2 and 4 on the right.",
    through=((0, 1), (2, 3)),
)

THROUGH_1_3_2_4: Final[Topology] = Topology(
    id="through_1_3_2_4",
    name="Through 1-3, 2-4",
    description="Ports 1 and 2 on the left, 3 and 4 on the right.",
    through=((0, 2), (1, 3)),
)

THROUGH_1_4_2_3: Final[Topology] = Topology(
    id="through_1_4_2_3",
    name="Through 1-4, 2-3",
    description="Ports 1 and 2 on the left, 4 and 3 on the right (crossed).",
    through=((0, 3), (1, 2)),
)

FOUR_PORT_TOPOLOGIES: Final[tuple[Topology, ...]] = (
    THROUGH_1_2_3_4,
    THROUGH_1_3_2_4,
    THROUGH_1_4_2_3,
)

DEFAULT_FOUR_PORT_TOPOLOGY: Final[Topology] = THROUGH_1_2_3_4
"""PLTS default: through 1-2 and 3-4, giving the 1-3 / 2-4 pair mapping."""


def topology_by_id(topology_id: str) -> Topology:
    """Look up a four-port topology preset by id."""

    for topology in FOUR_PORT_TOPOLOGIES:
        if topology.id == topology_id:
            return topology
    raise InputValidationError(f"Unknown topology: {topology_id!r}.")
