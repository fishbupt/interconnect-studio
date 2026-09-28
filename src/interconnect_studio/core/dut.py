"""How a DUT's physical ports are addressed.

A measurement file carries N physical ports and nothing about what they
mean. The DUT configuration supplies the meaning: which ports form a
differential pair, which are single-ended, how they are labelled, and how
they are numbered when the user talks about them.

PLTS calls the same thing DUT Configuration, and is explicit that changing
it **only affects differential maths, it does not remap the data** (see
``PLTS_REFERENCE.md`` §3.5). The same holds here: a configuration never
touches the S matrix.

``PortGroup`` stays the single source of truth for pairing and for which
ports are two ends of one path, so logical ports are derived from it rather
than stored beside it.
"""

from dataclasses import dataclass, replace
from typing import Final

from interconnect_studio.core.errors import InputValidationError
from interconnect_studio.core.port_group import Line, PortGroup


@dataclass(frozen=True, slots=True)
class LogicalPort:
    """One port as the user addresses it.

    A single-ended logical port is one DUT port; a differential one is two,
    positive conductor first. ``number`` is 1-based, as displayed.
    """

    number: int
    label: str
    dut_ports: tuple[int, ...]

    @property
    def is_differential(self) -> bool:
        """Whether this logical port is a differential pair."""

        return len(self.dut_ports) == 2

    @property
    def display_ports(self) -> str:
        """The DUT ports behind it, 1-based, as shown in the UI."""

        return ",".join(str(port + 1) for port in self.dut_ports)


@dataclass(frozen=True, slots=True)
class DutConfiguration:
    """A named way of addressing one DUT's ports.

    Parameters
    ----------
    name:
        Display name, also the default file name when saved.
    n_ports:
        Physical port count. ``port_group`` must cover exactly
        ``0..n_ports-1``.
    port_group:
        Pairing and through relationships. See ``PortGroup``.
    port_labels:
        One label per physical port, indexed 0-based. PLTS uses these in
        place of its ``<<<<`` / ``>>>>`` arrows. They describe the DUT, so
        they override a file's own ``Network.port_names`` for display.
    """

    name: str
    n_ports: int
    port_group: PortGroup
    port_labels: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise InputValidationError("DUT configuration name must be a non-empty string.")
        if isinstance(self.n_ports, bool) or not isinstance(self.n_ports, int):
            raise InputValidationError("DUT configuration n_ports must be an integer.")
        if self.n_ports < 1:
            raise InputValidationError(
                f"A DUT needs at least one port, got {self.n_ports}."
            )
        if not isinstance(self.port_group, PortGroup):
            raise InputValidationError("DUT configuration port_group must be a PortGroup.")
        self.port_group.validate_covers(self.n_ports)
        if not isinstance(self.port_labels, tuple) or len(self.port_labels) != self.n_ports:
            raise InputValidationError(
                f"DUT configuration needs one label per port; expected {self.n_ports}, "
                f"got {len(self.port_labels) if isinstance(self.port_labels, tuple) else '?'}."
            )
        if any(not isinstance(label, str) or not label.strip() for label in self.port_labels):
            raise InputValidationError("DUT port labels must be non-empty strings.")

    @property
    def logical_ports(self) -> tuple[LogicalPort, ...]:
        """The logical ports, numbered from 1.

        They run line by line, near end before far end -- the same order the
        mixed-mode transform uses, so logical port 2 of a differential pair
        is the port SDD21 responds at.
        """

        ports: list[LogicalPort] = []
        for line in self.port_group.lines:
            for end in line.ends:
                ports.append(
                    LogicalPort(
                        number=len(ports) + 1,
                        label=" / ".join(self.port_labels[port] for port in end),
                        dut_ports=end,
                    )
                )
        return tuple(ports)

    @property
    def n_logical_ports(self) -> int:
        """How many ports the user addresses."""

        return len(self.logical_ports)

    @property
    def is_differential(self) -> bool:
        """Whether every logical port is a differential pair.

        This is what mixed-mode conversion requires.
        """

        return self.port_group.is_differential

    @property
    def topology_summary(self) -> str:
        """PLTS-style shorthand for the logical ports, e.g. ``Diff-Diff``."""

        return "-".join(
            "Diff" if port.is_differential else "SE" for port in self.logical_ports
        )

    @property
    def through_summary(self) -> str:
        """Through paths in 1-based display ports, e.g. ``1,3 -> 2,4``."""

        paths = [
            f"{_display(line.near)}\u2192{_display(line.far)}"
            for line in self.port_group.lines
            if line.far
        ]
        return " , ".join(paths) if paths else "no through paths"

    def logical_port_of(self, dut_port: int) -> LogicalPort:
        """Which logical port a physical, 0-based DUT port belongs to."""

        for logical in self.logical_ports:
            if dut_port in logical.dut_ports:
                return logical
        raise InputValidationError(
            f"DUT port {dut_port} is not in the range 0..{self.n_ports - 1}."
        )

    def with_labels(self, port_labels: tuple[str, ...]) -> "DutConfiguration":
        """Return a copy carrying different physical port labels."""

        return replace(self, port_labels=port_labels)

    def renamed(self, name: str) -> "DutConfiguration":
        """Return a copy under a different name."""

        return replace(self, name=name)

    @staticmethod
    def default_labels(n_ports: int) -> tuple[str, ...]:
        """``Port 1`` .. ``Port N``, the labels used until a user sets their own."""

        return tuple(f"Port {port + 1}" for port in range(n_ports))

    @classmethod
    def single_ended(cls, n_ports: int, *, name: str = "Single-Ended") -> "DutConfiguration":
        """Every port on its own, with no through relationship asserted.

        This is the Reset state, and what a file gets before anyone chooses
        a topology: the data is usable single-ended and nothing has been
        claimed about how the ports connect.
        """

        if isinstance(n_ports, bool) or not isinstance(n_ports, int) or n_ports < 1:
            raise InputValidationError(f"A DUT needs at least one port, got {n_ports}.")
        return cls(
            name=name,
            n_ports=n_ports,
            port_group=PortGroup(
                lines=tuple(
                    Line(name=f"Port {port + 1}", near=(port,)) for port in range(n_ports)
                )
            ),
            port_labels=cls.default_labels(n_ports),
        )


