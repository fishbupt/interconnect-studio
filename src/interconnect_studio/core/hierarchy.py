"""Data browser hierarchy, mirroring the PLTS Data Browser.

PLTS organises the browser as three fixed levels::

    Category        (Data Analysis / RLCG / Calibration / Template View)
    └── View type   (e.g. "Frequency Domain (Single-Ended)")
        └── Window  (one data file opened in that view, "name : n")

Categories and view types are a fixed catalogue; only windows are created and
closed by the user. A data file is not a tree node on its own: it appears once
under every view type it is opened in. Parameters and display formats are not
tree nodes; they are chosen in the parameter/format panel.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from pathlib import Path

from interconnect_studio.core.errors import InputValidationError
from interconnect_studio.core.network import Network


def _validate_name(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputValidationError(f"{label} must be a non-empty string.")
    return value.strip()


class BrowserCategory(Enum):
    """Top-level nodes of the PLTS Data Browser, in display order."""

    DATA_ANALYSIS = "Data Analysis"
    RLCG = "RLCG"
    CALIBRATION = "Calibration"
    TEMPLATE_VIEW = "Template View"

    @property
    def label(self) -> str:
        """Text shown in the browser."""

        return self.value

    @property
    def view_types(self) -> tuple["ViewType", ...]:
        """Fixed view types under this category, in display order."""

        return tuple(view for view in ViewType if view.category is self)


class ViewType(Enum):
    """Fixed second-level nodes of the PLTS Data Browser, in display order.

    Labels match the PLTS analysis view names, which are also the names PLTS
    uses in window titles and in its remote interface.
    """

    TIME_DOMAIN_DIFFERENTIAL = ("Time Domain (Differential)", BrowserCategory.DATA_ANALYSIS)
    TIME_DOMAIN_SINGLE_ENDED = ("Time Domain (Single-Ended)", BrowserCategory.DATA_ANALYSIS)
    FREQUENCY_DOMAIN_BALANCED = ("Frequency Domain (Balanced)", BrowserCategory.DATA_ANALYSIS)
    FREQUENCY_DOMAIN_SINGLE_ENDED = (
        "Frequency Domain (Single-Ended)",
        BrowserCategory.DATA_ANALYSIS,
    )
    EYE_DIAGRAM_DIFFERENTIAL = ("Eye Diagram (Differential)", BrowserCategory.DATA_ANALYSIS)
    EYE_DIAGRAM_SINGLE_ENDED = ("Eye Diagram (Single-Ended)", BrowserCategory.DATA_ANALYSIS)

    RLCG_DIFFERENTIAL = ("RLCG (Differential)", BrowserCategory.RLCG)
    RLCG_COMMON = ("RLCG (Common)", BrowserCategory.RLCG)
    RLCG_W_ELEMENT = ("RLCG (W-Element)", BrowserCategory.RLCG)
    RLCG_SELF_MUTUAL = ("RLCG (Self/Mutual)", BrowserCategory.RLCG)

    ERROR_TERMS = ("Error Terms", BrowserCategory.CALIBRATION)
    MEASURED_STANDARDS = ("Measured Standards", BrowserCategory.CALIBRATION)

    CREATE_NEW = ("Create New", BrowserCategory.TEMPLATE_VIEW)
    CREATE_NEW_FOR_MULTI_DATA = ("Create New for Multi-data", BrowserCategory.TEMPLATE_VIEW)

    @property
    def label(self) -> str:
        """Text shown in the browser."""

        label: str = self.value[0]
        return label

    @property
    def category(self) -> BrowserCategory:
        """Category this view type sits under."""

        category: BrowserCategory = self.value[1]
        return category


@dataclass(frozen=True, slots=True)
class DataFile:
    """One imported file, or one algorithm result.

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
class ViewWindow:
    """Leaf node: one data file opened in one view type.

    ``number`` is the window's sequence number, unique across the browser, and
    is shown after the file name as PLTS does ("dut.s2p : 1").
    """

    view_type: ViewType
    data_file: DataFile
    number: int

    def __post_init__(self) -> None:
        if not isinstance(self.view_type, ViewType):
            raise InputValidationError("ViewWindow view_type must be a ViewType.")
        if not isinstance(self.data_file, DataFile):
            raise InputValidationError("ViewWindow data_file must be a DataFile.")
        if isinstance(self.number, bool) or not isinstance(self.number, int) or self.number < 1:
            raise InputValidationError("ViewWindow number must be a positive integer.")

    @property
    def label(self) -> str:
        """Text shown in the browser."""

        return f"{self.data_file.name} : {self.number}"


@dataclass(frozen=True, slots=True)
class DataBrowserTree:
    """Open windows of the browser; categories and view types are implicit."""

    windows: tuple[ViewWindow, ...] = field(default=())

    def __post_init__(self) -> None:
        if not isinstance(self.windows, tuple) or not all(
            isinstance(item, ViewWindow) for item in self.windows
        ):
            raise InputValidationError("DataBrowserTree windows must be a tuple of ViewWindow.")

        numbers = [item.number for item in self.windows]
        if len(set(numbers)) != len(numbers):
            raise InputValidationError("ViewWindow numbers must be unique.")

    def windows_of(self, view_type: ViewType) -> tuple[ViewWindow, ...]:
        """Windows open under one view type, in opening order."""

        return tuple(item for item in self.windows if item.view_type is view_type)

    @property
    def next_number(self) -> int:
        """Sequence number for the next window to open."""

        return max((item.number for item in self.windows), default=0) + 1

    def open(
        self, view_type: ViewType, data_file: DataFile
    ) -> tuple["DataBrowserTree", ViewWindow]:
        """Return a tree with one more window, and that window."""

        window = ViewWindow(view_type=view_type, data_file=data_file, number=self.next_number)
        return DataBrowserTree(windows=(*self.windows, window)), window

    def window(self, number: int) -> ViewWindow:
        """The open window with this number."""

        for item in self.windows:
            if item.number == number:
                return item
        raise InputValidationError(f"Window {number} is not open.")

    def windows_of_file(self, file_id: str) -> tuple[ViewWindow, ...]:
        """Windows showing one data file, in opening order."""

        return tuple(item for item in self.windows if item.data_file.id == file_id)

    def close_window(self, number: int) -> "DataBrowserTree":
        """Return a tree without one window (PLTS "Close View")."""

        self.window(number)
        return DataBrowserTree(windows=tuple(w for w in self.windows if w.number != number))

    def close_file(self, file_id: str) -> "DataBrowserTree":
        """Return a tree without every window of one data file (PLTS "Close File")."""

        if not self.windows_of_file(file_id):
            raise InputValidationError(f"Data file {file_id} is not open.")
        return DataBrowserTree(windows=tuple(w for w in self.windows if w.data_file.id != file_id))

    def rename_file(self, file_id: str, name: str) -> "DataBrowserTree":
        """Return a tree where one data file has a new display name (PLTS "Rename File").

        Every window of the file shows the new name; the file ``id``, which
        traces refer to, is unchanged.
        """

        if not self.windows_of_file(file_id):
            raise InputValidationError(f"Data file {file_id} is not open.")
        renamed = replace(self.windows_of_file(file_id)[0].data_file, name=name)
        return DataBrowserTree(
            windows=tuple(
                replace(w, data_file=renamed) if w.data_file.id == file_id else w
                for w in self.windows
            )
        )
