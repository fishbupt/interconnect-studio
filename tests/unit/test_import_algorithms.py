from pathlib import Path

import numpy as np
import pytest

from interconnect_studio.algorithms.network import (
    ParameterAssignment,
    build_network,
    missing_parameters,
    port_assignments,
    subset_frequency_range,
    subset_point_count,
)
from interconnect_studio.core import InputValidationError, Network
from interconnect_studio.io import ImportFileType
from interconnect_studio.services import (
    BuildSource,
    FrequencyRange,
    ImportService,
)

DATA_DIR = Path(__file__).parents[1] / "data" / "import"


def network(n_ports: int, offset: float = 0.0, z0: float = 50.0, n_freq: int = 5) -> Network:
    """S[k, r, c] = offset + 10*r + c + j*k with 0-based r, c."""

    s = np.empty((n_freq, n_ports, n_ports), dtype=np.complex128)
    for k in range(n_freq):
        for row in range(n_ports):
            for col in range(n_ports):
                s[k, row, col] = offset + 10 * row + col + 1j * k
    return Network(np.arange(1, n_freq + 1) * 1.0e9, s, z0=z0)


def test_subset_keeps_measured_points_inside_the_range() -> None:
    result = subset_frequency_range(network(2), 2.0e9, 4.0e9)

    np.testing.assert_array_equal(result.frequencies_hz, [2.0e9, 3.0e9, 4.0e9])
    np.testing.assert_array_equal(result.s, network(2).s[1:4])


def test_subset_does_not_resample_between_points() -> None:
    result = subset_frequency_range(network(1), 1.5e9, 3.5e9)

    np.testing.assert_array_equal(result.frequencies_hz, [2.0e9, 3.0e9])


def test_subset_point_count_matches_subset() -> None:
    assert subset_point_count(network(1), 1.5e9, 3.5e9) == 2


@pytest.mark.parametrize(
    ("start", "stop", "message"),
    [
        (0.5e9, 3.0e9, "beyond the measured range"),
        (2.0e9, 6.0e9, "beyond the measured range"),
        (3.0e9, 2.0e9, "must not exceed"),
        (2.2e9, 2.8e9, "No measured point"),
    ],
)
def test_subset_rejects_invalid_ranges(start: float, stop: float, message: str) -> None:
    with pytest.raises(InputValidationError, match=message):
        subset_frequency_range(network(1), start, stop)


def test_port_assignments_cover_every_pair_of_mapped_ports() -> None:
    items = port_assignments(0, [0, 1], [4, 5])

    assert {(item.row, item.col) for item in items} == {(4, 4), (4, 5), (5, 4), (5, 5)}
    s45 = next(item for item in items if (item.row, item.col) == (4, 5))
    assert (s45.source_row, s45.source_col) == (0, 1)


def test_build_places_parameters_and_later_assignments_overwrite() -> None:
    first, second = network(2), network(2, offset=100.0)
    assignments = [
        *port_assignments(0, [0, 1], [0, 1]),
        ParameterAssignment(row=1, col=0, source=1, source_row=0, source_col=1),
    ]

    built = build_network([first, second], 2, assignments)

    np.testing.assert_array_equal(built.s[:, 0, 0], first.s[:, 0, 0])
    np.testing.assert_array_equal(built.s[:, 1, 0], second.s[:, 0, 1])


def test_build_maps_two_port_files_into_a_four_port() -> None:
    left, right = network(2), network(2, offset=100.0)
    assignments = [
        *port_assignments(0, [0, 1], [0, 1]),
        *port_assignments(1, [0, 1], [2, 3]),
        *port_assignments(0, [0, 1], [0, 2]),
        *port_assignments(0, [0, 1], [0, 3]),
        *port_assignments(0, [0, 1], [1, 2]),
        *port_assignments(0, [0, 1], [1, 3]),
    ]

    built = build_network([left, right], 4, assignments)

    assert built.n_ports == 4
    np.testing.assert_array_equal(built.s[:, 3, 2], right.s[:, 1, 0])


def test_missing_parameters_lists_uncovered_pairs() -> None:
    assert missing_parameters(2, port_assignments(0, [0], [0])) == ((0, 1), (1, 0), (1, 1))


def test_build_refuses_unassigned_parameters() -> None:
    with pytest.raises(InputValidationError, match="Unassigned DUT parameters: S1,2"):
        build_network([network(2)], 2, port_assignments(0, [0], [0]))


@pytest.mark.parametrize(
    ("other", "message"),
    [
        (network(2, n_freq=4), "frequency grid"),
        (network(2, z0=75.0), "reference impedance"),
    ],
)
def test_build_refuses_sources_that_would_need_resampling(other: Network, message: str) -> None:
    with pytest.raises(InputValidationError, match=message):
        build_network([network(2), other], 2, port_assignments(0, [0, 1], [0, 1]))


def test_service_imports_a_subset() -> None:
    imported = ImportService().import_single(
        DATA_DIR / "three_port.s3p",
        ImportFileType.TOUCHSTONE,
        FrequencyRange(start_hz=2.0e8, stop_hz=3.0e8),
    )

    assert imported.name == "three_port.s3p"
    assert imported.source_path == DATA_DIR / "three_port.s3p"
    assert imported.network.n_freq == 2


def test_service_builds_from_sources() -> None:
    service = ImportService()
    source = BuildSource(DATA_DIR / "two_port.ts", service.read(DATA_DIR / "two_port.ts",
                                                               ImportFileType.TOUCHSTONE_2))

    imported = service.build([source], 2, port_assignments(0, [0, 1], [1, 0]), "swapped.s2p")

    assert imported.name == "swapped.s2p"
    assert imported.source_path is None
    np.testing.assert_array_equal(imported.network.s[:, 0, 0], source.network.s[:, 1, 1])


def test_service_builds_from_config_file() -> None:
    imported = ImportService().build_from_config(DATA_DIR / "build_config.csv")
    s = imported.network.s[0]

    assert imported.name == "build_config.s3p"
    assert imported.network.n_ports == 3
    # file_1 maps its ports onto the same DUT ports ...
    assert s[1, 1] == 22
    # ... then file_2 ports [1 2] -> DUT [3 1] overwrites S33, S31, S13 and S11.
    assert (s[2, 2], s[2, 0], s[0, 2], s[0, 0]) == (11, 12, 21, 22)


def test_service_export_fixes_the_touchstone_suffix(tmp_path: Path) -> None:
    service = ImportService()

    written = service.export_touchstone(network(3), tmp_path / "built.txt")

    assert written.name == "built.s3p"
    np.testing.assert_allclose(
        service.read(written, ImportFileType.TOUCHSTONE).s, network(3).s
    )
