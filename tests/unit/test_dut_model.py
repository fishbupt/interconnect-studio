"""The DUT configuration model: logical ports, labels, and presets."""

import pytest

from interconnect_studio.algorithms.mixed_mode import (
    DEFAULT_FOUR_PORT_TOPOLOGY,
    to_mixed_mode,
    topology_by_id,
)
from interconnect_studio.core import (
    DutConfiguration,
    InputValidationError,
    Line,
    Network,
    PortGroup,
    quick_topologies_for,
    quick_topology,
)


def configuration(*lines: Line, n_ports: int) -> DutConfiguration:
    return DutConfiguration(
        name="Test",
        n_ports=n_ports,
        port_group=PortGroup(lines=lines),
        port_labels=DutConfiguration.default_labels(n_ports),
    )


def test_single_ended_gives_one_logical_port_per_physical_port() -> None:
    config = DutConfiguration.single_ended(4)

    assert config.n_logical_ports == 4
    assert [port.dut_ports for port in config.logical_ports] == [(0,), (1,), (2,), (3,)]
    assert config.is_differential is False
    assert config.topology_summary == "SE-SE-SE-SE"


def test_single_ended_asserts_no_through_relationship() -> None:
    """A file arrives without one, and inventing one would be a claim."""

    config = DutConfiguration.single_ended(2)

    assert all(line.far == () for line in config.port_group.lines)


def test_four_port_pair_has_two_differential_logical_ports() -> None:
    config = DEFAULT_FOUR_PORT_TOPOLOGY.dut_configuration()

    assert config.n_ports == 4
    assert config.n_logical_ports == 2
    assert config.topology_summary == "Diff-Diff"
    assert [port.dut_ports for port in config.logical_ports] == [(0, 2), (1, 3)]


def test_logical_ports_are_numbered_from_one_near_end_first() -> None:
    """Logical port 2 is the far end, which is where SDD21 responds."""

    config = DEFAULT_FOUR_PORT_TOPOLOGY.dut_configuration()

    near, far = config.logical_ports
    assert (near.number, far.number) == (1, 2)
    assert near.dut_ports == DEFAULT_FOUR_PORT_TOPOLOGY.port_group.lines[0].near
    assert far.dut_ports == DEFAULT_FOUR_PORT_TOPOLOGY.port_group.lines[0].far


def test_logical_port_order_matches_the_mixed_mode_transform() -> None:
    """Both walk the port group the same way, so numbering cannot drift."""

    topology = topology_by_id("through_1_4_2_3")
    config = topology.dut_configuration()
    network = Network([1.0e9], [[[0.0] * 4] * 4], z0=50.0)

    mixed = to_mixed_mode(network, config.port_group)

    assert mixed.n_mode_ports == config.n_logical_ports
    assert config.logical_ports[1].dut_ports == topology.port_group.lines[0].far


def test_logical_port_label_joins_the_ports_behind_it() -> None:
    config = DEFAULT_FOUR_PORT_TOPOLOGY.dut_configuration().with_labels(
        ("TX+", "RX+", "TX-", "RX-")
    )

    assert config.logical_ports[0].label == "TX+ / TX-"
    assert config.logical_ports[0].display_ports == "1,3"


def test_logical_port_of_finds_the_owning_port() -> None:
    config = DEFAULT_FOUR_PORT_TOPOLOGY.dut_configuration()

    assert config.logical_port_of(3).number == 2
    assert config.logical_port_of(0).number == 1


def test_logical_port_of_rejects_a_port_outside_the_dut() -> None:
    with pytest.raises(InputValidationError, match="not in the range"):
        DutConfiguration.single_ended(2).logical_port_of(5)


def test_a_reflection_only_pair_is_one_logical_port() -> None:
    """Two ports, one differential port, nothing at a far end."""

    config = quick_topology("2_diff_reflection")

    assert config.n_logical_ports == 1
    assert config.is_differential is True
    assert config.topology_summary == "Diff"


def test_a_balun_is_not_differential_end_to_end() -> None:
    """Differential in, single-ended out: no mode exists across the path."""

    config = quick_topology("3_diff_se")

    assert config.topology_summary == "Diff-SE"
    assert config.is_differential is False


def test_mixed_mode_refuses_a_balun_rather_than_guessing() -> None:
    network = Network([1.0e9], [[[0.0] * 3] * 3], z0=50.0)

    with pytest.raises(InputValidationError, match="differential"):
        to_mixed_mode(network, quick_topology("3_diff_se").port_group)


@pytest.mark.parametrize(
    ("topology_id", "summary"),
    [
        ("2_se_se", "SE-SE"),
        ("2_diff_reflection", "Diff"),
        ("3_diff_se", "Diff-SE"),
        ("3_se_se", "SE-SE-SE"),
        ("4_diff_se", "Diff-SE-SE"),
        ("4_se_diff", "SE-Diff-SE"),
        ("4_se_se", "SE-SE-SE-SE"),
    ],
)
def test_every_preset_reports_its_shape(topology_id: str, summary: str) -> None:
    assert quick_topology(topology_id).topology_summary == summary


def test_presets_are_listed_by_port_count() -> None:
    ids = [topology_id for topology_id, _ in quick_topologies_for(2)]

    assert ids == ["2_se_se", "2_diff_reflection"]
    assert quick_topologies_for(9) == ()


def test_unknown_preset_is_named_in_the_error() -> None:
    with pytest.raises(InputValidationError, match="nonsense"):
        quick_topology("nonsense")


def test_configuration_must_cover_every_port() -> None:
    with pytest.raises(InputValidationError, match="cover exactly"):
        configuration(Line(name="Line 1", near=(0,), far=(1,)), n_ports=4)


def test_labels_must_match_the_port_count() -> None:
    with pytest.raises(InputValidationError, match="one label per port"):
        DutConfiguration(
            name="Test",
            n_ports=2,
            port_group=PortGroup(lines=(Line(name="Line 1", near=(0,), far=(1,)),)),
            port_labels=("only one",),
        )


def test_labels_must_not_be_blank() -> None:
    with pytest.raises(InputValidationError, match="non-empty"):
        DutConfiguration(
            name="Test",
            n_ports=2,
            port_group=PortGroup(lines=(Line(name="Line 1", near=(0,), far=(1,)),)),
            port_labels=("Port 1", "  "),
        )


def test_name_must_not_be_blank() -> None:
    with pytest.raises(InputValidationError, match="name"):
        DutConfiguration.single_ended(2).renamed("   ")


def test_renaming_and_relabelling_leave_the_original_alone() -> None:
    config = DutConfiguration.single_ended(2)

    renamed = config.renamed("Fixture").with_labels(("A", "B"))

    assert config.name == "Single-Ended"
    assert config.port_labels == ("Port 1", "Port 2")
    assert renamed.name == "Fixture"
    assert renamed.port_labels == ("A", "B")


@pytest.mark.parametrize("n_ports", [0, -1])
def test_a_dut_needs_at_least_one_port(n_ports: int) -> None:
    with pytest.raises(InputValidationError, match="at least one port"):
        DutConfiguration.single_ended(n_ports)
