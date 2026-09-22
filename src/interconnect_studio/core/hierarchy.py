"""Data browser hierarchy: Group -> Measurement -> DataFile.

The three levels are fixed: nodes cannot nest deeper and levels cannot be
skipped. Parameters and display formats are not tree nodes; they are chosen
in the parameter/format panel.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from interconnect_studio.core.errors import InputValidationError
from interconnect_studio.core.network import Network


def _validate_name(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputValidationError(f"{label} must be a non-empty string.")
    return value.strip()


@dataclass(frozen=True, slots=True)
class DataFile:
    """Leaf node: one imported file, or one algorithm result.

    ``source_path`` is the file it was read from, and is ``None`` for results
    produced by algorithms. ``id`` is stable across renames and is what
    ``Trace.source_id`` refers to.
    """

    id: str
    name: str
    network: Network
    source_path: Path | None = None
    imported_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _validate_name(self.id, "DataFile id"))
        object.__setattr__(self, "name", _validate_name(self.name, "DataFile name"))
        if not isinstance(self.network, Network):
            raise InputValidationError("DataFile network must be a Network.")
        if self.source_path is not None and not isinstance(self.source_path, Path):
            raise InputValidationError("DataFile source_path must be a Path or None.")
        if self.imported_at is not None and not isinstance(self.imported_at, datetime):
            raise InputValidationError("DataFile imported_at must be a datetime or None.")


@dataclass(frozen=True, slots=True)
class Measurement:
    """Container of data files."""

    name: str
    files: tuple[DataFile, ...] = field(default=())

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _validate_name(self.name, "Measurement name"))
        if not isinstance(self.files, tuple) or not all(
            isinstance(item, DataFile) for item in self.files
        ):
            raise InputValidationError("Measurement files must be a tuple of DataFile objects.")

        ids = [item.id for item in self.files]
        if len(set(ids)) != len(ids):
            raise InputValidationError("Measurement file ids must be unique.")


@dataclass(frozen=True, slots=True)
class Group:
    """Top-level container of measurements."""

    name: str
    measurements: tuple[Measurement, ...] = field(default=())

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _validate_name(self.name, "Group name"))
        if not isinstance(self.measurements, tuple) or not all(
            isinstance(item, Measurement) for item in self.measurements
        ):
            raise InputValidationError("Group measurements must be a tuple of Measurement objects.")
