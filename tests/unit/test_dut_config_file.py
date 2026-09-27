"""DUT configuration file round trips and malformed input."""

import json
from pathlib import Path

import pytest

from interconnect_studio.algorithms.mixed_mode import DEFAULT_FOUR_PORT_TOPOLOGY
from interconnect_studio.core import DataFormatError, DutConfiguration, quick_topology
from interconnect_studio.io.dut_config import (
    DUT_CONFIG_VERSION,
    dut_configuration_to_dict,
    read_dut_configuration,
    write_dut_configuration,
)


def round_trip(configuration: DutConfiguration, tmp_path: Path) -> DutConfiguration:
    path = tmp_path / "dut.dutcfg"
    write_dut_configuration(configuration, path)
    return read_dut_configuration(path)


def test_four_port_pair_survives_a_round_trip(tmp_path: Path) -> None:
    configuration = DEFAULT_FOUR_PORT_TOPOLOGY.dut_configuration().with_labels(
        ("TX+", "RX+", "TX-", "RX-")
    )

    assert round_trip(configuration, tmp_path) == configuration


@pytest.mark.parametrize(
    "topology_id",
    ["2_se_se", "2_diff_reflection", "3_diff_se", "3_se_se", "4_se_diff", "4_se_se"],
)
def test_every_preset_survives_a_round_trip(topology_id: str, tmp_path: Path) -> None:
    configuration = quick_topology(topology_id)

    assert round_trip(configuration, tmp_path) == configuration


def test_an_empty_far_end_survives_a_round_trip(tmp_path: Path) -> None:
    """The case JSON would quietly drop if ``far`` were optional on write."""

    restored = round_trip(quick_topology("2_diff_reflection"), tmp_path)

    assert restored.port_group.lines[0].far == ()
    assert restored.n_logical_ports == 1


def test_the_file_keeps_ports_zero_based(tmp_path: Path) -> None:
    path = tmp_path / "dut.dutcfg"
    write_dut_configuration(DEFAULT_FOUR_PORT_TOPOLOGY.dut_configuration(), path)

    document = json.loads(path.read_text(encoding="utf-8"))

    assert document["version"] == DUT_CONFIG_VERSION
    assert document["lines"] == [{"name": "Pair 1", "near": [0, 2], "far": [1, 3]}]


def test_reading_rejects_another_format(tmp_path: Path) -> None:
    path = tmp_path / "other.dutcfg"
    path.write_text(json.dumps({"format": "something-else", "version": 1}), encoding="utf-8")

    with pytest.raises(DataFormatError, match="Not a DUT configuration file"):
        read_dut_configuration(path)


def test_reading_rejects_a_future_version(tmp_path: Path) -> None:
    document = dut_configuration_to_dict(DutConfiguration.single_ended(2))
    document["version"] = DUT_CONFIG_VERSION + 1
    path = tmp_path / "future.dutcfg"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(DataFormatError, match="Unsupported DUT configuration version"):
        read_dut_configuration(path)


def test_reading_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "broken.dutcfg"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(DataFormatError, match="not valid JSON"):
        read_dut_configuration(path)


def test_a_file_that_parses_cannot_yield_an_invalid_configuration(tmp_path: Path) -> None:
    """Domain rules are enforced once, in the model, not again in the reader."""

    document = dut_configuration_to_dict(DutConfiguration.single_ended(4))
    document["n_ports"] = 6
    path = tmp_path / "short.dutcfg"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(DataFormatError, match="Invalid DUT configuration"):
        read_dut_configuration(path)


def test_reading_reports_a_missing_field(tmp_path: Path) -> None:
    document = dut_configuration_to_dict(DutConfiguration.single_ended(2))
    del document["port_labels"]
    path = tmp_path / "partial.dutcfg"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(DataFormatError, match="Malformed DUT configuration"):
        read_dut_configuration(path)


def test_reading_a_missing_file_says_so(tmp_path: Path) -> None:
    with pytest.raises(DataFormatError, match="Unable to read"):
        read_dut_configuration(tmp_path / "absent.dutcfg")
