"""File-format round trips must preserve analytical mixed-mode golden results."""

from pathlib import Path

import numpy as np
import pytest

from interconnect_studio.algorithms.mixed_mode import DEFAULT_FOUR_PORT_TOPOLOGY, to_mixed_mode
from interconnect_studio.io import detect_file_type, read_network, read_touchstone
from interconnect_studio.services import ExportFileType, ExportOptions, ExportService

GOLDEN = Path(__file__).parents[2] / "golden_data/mixed_mode"


@pytest.mark.parametrize(
    "case,filename",
    [
        ("Case001_coupled_pair", "coupled_pair.s4p"),
        ("Case002_coupled_pair_skew", "coupled_pair_skew.s4p"),
    ],
)
@pytest.mark.parametrize("file_type", list(ExportFileType))
def test_export_preserves_golden_mixed_mode(
    tmp_path: Path,
    case: str,
    filename: str,
    file_type: ExportFileType,
) -> None:
    original = read_touchstone(GOLDEN / case / "input" / filename)
    target = ExportService().export(
        original, tmp_path / "converted", ExportOptions(file_type=file_type)
    )
    restored = read_network(target, detect_file_type(target))
    actual = to_mixed_mode(restored, DEFAULT_FOUR_PORT_TOPOLOGY.port_group)
    expected = to_mixed_mode(original, DEFAULT_FOUR_PORT_TOPOLOGY.port_group)
    np.testing.assert_allclose(actual.s, expected.s, rtol=1e-12, atol=1e-14)
    np.testing.assert_array_equal(restored.frequencies_hz, original.frequencies_hz)
    assert restored.z0 == original.z0
