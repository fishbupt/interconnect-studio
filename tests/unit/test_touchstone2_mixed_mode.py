"""Touchstone 2.0 ``[Mixed-Mode Order]``.

The fixtures are written out in full rather than generated, so the expected
answer is readable next to the file that produces it. The reference case is
one differential pair per end of an ideal matched line: in mixed mode that
is a diagonal ``Sdd21`` / ``Scc21``, and the single-ended matrix it must
come back as is written out by hand.
"""

from pathlib import Path

import numpy as np
import pytest

from interconnect_studio.core import DataFormatError
from interconnect_studio.io.touchstone2 import (
    read_touchstone2,
    read_touchstone2_with_pairs,
)

# Two ideal matched lines, 1->2 and 3->4, both with transmission t.
# Pairing {1,3} and {2,4} makes Sdd21 = Scc21 = t and no mode conversion,
# so the mixed-mode matrix is two identical 2x2 blocks.
T = 0.5

HEADER = """[Version] 2.0
# GHz S RI R 50
[Number of Ports] 4
[Mixed-Mode Order] {order}
[Number of Frequencies] 1
[Network Data]
"""


def block_ordered_rows(order: str) -> str:
    """One frequency record whose rows follow ``order``.

    ``order`` names the file's declared rows; the values are placed so that
    every declaration describes the same physical network.
    """

    mixed = {
        ("D", 0): {("D", 1): T},
        ("D", 1): {("D", 0): T},
        ("C", 0): {("C", 1): T},
        ("C", 1): {("C", 0): T},
    }
    rows = [_row_key(entry) for entry in order.split()]
    values = ["1.0"]
    for row in rows:
        for column in rows:
            value = mixed.get(row, {}).get(column, 0.0)
            values.extend([f"{value:g}", "0"])
    return " ".join(values) + "\n"


def _row_key(descriptor: str) -> tuple[str, int]:
    """``D1,3`` -> ``("D", 0)``: which mode, and which pair (declaration order)."""

    kind, ports = descriptor[0], descriptor[1:]
    pair = 0 if ports in {"1,3", "2,4"} and ports == "1,3" else 1
    return kind, pair


def write_file(tmp_path: Path, order: str, rows: str | None = None) -> Path:
    path = tmp_path / "mixed.ts"
    body = rows if rows is not None else block_ordered_rows(order)
    path.write_text(HEADER.format(order=order) + body + "[End]\n", encoding="utf-8")
    return path


def expected_single_ended() -> np.ndarray:
    """Two matched through lines, 1->2 and 3->4."""

    s = np.zeros((1, 4, 4), dtype=np.complex128)
    for near, far in ((0, 1), (2, 3)):
        s[0, far, near] = s[0, near, far] = T
    return s


@pytest.mark.parametrize(
    "order",
    ["D1,3 D2,4 C1,3 C2,4", "D1,3 C1,3 D2,4 C2,4", "C2,4 D2,4 C1,3 D1,3"],
    ids=["block", "interleaved", "reversed"],
)
def test_any_declared_order_gives_the_same_network(tmp_path: Path, order: str) -> None:
    """The file may declare rows in any order; we permute to block order."""

    network = read_touchstone2(write_file(tmp_path, order))

    np.testing.assert_allclose(network.s, expected_single_ended(), atol=1e-15)


def test_the_declared_pairing_comes_back_with_the_network(tmp_path: Path) -> None:
    _, port_group = read_touchstone2_with_pairs(write_file(tmp_path, "D1,3 D2,4 C1,3 C2,4"))

    assert port_group is not None
    assert [line.near for line in port_group.lines] == [(0, 2), (1, 3)]


def test_no_through_path_is_invented_for_the_pairs(tmp_path: Path) -> None:
    """The file says which ports pair, not which pairs face each other."""

    _, port_group = read_touchstone2_with_pairs(write_file(tmp_path, "D1,3 D2,4 C1,3 C2,4"))

    assert port_group is not None
    assert all(line.far == () for line in port_group.lines)


