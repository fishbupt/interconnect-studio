import pytest

from interconnect_studio.core import InputValidationError, Line, PortGroup


def test_differential_line_reports_its_ports() -> None:
    line = Line(name="Pair 1", near=(0, 2), far=(1, 3))

    assert line.is_differential is True
    assert line.ports == (0, 2, 1, 3)


def test_single_ended_line_is_not_differential() -> None:
    assert Line(name="Line 1", near=(0,), far=(1,)).is_differential is False


def test_tuple_order_carries_polarity() -> None:
    """A crossed topology puts the higher index first at the far end."""

    line = Line(name="Pair 1", near=(0, 1), far=(3, 2))

    assert line.far[0] == 3


def test_line_rejects_mismatched_end_sizes() -> None:
    with pytest.raises(InputValidationError, match="same number of ports"):
        Line(name="Pair 1", near=(0, 1), far=(2,))


def test_line_rejects_duplicate_ports() -> None:
    with pytest.raises(InputValidationError, match="unique"):
        Line(name="Pair 1", near=(0, 1), far=(1, 2))


def test_line_rejects_negative_ports() -> None:
    with pytest.raises(InputValidationError, match="non-negative"):
        Line(name="Pair 1", near=(0, -1), far=(2, 3))


def test_line_rejects_empty_name() -> None:
    with pytest.raises(InputValidationError, match="non-empty"):
        Line(name="  ", near=(0, 1), far=(2, 3))


def test_port_group_counts_ports() -> None:
    group = PortGroup(lines=(Line(name="Pair 1", near=(0, 2), far=(1, 3)),))

    assert group.n_ports == 4
    assert group.is_differential is True


def test_port_group_rejects_a_port_in_two_lines() -> None:
    with pytest.raises(InputValidationError, match="only one Line"):
        PortGroup(
            lines=(
                Line(name="Pair 1", near=(0, 1), far=(2, 3)),
                Line(name="Pair 2", near=(0, 5), far=(6, 7)),
            )
        )


def test_port_group_rejects_duplicate_line_names() -> None:
    with pytest.raises(InputValidationError, match="names must be unique"):
        PortGroup(
            lines=(
                Line(name="Pair 1", near=(0, 1), far=(2, 3)),
                Line(name="Pair 1", near=(4, 5), far=(6, 7)),
            )
        )


def test_port_group_rejects_empty() -> None:
    with pytest.raises(InputValidationError, match="at least one Line"):
        PortGroup(lines=())


def test_validate_covers_accepts_a_complete_grouping() -> None:
    PortGroup(lines=(Line(name="Pair 1", near=(0, 2), far=(1, 3)),)).validate_covers(4)


def test_validate_covers_rejects_a_gap() -> None:
    group = PortGroup(lines=(Line(name="Pair 1", near=(0, 2), far=(1, 5)),))

    with pytest.raises(InputValidationError, match="cover exactly"):
        group.validate_covers(4)
