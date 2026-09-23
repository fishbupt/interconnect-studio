from pathlib import Path

import numpy as np
import pytest

from interconnect_studio.core import DataFormatError, Network
from interconnect_studio.io import (
    ImportFileType,
    guess_file_type,
    read_build_config,
    read_citifile,
    read_network,
    read_text_network,
    read_touchstone,
    read_touchstone2,
    write_touchstone,
)

DATA_DIR = Path(__file__).parents[1] / "data" / "import"
FREQUENCIES_HZ = [1.0e8, 2.0e8, 3.0e8]


def expected_s(n_ports: int) -> np.ndarray:
    """Fixture values: S[r][c] = (10*r + c) + j*k with 1-based r, c and point index k."""

    s = np.empty((3, n_ports, n_ports), dtype=np.complex128)
    for k in range(3):
        for row in range(n_ports):
            for col in range(n_ports):
                s[k, row, col] = 10 * (row + 1) + (col + 1) + 1j * k
    return s


def assert_fixture(network: Network, n_ports: int) -> None:
    np.testing.assert_allclose(network.frequencies_hz, FREQUENCIES_HZ)
    np.testing.assert_allclose(network.s, expected_s(n_ports))
    assert network.z0 == 50


def test_touchstone_reads_three_ports_row_major() -> None:
    assert_fixture(read_touchstone(DATA_DIR / "three_port.s3p"), 3)


def test_touchstone_reads_twelve_ports_wrapped_over_lines(tmp_path: Path) -> None:
    n_ports = 12
    s = np.arange(n_ports * n_ports, dtype=np.float64).reshape(1, n_ports, n_ports) + 0j
    network = Network([1.0e9], s, z0=50.0)
    path = tmp_path / "twelve.s12p"
    write_touchstone(network, path)

    # Rewrap to four value pairs per line, as Touchstone 1.x writers do past 4 ports.
    tokens = path.read_text().splitlines()[2].split()
    lines = [tokens[0]] + [
        " ".join(tokens[1 + index : 9 + index]) for index in range(0, len(tokens) - 1, 8)
    ]
    path.write_text("# Hz S RI R 50\n" + "\n".join(lines) + "\n")

    np.testing.assert_allclose(read_touchstone(path).s, s)


def test_touchstone2_reads_12_21_order_and_reference() -> None:
    assert_fixture(read_touchstone2(DATA_DIR / "two_port.ts"), 2)


def test_touchstone2_reads_21_12_order(tmp_path: Path) -> None:
    path = tmp_path / "order.ts"
    path.write_text(
        "[Version] 2.0\n# Hz S RI R 50\n[Number of Ports] 2\n[Two-Port Data Order] 21_12\n"
        "[Number of Frequencies] 1\n[Network Data]\n1 11 0 21 0 12 0 22 0\n[End]\n"
    )

    s = read_touchstone2(path).s[0]

    assert (s[1, 0], s[0, 1]) == (21, 12)


def test_touchstone2_expands_lower_matrix_format(tmp_path: Path) -> None:
    path = tmp_path / "lower.ts"
    path.write_text(
        "[Version] 2.0\n# Hz S RI R 75\n[Number of Ports] 3\n[Number of Frequencies] 1\n"
        "[Matrix Format] Lower\n[Network Data]\n1 11 0\n21 0 22 0\n31 0 32 0 33 0\n[End]\n"
    )

    network = read_touchstone2(path)

    assert network.z0 == 75
    assert network.s[0, 0, 2] == network.s[0, 2, 0] == 31
    assert network.s[0, 1, 2] == 32


