"""A mixed-mode Touchstone 2.0 file built from the coupled-pair golden case.

The unit tests cover the format on small hand-written files. This covers the
path a real file takes: a physically shaped 4-port, written out as mixed-mode
data in a declaration order that is deliberately not our block order, and
read back. It has to return the single-ended matrix the golden case holds,
which is the only thing that makes such a file usable downstream.

The file is generated into ``tmp_path`` rather than committed: it is 137 kB
of numbers derived from data already in the repository, and a second copy
could drift from the first.
"""

from pathlib import Path

import numpy as np

from interconnect_studio.algorithms.mixed_mode import to_mixed_mode, topology_by_id
from interconnect_studio.core import Network
from interconnect_studio.io.touchstone import read_touchstone
from interconnect_studio.io.touchstone2 import read_touchstone2_with_pairs

GOLDEN_ROOT = Path(__file__).resolve().parents[2] / "golden_data" / "mixed_mode"

# Declared per pair rather than in block order, so a reader that ignored
# [Mixed-Mode Order] and assumed our own layout would fail here.
DECLARED_ORDER = "D1,3 C1,3 D2,4 C2,4"
FILE_ROW_FOR_OUR_ROW = (0, 2, 1, 3)


def coupled_pair() -> Network:
    return read_touchstone(
        GOLDEN_ROOT / "Case001_coupled_pair" / "input" / "coupled_pair.s4p"
    )


def write_mixed_mode_file(network: Network, path: Path) -> Path:
    """Write ``network`` as mixed-mode Touchstone 2.0 in DECLARED_ORDER."""

    mixed = to_mixed_mode(network, topology_by_id("through_1_2_3_4").port_group)
    rows = list(FILE_ROW_FOR_OUR_ROW)
    s = mixed.s[:, rows, :][:, :, rows]

    lines = [
        "[Version] 2.0",
        "# GHz S RI R 50",
        "[Number of Ports] 4",
        f"[Mixed-Mode Order] {DECLARED_ORDER}",
        f"[Number of Frequencies] {network.n_freq}",
        "[Network Data]",
    ]
    for point in range(network.n_freq):
        values = [f"{network.frequencies_hz[point] / 1e9:.17g}"]
        for row in range(4):
            for column in range(4):
                value = s[point, row, column]
                values += [f"{value.real:.17g}", f"{value.imag:.17g}"]
        lines.append(" ".join(values))
    lines.append("[End]")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_a_mixed_mode_file_reads_back_as_its_single_ended_network(
    tmp_path: Path,
) -> None:
    original = coupled_pair()
    path = write_mixed_mode_file(original, tmp_path / "coupled_pair.ts")

    recovered, port_group = read_touchstone2_with_pairs(path)

    np.testing.assert_allclose(recovered.s, original.s, rtol=1e-12, atol=1e-14)
    np.testing.assert_allclose(
        recovered.frequencies_hz, original.frequencies_hz, rtol=1e-12
    )
    assert recovered.z0 == original.z0
    assert port_group is not None


def test_the_recovered_pairing_reproduces_the_mixed_mode_parameters(
    tmp_path: Path,
) -> None:
    """The pairing has to be usable, not merely present.

    Converting the recovered network with the port group the file declared
    must give back the mixed-mode matrix the file carried.
    """

    original = coupled_pair()
    path = write_mixed_mode_file(original, tmp_path / "coupled_pair.ts")
    expected = to_mixed_mode(original, topology_by_id("through_1_2_3_4").port_group)

    recovered, port_group = read_touchstone2_with_pairs(path)
    assert port_group is not None

    np.testing.assert_allclose(
        to_mixed_mode(recovered, port_group).s, expected.s, rtol=1e-12, atol=1e-14
    )


def test_the_declared_pairs_are_the_ones_the_topology_implies(tmp_path: Path) -> None:
    """Through 1-2, 3-4 pairs ports 1,3 at one end and 2,4 at the other."""

    path = write_mixed_mode_file(coupled_pair(), tmp_path / "coupled_pair.ts")

    _, port_group = read_touchstone2_with_pairs(path)

    assert port_group is not None
    assert [line.near for line in port_group.lines] == [(0, 2), (1, 3)]
