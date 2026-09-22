"""Qt adapter over the Group / Measurement / DataFile hierarchy."""

from typing import Final

from PyQt6.QtCore import QAbstractItemModel, QModelIndex, QObject, Qt

from interconnect_studio.core import DataFile, Group, Measurement

# Qt requires these signatures to default to a null index; a module-level
# singleton keeps that without constructing one per call.
_NULL_INDEX: Final[QModelIndex] = QModelIndex()

_GROUP_DEPTH: Final[int] = 0
_MEASUREMENT_DEPTH: Final[int] = 1
_FILE_DEPTH: Final[int] = 2


class _Node:
    """Internal tree node.

    Qt needs a stable object per row to put in ``QModelIndex.internalPointer``;
    the domain objects are immutable values and cannot carry a parent link, so
    the model keeps this parallel structure and holds references to it.
    """

    __slots__ = ("children", "depth", "payload", "parent", "row")

    def __init__(self, payload: object, depth: int, parent: "_Node | None", row: int) -> None:
        self.payload = payload
        self.depth = depth
        self.parent = parent
        self.row = row
        self.children: list[_Node] = []


class DataBrowserModel(QAbstractItemModel):
    """Read-only tree model over the fixed three-level hierarchy.

    The tree ends at ``DataFile``: parameters and display formats are chosen
    in the parameter/format panel, not here.
    """

    def __init__(
        self,
        groups: tuple[Group, ...] = (),
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._groups: tuple[Group, ...] = ()
        self._roots: list[_Node] = []
        self.set_groups(groups)

    @property
    def groups(self) -> tuple[Group, ...]:
        """Hierarchy currently exposed."""

        return self._groups

    def set_groups(self, groups: tuple[Group, ...]) -> None:
        """Replace the whole hierarchy."""

        self.beginResetModel()
        self._groups = groups
        self._roots = [self._build_group(group, row) for row, group in enumerate(groups)]
        self.endResetModel()

    def data_file_at(self, index: QModelIndex) -> DataFile | None:
        """Return the data file an index points at, or None for other rows."""

        if not index.isValid():
            return None
        node = index.internalPointer()
        if not isinstance(node, _Node) or node.depth != _FILE_DEPTH:
            return None
        payload = node.payload
        return payload if isinstance(payload, DataFile) else None

    def index_of_data_file(self, file_id: str) -> QModelIndex:
        """Return the index of a data file by id, or an invalid index."""

        for group_node in self._roots:
            for measurement_node in group_node.children:
                for file_node in measurement_node.children:
                    payload = file_node.payload
                    if isinstance(payload, DataFile) and payload.id == file_id:
                        return self.createIndex(file_node.row, 0, file_node)
        return QModelIndex()

    def index(self, row: int, column: int, parent: QModelIndex = _NULL_INDEX) -> QModelIndex:
        """Return the index of a child row."""

        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        siblings = self._children_of(parent)
        if row >= len(siblings):
            return QModelIndex()
        return self.createIndex(row, column, siblings[row])

    def parent(self, index: QModelIndex = _NULL_INDEX) -> QModelIndex:  # type: ignore[override]
        """Return the index of a row's parent."""

        if not index.isValid():
            return QModelIndex()
        node = index.internalPointer()
        if not isinstance(node, _Node) or node.parent is None:
            return QModelIndex()
        return self.createIndex(node.parent.row, 0, node.parent)

    def rowCount(self, parent: QModelIndex = _NULL_INDEX) -> int:  # noqa: N802
        """Number of children of a row."""

        if parent.column() > 0:
            return 0
        return len(self._children_of(parent))

    def columnCount(self, parent: QModelIndex = _NULL_INDEX) -> int:  # noqa: N802
        """The tree shows names only."""

        return 1

    def data(
        self,
        index: QModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        """Display name of a row."""

        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        node = index.internalPointer()
        if not isinstance(node, _Node):
            return None
        payload = node.payload
        if isinstance(payload, Group | Measurement | DataFile):
            return payload.name
        return None

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        """The dock title already names the panel, so no header text."""

        return None

    def _children_of(self, parent: QModelIndex) -> list[_Node]:
        if not parent.isValid():
            return self._roots
        node = parent.internalPointer()
        return node.children if isinstance(node, _Node) else []

    def _build_group(self, group: Group, row: int) -> _Node:
        node = _Node(group, _GROUP_DEPTH, None, row)
        for measurement_row, measurement in enumerate(group.measurements):
            node.children.append(self._build_measurement(measurement, node, measurement_row))
        return node

    def _build_measurement(self, measurement: Measurement, parent: _Node, row: int) -> _Node:
        node = _Node(measurement, _MEASUREMENT_DEPTH, parent, row)
        for file_row, data_file in enumerate(measurement.files):
            node.children.append(_Node(data_file, _FILE_DEPTH, node, file_row))
        return node
