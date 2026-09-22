from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from interconnect_studio.core import (
    DataFile,
    Group,
    InputValidationError,
    Measurement,
    Network,
)


def network() -> Network:
    return Network([1.0e9, 2.0e9], np.zeros((2, 2, 2), dtype=np.complex128), z0=50.0)


def data_file(file_id: str = "f1", name: str = "DUT") -> DataFile:
    return DataFile(id=file_id, name=name, network=network())


def test_data_file_keeps_source_metadata() -> None:
    imported = datetime(2026, 1, 1, 12, 0, 0)
    item = DataFile(
        id="f1",
        name="DUT",
        network=network(),
        source_path=Path("dut.s2p"),
        imported_at=imported,
    )

    assert item.source_path == Path("dut.s2p")
    assert item.imported_at == imported


def test_data_file_allows_missing_source_for_algorithm_results() -> None:
    item = data_file()

    assert item.source_path is None


@pytest.mark.parametrize("bad_name", ["", "   "])
def test_data_file_rejects_empty_identifiers(bad_name: str) -> None:
    with pytest.raises(InputValidationError, match="non-empty"):
        DataFile(id=bad_name, name="DUT", network=network())


def test_data_file_strips_surrounding_whitespace() -> None:
    item = DataFile(id="  f1  ", name="  DUT  ", network=network())

    assert item.id == "f1"
    assert item.name == "DUT"


def test_data_file_rejects_non_network() -> None:
    with pytest.raises(InputValidationError, match="must be a Network"):
        DataFile(id="f1", name="DUT", network="not a network")  # type: ignore[arg-type]


def test_measurement_holds_files() -> None:
    measurement = Measurement(name="Run 1", files=(data_file("f1"), data_file("f2")))

    assert len(measurement.files) == 2


def test_measurement_defaults_to_no_files() -> None:
    assert Measurement(name="Run 1").files == ()


def test_measurement_rejects_duplicate_file_ids() -> None:
    with pytest.raises(InputValidationError, match="unique"):
        Measurement(name="Run 1", files=(data_file("f1"), data_file("f1", name="Other")))


def test_group_holds_measurements() -> None:
    group = Group(name="Board A", measurements=(Measurement(name="Run 1"),))

    assert group.measurements[0].name == "Run 1"


def test_group_rejects_non_measurement_children() -> None:
    with pytest.raises(InputValidationError, match="tuple of Measurement"):
        Group(name="Board A", measurements=(data_file(),))  # type: ignore[arg-type]


def test_hierarchy_is_immutable() -> None:
    group = Group(name="Board A")

    with pytest.raises(AttributeError):
        group.name = "new"  # type: ignore[misc]
