from pathlib import Path

import numpy as np
import pytest

from interconnect_studio.core import DataFormatError
from interconnect_studio.io import read_touchstone

DATA_DIR = Path(__file__).parents[1] / "data" / "touchstone"


def test_read_touchstone_2port_ri_restores_standard_parameter_order() -> None:
    network = read_touchstone(DATA_DIR / "valid_2port_ri.s2p")

    np.testing.assert_array_equal(network.frequencies_hz, [100.0e6, 200.0e6])
    assert network.n_ports == 2
    assert network.z0 == 75.0 + 0.0j

    assert network.s[0, 0, 0] == pytest.approx(0.10 + 0.01j)
    assert network.s[0, 1, 0] == pytest.approx(0.80 - 0.10j)
    assert network.s[0, 0, 1] == pytest.approx(0.02 + 0.03j)
    assert network.s[0, 1, 1] == pytest.approx(0.20 - 0.02j)


def test_read_touchstone_4port_uses_column_major_touchstone_order() -> None:
    network = read_touchstone(DATA_DIR / "valid_4port_ma.s4p")

    assert network.n_ports == 4
    for row in range(4):
        for column in range(4):
            expected = 10 * (row + 1) + (column + 1)
            assert network.s[0, row, column] == pytest.approx(expected + 0.0j)


def test_read_touchstone_db_converts_to_complex(tmp_path: Path) -> None:
    path = tmp_path / "gain.s1p"
    path.write_text("# GHz S DB R 50\n1 6.020599913279624 90\n", encoding="utf-8")

    network = read_touchstone(path)

    assert network.s[0, 0, 0] == pytest.approx(0.0 + 2.0j, abs=1e-12)


def test_read_touchstone_ma_converts_phase_degrees(tmp_path: Path) -> None:
    path = tmp_path / "phase.s1p"
    path.write_text("# kHz S MA R 50\n1000 2 -90\n", encoding="utf-8")

    network = read_touchstone(path)

    assert network.frequencies_hz[0] == pytest.approx(1.0e6)
    assert network.s[0, 0, 0] == pytest.approx(0.0 - 2.0j, abs=1e-12)


@pytest.mark.parametrize(
    ("unit", "scale"),
    [
        ("Hz", 1.0),
        ("kHz", 1.0e3),
        ("MHz", 1.0e6),
        ("GHz", 1.0e9),
    ],
)
def test_read_touchstone_converts_frequency_units(
    tmp_path: Path,
    unit: str,
    scale: float,
) -> None:
    path = tmp_path / "unit.s1p"
    path.write_text(f"# {unit} S RI R 50\n2 0 0\n", encoding="utf-8")

    network = read_touchstone(path)

    assert network.frequencies_hz[0] == 2.0 * scale


def test_read_touchstone_uses_touchstone_defaults_without_option_line(tmp_path: Path) -> None:
    path = tmp_path / "default.s1p"
    path.write_text("1 2 0\n", encoding="utf-8")

    network = read_touchstone(path)

    assert network.frequencies_hz[0] == 1.0e9
    assert network.s[0, 0, 0] == pytest.approx(2.0 + 0.0j)
    assert network.z0 == 50.0 + 0.0j


def test_read_touchstone_ignores_comments_and_accepts_fortran_exponents(
    tmp_path: Path,
) -> None:
    path = tmp_path / "comments.s1p"
    path.write_text(
        "! header\n# Hz S RI R 50 ! option comment\n1D+6 1D-1 -2d-1 ! data\n",
        encoding="utf-8",
    )

    network = read_touchstone(path)

    assert network.frequencies_hz[0] == 1.0e6
    assert network.s[0, 0, 0] == pytest.approx(0.1 - 0.2j)


@pytest.mark.parametrize(
    ("suffix", "content", "message"),
    [
        (".txt", "# GHz S RI R 50\n1 0 0\n", "suffix"),
        (".s3p", "# GHz S RI R 50\n1 0 0\n", "supports 1, 2 or 4 ports"),
        (".s1p", "# THz S RI R 50\n1 0 0\n", "frequency unit"),
        (".s1p", "# GHz Y RI R 50\n1 0 0\n", "Only S-parameters"),
        (".s1p", "# GHz S XY R 50\n1 0 0\n", "data format"),
        (".s1p", "[Version] 2.0\n", "2.0"),
        (".s1p", "# GHz S RI R 50\n1 0\n", "complete number"),
        (".s1p", "# GHz S RI R 50\n1 nope 0\n", "numeric token"),
    ],
)
def test_read_touchstone_rejects_invalid_or_unsupported_input(
    tmp_path: Path,
    suffix: str,
    content: str,
    message: str,
) -> None:
    path = tmp_path / f"invalid{suffix}"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(DataFormatError, match=message):
        read_touchstone(path)


def test_read_touchstone_rejects_duplicate_frequency_points(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.s1p"
    path.write_text("# Hz S RI R 50\n1 0 0\n1 0 0\n", encoding="utf-8")

    with pytest.raises(DataFormatError, match="Network invariants"):
        read_touchstone(path)


def test_read_touchstone_rejects_multiple_option_lines(tmp_path: Path) -> None:
    path = tmp_path / "duplicate-option.s1p"
    path.write_text(
        "# GHz S RI R 50\n# GHz S RI R 50\n1 0 0\n",
        encoding="utf-8",
    )

    with pytest.raises(DataFormatError, match="Multiple"):
        read_touchstone(path)