def _display(ports: tuple[int, ...]) -> str:
    return ",".join(str(port + 1) for port in ports)


def _configuration(
    name: str,
    n_ports: int,
    lines: tuple[Line, ...],
) -> DutConfiguration:
    return DutConfiguration(
        name=name,
        n_ports=n_ports,
        port_group=PortGroup(lines=lines),
        port_labels=DutConfiguration.default_labels(n_ports),
    )


# PLTS Quick Topologies (PLTS_REFERENCE.md §3.5), minus the four-port
# Diff-Diff wirings: those are through-path presets and belong to
# ``algorithms.mixed_mode.Topology``, which reaches them through
# ``Topology.dut_configuration()``. Defining them twice would let the two
# disagree, which is the mistake PortGroup exists to prevent.
#
# INFERRED: the help gives each preset's name but not which DUT port goes
# where inside it. The assignments below read the shorthand as naming the
# DUT's two sides in order, lowest ports first. The model supports any
# assignment; these defaults need checking against the real dialog before
# they are presented as PLTS-compatible.
QUICK_TOPOLOGIES: Final[dict[str, DutConfiguration]] = {
    "2_se_se": _configuration(
        "2-Port SE-SE",
        2,
        (Line(name="Line 1", near=(0,), far=(1,)),),
    ),
    "2_diff_reflection": _configuration(
        "2-Port Differential Reflection",
        2,
        (Line(name="Pair 1", near=(0, 1)),),
    ),
    "3_diff_se": _configuration(
        "3-Port Diff-SE",
        3,
        (Line(name="Line 1", near=(0, 1), far=(2,)),),
    ),
    "3_se_se": _configuration(
        "3-Port SE-SE",
        3,
        (
            Line(name="Line 1", near=(0,), far=(1,)),
            Line(name="Line 2", near=(2,)),
        ),
    ),
    "4_diff_se": _configuration(
        "4-Port Diff-SE",
        4,
        (
            Line(name="Line 1", near=(0, 1), far=(2,)),
            Line(name="Line 2", near=(3,)),
        ),
    ),
    "4_se_diff": _configuration(
        "4-Port SE-Diff",
        4,
        (
            Line(name="Line 1", near=(0,), far=(2, 3)),
            Line(name="Line 2", near=(1,)),
        ),
    ),
    "4_se_se": _configuration(
        "4-Port SE-SE",
        4,
        (
            Line(name="Line 1", near=(0,), far=(1,)),
            Line(name="Line 2", near=(2,), far=(3,)),
        ),
    ),
}


def quick_topology(topology_id: str) -> DutConfiguration:
    """Look up a PLTS Quick Topology preset by id."""

    try:
        return QUICK_TOPOLOGIES[topology_id]
    except KeyError:
        raise InputValidationError(f"Unknown quick topology: {topology_id!r}.") from None


def quick_topologies_for(n_ports: int) -> tuple[tuple[str, DutConfiguration], ...]:
    """The presets that fit a port count.

    Four-port Diff-Diff wirings are not here; see the note above the table.
    """

    return tuple(
        (topology_id, configuration)
        for topology_id, configuration in QUICK_TOPOLOGIES.items()
        if configuration.n_ports == n_ports
    )
