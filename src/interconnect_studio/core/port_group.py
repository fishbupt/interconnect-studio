"""Port grouping shared by mixed-mode and crosstalk analysis.

Both describe the same thing -- which ports belong to the same line, and
which end of it -- so they use one representation rather than growing two.
"""

from dataclasses import dataclass

from interconnect_studio.core.errors import InputValidationError


@dataclass(frozen=True, slots=True)
class Line:
    """One transmission line's ports at each end.

    ``near`` and ``far`` hold one port for a single-ended line and two for a
    differential one. **Tuple order carries polarity**: the first entry is the
    positive conductor. Polarity follows the physical trace, so a topology
    whose through path runs from port 0 to port 3 puts port 3 first at the
    far end, even though a higher index sorts later.

    Ports are Python-internal 0-based indices.
    """

    name: str
    near: tuple[int, ...]
    far: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise InputValidationError("Line name must be a non-empty string.")
        for label, ports in (("near", self.near), ("far", self.far)):
            if not isinstance(ports, tuple) or not ports:
                raise InputValidationError(f"Line {label} must be a non-empty tuple of ports.")
            for port in ports:
                if isinstance(port, bool) or not isinstance(port, int) or port < 0:
                    raise InputValidationError(f"Line {label} ports must be non-negative integers.")
        if len(self.near) != len(self.far):
            raise InputValidationError(
                "Line near and far must hold the same number of ports; "
                f"got {len(self.near)} and {len(self.far)}."
            )
        if len(set(self.near + self.far)) != len(self.near) + len(self.far):
            raise InputValidationError("Line ports must be unique.")

    @property
    def is_differential(self) -> bool:
        """Whether this line carries a differential pair."""

        return len(self.near) == 2

    @property
    def ports(self) -> tuple[int, ...]:
        """Every port of the line, near end first."""

        return self.near + self.far


@dataclass(frozen=True, slots=True)
class PortGroup:
    """How a DUT's ports are grouped into lines.

    Mixed-mode pair mapping and crosstalk victim/aggressor relationships are
    both derived from this, so they can never disagree.
    """

    lines: tuple[Line, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.lines, tuple) or not self.lines:
            raise InputValidationError("PortGroup must contain at least one Line.")
        if not all(isinstance(line, Line) for line in self.lines):
            raise InputValidationError("PortGroup lines must be Line objects.")

        names = [line.name for line in self.lines]
        if len(set(names)) != len(names):
            raise InputValidationError("PortGroup line names must be unique.")

        ports = [port for line in self.lines for port in line.ports]
        if len(set(ports)) != len(ports):
            raise InputValidationError("A port may belong to only one Line.")

    @property
    def n_ports(self) -> int:
        """Number of single-ended ports covered."""

        return sum(len(line.ports) for line in self.lines)

    @property
    def is_differential(self) -> bool:
        """Whether every line carries a differential pair."""

        return all(line.is_differential for line in self.lines)

    def validate_covers(self, n_ports: int) -> None:
        """Raise unless this group covers exactly ports 0..n_ports-1."""

        ports = {port for line in self.lines for port in line.ports}
        if ports != set(range(n_ports)):
            raise InputValidationError(
                f"PortGroup must cover exactly ports 0..{n_ports - 1}, got {sorted(ports)}."
            )
