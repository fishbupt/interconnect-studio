import numpy as np
import pytest

from interconnect_studio.core import InputValidationError, Trace


def test_trace_accepts_real_data_and_copies_inputs() -> None:
    x = np.array([1.0, 2.0, 3.0])
    y = np.array([10.0, 20.0, 30.0])
    trace = Trace("S21 LogMag", x, y, x_unit="Hz", y_unit="dB")

    x[0] = 99.0
    y[0] = 99.0

    np.testing.assert_array_equal(trace.x, [1.0, 2.0, 3.0])
    np.testing.assert_array_equal(trace.y, [10.0, 20.0, 30.0])
    assert trace.n_points == 3
    assert trace.is_complex is False
    assert trace.name == "S21 LogMag"


def test_trace_accepts_complex_data() -> None:
    trace = Trace("S11 Smith", [1.0, 2.0], [0.1 + 0.2j, 0.2 + 0.3j])

    assert trace.is_complex is True
    assert trace.y.dtype == np.complex128


def test_trace_arrays_are_read_only() -> None:
    trace = Trace("trace", [1.0, 2.0], [1.0, 2.0])

    assert trace.x.flags.writeable is False
    assert trace.y.flags.writeable is False
    with pytest.raises(ValueError):
        trace.y[0] = 3.0


def test_trace_allows_non_finite_y_for_display_singularities() -> None:
    trace = Trace("log", [1.0, 2.0], [-np.inf, np.nan], y_unit="dB")

    assert np.isneginf(trace.y[0])
    assert np.isnan(trace.y[1])


@pytest.mark.parametrize(
    ("x", "y", "message"),
    [
        ([[1.0, 2.0]], [1.0, 2.0], "x must be one-dimensional"),
        ([1.0, 2.0], [[1.0, 2.0]], "y must be one-dimensional"),
        ([], [], "at least one point"),
        ([1.0, 2.0], [1.0], "same number"),
        ([1.0, np.nan], [1.0, 2.0], "finite"),
        ([1.0, 1.0], [1.0, 2.0], "strictly increasing"),
        ([2.0, 1.0], [1.0, 2.0], "strictly increasing"),
    ],
)
def test_trace_rejects_invalid_arrays(
    x: object,
    y: object,
    message: str,
) -> None:
    with pytest.raises(InputValidationError, match=message):
        Trace("trace", x, y)


def test_trace_rejects_empty_name() -> None:
    with pytest.raises(InputValidationError, match="name"):
        Trace("  ", [1.0], [1.0])


def test_trace_defaults_to_no_source() -> None:
    trace = Trace("S21", [1.0, 2.0], [1.0, 2.0])

    assert trace.source_id == ""


def test_trace_keeps_source_id() -> None:
    trace = Trace("S21", [1.0, 2.0], [1.0, 2.0], source_id="file-1")

    assert trace.source_id == "file-1"


def test_trace_rejects_non_string_source_id() -> None:
    with pytest.raises(InputValidationError, match="source_id"):
        Trace("S21", [1.0, 2.0], [1.0, 2.0], source_id=1)  # type: ignore[arg-type]
