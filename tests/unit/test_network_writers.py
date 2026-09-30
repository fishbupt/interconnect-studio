from pathlib import Path

import numpy as np
import pytest

from interconnect_studio.core import DataFormatError, InputValidationError, Network
from interconnect_studio.io import (
    read_citifile,
    read_text_network,
    read_touchstone,
    read_touchstone2,
    write_citifile,
    write_text_network,
    write_touchstone2,
)
from interconnect_studio.io.atomic import atomic_destination
from interconnect_studio.services import (
    ExportFileType,
    ExportOptions,
    ExportService,
    FrequencyRange,
)


def asymmetric(n_ports: int, z0: complex = 75.0) -> Network:
    values = np.arange(1, 3 * n_ports * n_ports + 1).reshape(3, n_ports, n_ports)
    s = values / 1000 + 1j * (values[::-1] / 2000)
    return Network([1e6, 2e6, 5e6], s, z0=z0)


@pytest.mark.parametrize("n_ports", [1, 2, 3, 4])
@pytest.mark.parametrize("data_format", ["ri", "ma", "db"])
@pytest.mark.parametrize("unit", ["hz", "khz", "mhz", "ghz"])
def test_touchstone2_roundtrip_asymmetric_matrix(
    tmp_path: Path,
    n_ports: int,
    data_format: str,
    unit: str,
) -> None:
    network = asymmetric(n_ports)
    path = tmp_path / "channel.ts"
    write_touchstone2(network, path, data_format=data_format, frequency_unit=unit)
    result = read_touchstone2(path)
    np.testing.assert_allclose(result.s, network.s, rtol=2e-14, atol=1e-15)
    np.testing.assert_array_equal(result.frequencies_hz, network.frequencies_hz)
    assert result.z0 == network.z0
    if n_ports == 2:
        assert "[Two-Port Data Order] 12_21" in path.read_text()


def test_citifile_roundtrip_full_arrays(tmp_path: Path) -> None:
    network = asymmetric(4, 50)
    path = tmp_path / "channel.cti"
    write_citifile(network, path)
    result = read_citifile(path)
    np.testing.assert_array_equal(result.s, network.s)
    np.testing.assert_array_equal(result.frequencies_hz, network.frequencies_hz)


@pytest.mark.parametrize("reference", [75.0, 50 + 1j])
def test_citifile_rejects_reference_loss_and_preserves_existing_file(
    tmp_path: Path,
    reference: complex,
) -> None:
    path = tmp_path / "existing.cti"
    path.write_text("original")
    with pytest.raises(DataFormatError, match="50 ohms"):
        write_citifile(asymmetric(2, reference), path)
    assert path.read_text() == "original"


@pytest.mark.parametrize("n_ports", [2, 12])
@pytest.mark.parametrize("delimiter", ["comma", "tab"])
def test_text_roundtrip_reference_and_quoted_multi_digit_ports(
    tmp_path: Path,
    n_ports: int,
    delimiter: str,
) -> None:
    network = asymmetric(n_ports, 75 + 2j)
    path = tmp_path / "table.csv"
    write_text_network(network, path, delimiter, frequency_unit="ghz")
    result = read_text_network(path, delimiter)
    np.testing.assert_array_equal(result.s, network.s)
    np.testing.assert_array_equal(result.frequencies_hz, network.frequencies_hz)
    assert result.z0 == network.z0
    assert read_text_network(path, delimiter, z0=50).z0 == 50


def test_export_subset_and_port_permutation_leave_input_unchanged(tmp_path: Path) -> None:
    network = asymmetric(3)
    original = network.s.copy()
    options = ExportOptions(
        frequency_range=FrequencyRange(2e6, 5e6),
        port_order=(2, 0, 1),
    )
    target = ExportService().export(network, tmp_path / "output.wrong", options)
    assert target.suffix == ".s3p"
    restored = read_touchstone(target)
    np.testing.assert_array_equal(restored.s, original[1:][:, [2, 0, 1]][:, :, [2, 0, 1]])
    np.testing.assert_array_equal(network.s, original)
    assert network.z0 == 75


def test_citifile_reference_conversion_is_explicit(tmp_path: Path) -> None:
    network = asymmetric(2)
    target = ExportService().export(
        network,
        tmp_path / "output",
        ExportOptions(
            file_type=ExportFileType.CITIFILE,
            renormalize_to_50=True,
        ),
    )
    restored = read_citifile(target)
    assert restored.z0 == 50
    assert not np.array_equal(restored.s, network.s)
    assert network.z0 == 75


@pytest.mark.parametrize("order", [(0, 0), (0,), (0, 2)])
def test_export_invalid_mapping_preserves_destination(
    tmp_path: Path, order: tuple[int, ...]
) -> None:
    target = tmp_path / "output.s2p"
    target.write_text("original")
    with pytest.raises(InputValidationError):
        ExportService().export(asymmetric(2), target, ExportOptions(port_order=order))
    assert target.read_text() == "original"


def test_atomic_write_failure_leaves_no_partial_file(tmp_path: Path) -> None:
    target = tmp_path / "existing.s2p"
    target.write_text("original")
    with pytest.raises(OSError):
        with atomic_destination(target) as temporary:
            temporary.write_text("partial")
            raise OSError("disk full")
    assert target.read_text() == "original"
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize("reference", [50 + 2j, -50])
def test_touchstone2_rejects_unrepresentable_reference(tmp_path: Path, reference: complex) -> None:
    with pytest.raises(DataFormatError, match="reference impedance"):
        write_touchstone2(asymmetric(2, reference), tmp_path / "invalid.ts")


def test_touchstone2_zero_coefficients_db_roundtrip(tmp_path: Path) -> None:
    network = Network([1e9], np.zeros((1, 2, 2)), 50)
    path = tmp_path / "zeros.ts"
    write_touchstone2(network, path, data_format="db")
    np.testing.assert_array_equal(read_touchstone2(path).s, network.s)
