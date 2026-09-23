"""Qt adapter over the PLTS-style data browser hierarchy."""

from collections.abc import Iterable
from typing import Final

from PyQt6.QtCore import QAbstractItemModel, QModelIndex, QObject, Qt
from PyQt6.QtGui import QFont, QIcon

from interconnect_studio.core import (
    BrowserCategory,
    DataBrowserTree,
    DataFile,
    ViewType,
    ViewWindow,
)
from interconnect_studio.ui.icons import FolderKind, document_icon, folder_icon

# Qt requires these signatures to default to a null index; a module-level
# singleton keeps that without constructing one per call.
_NULL_INDEX: Final[QModelIndex] = QModelIndex()

_CATEGORY_DEPTH: Final[int] = 0
_VIEW_TYPE_DEPTH: Final[int] = 1
_WINDOW_DEPTH: Final[int] = 2

# View types the application can display today. The rest of the PLTS
# catalogue is still shown, greyed out, so the tree keeps the PLTS layout.
DEFAULT_AVAILABLE_VIEW_TYPES: Final[frozenset[ViewType]] = frozenset(
    {ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED}
)

_UNAVAILABLE_TOOLTIP: Final[str] = "Not available yet"


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
    """Read-only tree model: category -> view type -> window.

    Categories and view types always appear, whether or not any window is
    open, as in PLTS. Only windows depend on the tree passed in. Parameters and
    display formats are chosen in the parameter/format panel, not here.
    """

    def __init__(
        self,
        tree: DataBrowserTree | None = None,
        available_view_types: Iterable[ViewType] = DEFAULT_AVAILABLE_VIEW_TYPES,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._available = frozenset(available_view_types)
        self._expanded: set[BrowserCategory | ViewType] = set()
        self._tree = DataBrowserTree()
        self._roots: list[_Node] = []
        self.set_tree(tree or DataBrowserTree())

    @property
    def tree(self) -> DataBrowserTree:
        """Hierarchy currently exposed."""

        return self._tree

    def set_tree(self, tree: DataBrowserTree) -> None:
        """Replace the open windows."""

        self.beginResetModel()
        self._tree = tree
        # A reset collapses every row in attached views, so no folder is open.
        self._expanded.clear()
        self._roots = [
            self._build_category(category, row) for row, category in enumerate(BrowserCategory)
        ]
        self.endResetModel()

    def is_available(self, view_type: ViewType) -> bool:
        """Whether the application can display this view type yet."""

        return view_type in self._available

    def set_expanded(self, index: QModelIndex, expanded: bool) -> None:
        """Record whether a folder row is expanded, so its icon opens or closes.

        Views call this from their expanded / collapsed signals; the model has
        no other way to learn the expansion state.
        """

        node = self._node(index)
        if node is None or not isinstance(node.payload, BrowserCategory | ViewType):
            return
        if expanded:
            self._expanded.add(node.payload)
        else:
            self._expanded.discard(node.payload)
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DecorationRole])

    def view_type_at(self, index: QModelIndex) -> ViewType | None:
        """Return the view type an index points at, or None for other rows."""

        node = self._node(index)
        if node is None or node.depth != _VIEW_TYPE_DEPTH:
            return None
        payload = node.payload
        return payload if isinstance(payload, ViewType) else None

    def window_at(self, index: QModelIndex) -> ViewWindow | None:
        """Return the window an index points at, or None for other rows."""

        node = self._node(index)
        if node is None or node.depth != _WINDOW_DEPTH:
            return None
        payload = node.payload
        return payload if isinstance(payload, ViewWindow) else None

    def data_file_at(self, index: QModelIndex) -> DataFile | None:
        """Return the data file of the window an index points at, if any."""

        window = self.window_at(index)
        return window.data_file if window is not None else None

    def index_of_category(self, category: BrowserCategory) -> QModelIndex:
        """Return the index of a category row."""

        for node in self._roots:
            if node.payload is category:
                return self.createIndex(node.row, 0, node)
        return QModelIndex()

    def index_of_view_type(self, view_type: ViewType) -> QModelIndex:
        """Return the index of a view type row."""

        for category_node in self._roots:
            for view_node in category_node.children:
                if view_node.payload is view_type:
                    return self.createIndex(view_node.row, 0, view_node)
        return QModelIndex()

    def index_of_window(self, number: int) -> QModelIndex:
        """Return the index of a window by its number, or an invalid index."""

        for category_node in self._roots:
            for view_node in category_node.children:
                for window_node in view_node.children:
                    payload = window_node.payload
                    if isinstance(payload, ViewWindow) and payload.number == number:
                        return self.createIndex(window_node.row, 0, window_node)
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

        node = self._node(index)
        if node is None or node.parent is None:
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
    ) -> str | QIcon | QFont | None:
        """Name, folder or page icon, category font, and unavailable tooltip."""

        node = self._node(index)
        if node is None:
            return None
        payload = node.payload
        if role == Qt.ItemDataRole.DisplayRole:
            if isinstance(payload, BrowserCategory | ViewType | ViewWindow):
                return payload.label
            return None
        if role == Qt.ItemDataRole.DecorationRole:
            return self._icon(payload)
        if role == Qt.ItemDataRole.FontRole and isinstance(payload, BrowserCategory):
            font = QFont()
            font.setBold(True)
            return font
        if role == Qt.ItemDataRole.ToolTipRole and not self._is_enabled(node):
            return _UNAVAILABLE_TOOLTIP
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Windows are selectable; unavailable view types are greyed out."""

        node = self._node(index)
        if node is None or not self._is_enabled(node):
            return Qt.ItemFlag.NoItemFlags
        if node.depth == _WINDOW_DEPTH:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        return Qt.ItemFlag.ItemIsEnabled

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        """The dock title already names the panel, so no header text."""

        return None

    def _node(self, index: QModelIndex) -> _Node | None:
        if not index.isValid():
            return None
        node = index.internalPointer()
        return node if isinstance(node, _Node) else None

    def _icon(self, payload: object) -> QIcon | None:
        if isinstance(payload, BrowserCategory):
            return folder_icon(FolderKind.CATEGORY, is_open=payload in self._expanded)
        if isinstance(payload, ViewType):
            return folder_icon(FolderKind.VIEW_TYPE, is_open=payload in self._expanded)
        if isinstance(payload, ViewWindow):
            return document_icon()
        return None

    def _is_enabled(self, node: _Node) -> bool:
        payload = node.payload
        if isinstance(payload, BrowserCategory):
            return any(self.is_available(view) for view in payload.view_types)
        if isinstance(payload, ViewType):
            return self.is_available(payload)
        if isinstance(payload, ViewWindow):
            return self.is_available(payload.view_type)
        return False

    def _children_of(self, parent: QModelIndex) -> list[_Node]:
        if not parent.isValid():
            return self._roots
        node = parent.internalPointer()
        return node.children if isinstance(node, _Node) else []

    def _build_category(self, category: BrowserCategory, row: int) -> _Node:
        node = _Node(category, _CATEGORY_DEPTH, None, row)
        for view_row, view_type in enumerate(category.view_types):
            node.children.append(self._build_view_type(view_type, node, view_row))
        return node

    def _build_view_type(self, view_type: ViewType, parent: _Node, row: int) -> _Node:
        node = _Node(view_type, _VIEW_TYPE_DEPTH, parent, row)
        for window_row, window in enumerate(self._tree.windows_of(view_type)):
            node.children.append(_Node(window, _WINDOW_DEPTH, node, window_row))
        return node