def test_touchstone2_reference_line_overrides_option_line(tmp_path: Path) -> None:
    path = tmp_path / "reference.ts"
    path.write_text(
        "[Version] 2.0\n# Hz S RI R 50\n[Number of Ports] 1\n[Number of Frequencies] 1\n"
        "[Reference]\n75\n[Network Data]\n1 0.5 0\n[End]\n"
    )

    assert read_touchstone2(path).z0 == 75


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("# Hz S RI R 50\n", "\\[Version\\] must precede"),
        (
            "[Version] 2.0\n# Hz S RI R 50\n[Number of Ports] 2\n[Two-Port Data Order] 12_21\n"
            "[Number of Frequencies] 1\n[Reference] 50 75\n[Network Data]\n1 0 0 0 0 0 0 0 0\n",
            "impedances differ",
        ),
        (
            "[Version] 2.0\n# Hz S RI R 50\n[Number of Ports] 2\n[Number of Frequencies] 1\n"
            "[Network Data]\n1 0 0 0 0 0 0 0 0\n",
            "Two-Port Data Order",
        ),
        (
            "[Version] 2.0\n# Hz S RI R 50\n[Number of Ports] 4\n[Number of Frequencies] 1\n"
            "[Mixed-Mode Order] D2,1 D1,1 C2,1 C1,1\n",
            "Mixed-mode",
        ),
        (
            "[Version] 2.0\n# Hz S RI R 50\n[Number of Ports] 1\n[Number of Frequencies] 2\n"
            "[Network Data]\n1 0 0\n",
            "Number of Frequencies",
        ),
    ],
)
def test_touchstone2_rejects_invalid_files(tmp_path: Path, body: str, message: str) -> None:
    path = tmp_path / "bad.ts"
    path.write_text(body)

    with pytest.raises(DataFormatError, match=message):
        read_touchstone2(path)


def test_citifile_reads_var_list_and_s_arrays() -> None:
    assert_fixture(read_citifile(DATA_DIR / "two_port.cti"), 2)


def test_citifile_reads_a_linear_segment_and_skips_other_arrays(tmp_path: Path) -> None:
    path = tmp_path / "segment.cti"
    path.write_text(
        "CITIFILE A.01.00\nNAME DATA\nVAR FREQ MAG 3\nDATA E[1] RI\nDATA S[1,1] RI\n"
        "SEG_LIST_BEGIN\nSEG 1000000 3000000 3\nSEG_LIST_END\n"
        "BEGIN\n9,9\n9,9\n9,9\nEND\nBEGIN\n0.1,0\n0.2,0\n0.3,0\nEND\n"
    )

    network = read_citifile(path)

    np.testing.assert_allclose(network.frequencies_hz, [1e6, 2e6, 3e6])
    np.testing.assert_allclose(network.s[:, 0, 0], [0.1, 0.2, 0.3])


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("NAME DATA\n", "CITIFILE keyword"),
        (
            "CITIFILE A.01.00\nVAR FREQ MAG 1\nDATA S[1,1] RI\nDATA S[2,2] RI\n"
            "VAR_LIST_BEGIN\n1\nVAR_LIST_END\nBEGIN\n0,0\nEND\nBEGIN\n0,0\nEND\n",
            "incomplete",
        ),
        (
            "CITIFILE A.01.00\nVAR FREQ MAG 2\nDATA S[1,1] RI\nVAR_LIST_BEGIN\n1\n2\n"
            "VAR_LIST_END\nBEGIN\n0,0\nEND\n",
            "has 1 values",
        ),
        ("CITIFILE A.01.00\nVAR FREQ MAG 1\nDATA S[1,1] RI\nBEGIN\n0,0\n", "unterminated"),
    ],
)
def test_citifile_rejects_invalid_files(tmp_path: Path, body: str, message: str) -> None:
    path = tmp_path / "bad.cti"
    path.write_text(body)

    with pytest.raises(DataFormatError, match=message):
        read_citifile(path)


def test_text_reads_tab_delimited_with_header_unit() -> None:
    assert_fixture(read_text_network(DATA_DIR / "two_port_tab.txt", "tab"), 2)


def test_text_reads_comma_delimited_with_xdata_unit() -> None:
    assert_fixture(read_text_network(DATA_DIR / "two_port_comma.csv", "comma"), 2)


def test_text_uses_the_given_reference_impedance() -> None:
    network = read_text_network(DATA_DIR / "two_port_comma.csv", "comma", z0=75.0)

    assert network.z0 == 75


def test_text_with_the_wrong_delimiter_explains_why() -> None:
    with pytest.raises(DataFormatError, match="check the delimiter"):
        read_text_network(DATA_DIR / "two_port_tab.txt", "comma")


def test_text_rejects_an_incomplete_matrix(tmp_path: Path) -> None:
    path = tmp_path / "partial.csv"
    path.write_text("freq,S11(real),S11(imag),S22(real),S22(imag)\n1,0,0,0,0\n")

    with pytest.raises(DataFormatError, match="incomplete"):
        read_text_network(path, "comma")


