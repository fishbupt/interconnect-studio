"""Icons drawn in code, so the application ships no image assets.

The data browser uses Windows Explorer style icons: amber folders that open
when their node is expanded, and a page for each open window. Categories get
a magnifier badge on the folder, as in the PLTS Data Browser, so the top level
is told apart from the view types below it. Icons keep the same colours in
both themes, as Explorer's folders do.
"""

from collections.abc import Callable
from enum import Enum
from functools import cache
from typing import Final

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

# Icons are designed on a 16-unit grid and rendered at these pixel sizes.
_DESIGN_UNITS: Final[float] = 16.0
_SIZES: Final[tuple[int, ...]] = (16, 20, 24, 32)

_FOLDER_EDGE: Final[str] = "#b8860b"
_FOLDER_BACK: Final[str] = "#e3b341"
_FOLDER_BODY: Final[str] = "#f5c542"
_FOLDER_FRONT: Final[str] = "#fad766"
_PAPER: Final[str] = "#ffffff"
_PAPER_EDGE: Final[str] = "#8a8f98"
_PAPER_LINE: Final[str] = "#4a7fc1"
_BADGE: Final[str] = "#2f6fb0"

_Painter = Callable[[QPainter], None]


class FolderKind(Enum):
    """Folder variants in the data browser."""

    CATEGORY = "category"
    VIEW_TYPE = "view_type"


def folder_icon(kind: FolderKind, *, is_open: bool) -> QIcon:
    """Folder icon for a data browser node, open or closed."""

    return _folder_icon(kind, is_open)


def document_icon() -> QIcon:
    """Page icon for an open window in the data browser."""

    return _document_icon()


@cache
def _folder_icon(kind: FolderKind, is_open: bool) -> QIcon:
    def paint(painter: QPainter) -> None:
        if is_open:
            _paint_open_folder(painter)
        else:
            _paint_closed_folder(painter)
        if kind is FolderKind.CATEGORY:
            _paint_magnifier(painter)

    return _render(paint)


@cache
def _document_icon() -> QIcon:
    return _render(_paint_document)


def _render(paint: _Painter) -> QIcon:
    icon = QIcon()
    for size in _SIZES:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(size / _DESIGN_UNITS, size / _DESIGN_UNITS)
        paint(painter)
        painter.end()
        icon.addPixmap(pixmap)
    return icon


def _pen(color: str, width: float = 0.8) -> QPen:
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _polygon(*points: tuple[float, float]) -> QPolygonF:
    return QPolygonF([QPointF(x, y) for x, y in points])


def _paint_tab(painter: QPainter) -> None:
    painter.setPen(_pen(_FOLDER_EDGE))
    painter.setBrush(QColor(_FOLDER_BACK))
    painter.drawPolygon(
        _polygon((1.5, 3.0), (6.0, 3.0), (7.5, 4.5), (14.5, 4.5), (14.5, 7.0), (1.5, 7.0))
    )


def _paint_closed_folder(painter: QPainter) -> None:
    _paint_tab(painter)
    body = QPainterPath()
    body.addRoundedRect(QRectF(1.5, 5.5, 13.0, 8.5), 1.0, 1.0)
    painter.setPen(_pen(_FOLDER_EDGE))
    painter.setBrush(QColor(_FOLDER_BODY))
    painter.drawPath(body)


def _paint_open_folder(painter: QPainter) -> None:
    _paint_tab(painter)
    painter.setPen(_pen(_FOLDER_EDGE))
    painter.setBrush(QColor(_FOLDER_BACK))
    painter.drawRect(QRectF(1.5, 5.5, 12.0, 8.5))

    painter.setPen(_pen(_PAPER_EDGE, 0.6))
    painter.setBrush(QColor(_PAPER))
    painter.drawRect(QRectF(3.5, 4.0, 9.0, 6.0))

    painter.setPen(_pen(_FOLDER_EDGE))
    painter.setBrush(QColor(_FOLDER_FRONT))
    painter.drawPolygon(_polygon((1.5, 14.0), (4.0, 8.0), (15.5, 8.0), (13.0, 14.0)))


def _paint_magnifier(painter: QPainter) -> None:
    painter.setBrush(QColor(255, 255, 255, 200))
    painter.setPen(_pen(_BADGE, 1.3))
    painter.drawEllipse(QPointF(10.5, 9.5), 2.6, 2.6)
    handle = _pen(_BADGE, 1.8)
    handle.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(handle)
    painter.drawLine(QPointF(12.4, 11.4), QPointF(14.6, 13.6))


def _paint_document(painter: QPainter) -> None:
    painter.setPen(_pen(_PAPER_EDGE))
    painter.setBrush(QColor(_PAPER))
    painter.drawPolygon(_polygon((3.0, 1.5), (9.5, 1.5), (13.0, 5.0), (13.0, 14.5), (3.0, 14.5)))

    painter.setBrush(QColor("#e6e8eb"))
    painter.drawPolygon(_polygon((9.5, 1.5), (9.5, 5.0), (13.0, 5.0)))

    painter.setPen(_pen(_PAPER_LINE, 0.9))
    for y in (7.5, 9.5, 11.5):
        painter.drawLine(QPointF(5.0, y), QPointF(11.0, y))