def test_polarity_follows_the_declared_order(tmp_path: Path) -> None:
    """``D3,1`` is the same pair as ``D1,3`` with the conductors swapped."""

    _, port_group = read_touchstone2_with_pairs(write_file(tmp_path, "D3,1 D2,4 C3,1 C2,4"))

    assert port_group is not None
    assert port_group.lines[0].near == (2, 0)


def test_a_single_ended_file_reports_no_pairing(tmp_path: Path) -> None:
    path = tmp_path / "plain.ts"
    path.write_text(
        "[Version] 2.0\n# GHz S RI R 50\n[Number of Ports] 1\n"
        "[Number of Frequencies] 1\n[Network Data]\n1.0 0.5 0\n[End]\n",
        encoding="utf-8",
    )

    network, port_group = read_touchstone2_with_pairs(path)

    assert port_group is None
    assert network.n_ports == 1


def test_mixing_single_ended_ports_in_is_refused_with_the_ports_named(
    tmp_path: Path,
) -> None:
    """The domain model has no room for an unpaired mode port, so say so."""

    with pytest.raises(DataFormatError, match=r"single-ended ports \(2, 4\)"):
        read_touchstone2(write_file(tmp_path, "D1,3 C1,3 S2 S4", rows="1.0 " + "0 0 " * 16))


def test_the_two_modes_of_a_pair_must_agree_on_polarity(tmp_path: Path) -> None:
    """``D1,3`` with ``C3,1`` leaves it ambiguous which conductor is positive."""

    with pytest.raises(DataFormatError, match="both modes must name the conductors"):
        read_touchstone2(
            write_file(tmp_path, "D1,3 C3,1 D2,4 C2,4", rows="1.0 " + "0 0 " * 16)
        )


def test_a_port_used_by_two_pairs_is_refused(tmp_path: Path) -> None:
    with pytest.raises(DataFormatError, match="port 3 in both"):
        read_touchstone2(
            write_file(tmp_path, "D1,3 D3,4 C1,3 C3,4", rows="1.0 " + "0 0 " * 16)
        )


def test_the_entry_count_must_match_the_port_count(tmp_path: Path) -> None:
    with pytest.raises(DataFormatError, match="lists 2 entries for 4 ports"):
        read_touchstone2(write_file(tmp_path, "D1,3 C1,3", rows="1.0 " + "0 0 " * 16))


def test_a_port_beyond_the_file_is_refused(tmp_path: Path) -> None:
    with pytest.raises(DataFormatError, match="names port 9"):
        read_touchstone2(
            write_file(tmp_path, "D1,9 D2,4 C1,9 C2,4", rows="1.0 " + "0 0 " * 16)
        )


@pytest.mark.parametrize(
    ("order", "message"),
    [
        ("D1 D2,4 C1,3 C2,4", "names one port"),
        ("S1,3 D2,4 C1,3 C2,4", "names two ports"),
        ("X1,3 D2,4 C1,3 C2,4", "expected S<n>"),
    ],
)
def test_malformed_entries_name_what_is_wrong(
    tmp_path: Path, order: str, message: str
) -> None:
    with pytest.raises(DataFormatError, match=message):
        read_touchstone2(write_file(tmp_path, order, rows="1.0 " + "0 0 " * 16))


def test_an_empty_keyword_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "empty.ts"
    path.write_text(
        "[Version] 2.0\n# GHz S RI R 50\n[Number of Ports] 4\n[Mixed-Mode Order]\n",
        encoding="utf-8",
    )

    with pytest.raises(DataFormatError, match="lists no ports"):
        read_touchstone2(path)


def test_a_declaration_repeated_is_refused(tmp_path: Path) -> None:
    with pytest.raises(DataFormatError, match="declares D1,3 twice"):
        read_touchstone2(
            write_file(tmp_path, "D1,3 D1,3 C1,3 C2,4", rows="1.0 " + "0 0 " * 16)
        )