@pytest.mark.parametrize(
    ("name", "file_type"),
    [
        ("three_port.s3p", ImportFileType.TOUCHSTONE),
        ("two_port.ts", ImportFileType.TOUCHSTONE_2),
        ("two_port.cti", ImportFileType.CITIFILE),
        ("two_port_tab.txt", ImportFileType.TEXT_TAB),
        ("two_port_comma.csv", ImportFileType.TEXT_COMMA),
    ],
)
def test_read_network_dispatches_on_file_type(name: str, file_type: ImportFileType) -> None:
    network = read_network(DATA_DIR / name, file_type)

    np.testing.assert_allclose(network.frequencies_hz, FREQUENCIES_HZ)


def test_read_network_reports_missing_files() -> None:
    with pytest.raises(DataFormatError, match="not found"):
        read_network(DATA_DIR / "missing.s2p", ImportFileType.TOUCHSTONE)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("a.s2p", ImportFileType.TOUCHSTONE),
        ("a.S16P", ImportFileType.TOUCHSTONE),
        ("a.ts", ImportFileType.TOUCHSTONE_2),
        ("a.cit", ImportFileType.CITIFILE),
        ("a.csv", ImportFileType.TEXT_COMMA),
        ("a.txt", None),
        ("a.sxp", None),
    ],
)
def test_guess_file_type(name: str, expected: ImportFileType | None) -> None:
    assert guess_file_type(name) is expected


def test_build_config_reads_folder_and_port_maps() -> None:
    config = read_build_config(DATA_DIR / "build_config.csv")

    assert config.folder == DATA_DIR / "."
    assert config.n_ports == 3
    second = config.entries[1]
    assert second.path == DATA_DIR / "." / "two_port.ts"
    assert (second.source_ports, second.destination_ports) == ((1, 2), (3, 1))


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("file,a.s2p,[1 2],[1 2]\n", "folder"),
        ("folder,.\nf1,a.s2p,[1 2],[1]\n", "maps 2 source ports"),
        ("folder,.\nf1,a.s2p,[1 2],[1 1]\n", "repeats"),
        ("folder,.\nf1,a.s2p,1 2,[1 2]\n", "port list"),
        ("folder,.\n", "no files"),
    ],
)
def test_build_config_rejects_invalid_rows(tmp_path: Path, body: str, message: str) -> None:
    path = tmp_path / "config.csv"
    path.write_text(body)

    with pytest.raises(DataFormatError, match=message):
        read_build_config(path)


def fixture_s(n_ports: int) -> np.ndarray:
    """2port.* / 4port.* fixtures: S[r][c] = (10r + c)/100 + j(k+1)/100, 1-based r, c."""

    s = np.empty((5, n_ports, n_ports), dtype=np.complex128)
    for k in range(5):
        for row in range(1, n_ports + 1):
            for col in range(1, n_ports + 1):
                s[k, row - 1, col - 1] = (10 * row + col) / 100 + 1j * (k + 1) / 100
    return s


@pytest.mark.parametrize("n_ports", [2, 4])
@pytest.mark.parametrize(
    ("suffix", "file_type"),
    [
        (".s{n}p", ImportFileType.TOUCHSTONE),
        (".ts", ImportFileType.TOUCHSTONE_2),
        (".cti", ImportFileType.CITIFILE),
    ],
)
def test_two_and_four_port_fixtures_read_the_same_in_every_format(
    n_ports: int, suffix: str, file_type: ImportFileType
) -> None:
    path = DATA_DIR / f"{n_ports}port{suffix.format(n=n_ports)}"

    network = read_network(path, file_type)

    assert guess_file_type(path) is file_type
    assert network.n_ports == n_ports
    np.testing.assert_allclose(network.frequencies_hz, [1e9, 2e9, 3e9, 4e9, 5e9])
    np.testing.assert_allclose(network.s, fixture_s(n_ports))
    assert network.z0 == 50


def test_file_types_list_touchstone_1_then_2_then_citifile_first() -> None:
    assert list(ImportFileType)[:3] == [
        ImportFileType.TOUCHSTONE,
        ImportFileType.TOUCHSTONE_2,
        ImportFileType.CITIFILE,
    ]
    assert ImportFileType.TOUCHSTONE.label == "Touchstone 1.0 (*.sNp)"
