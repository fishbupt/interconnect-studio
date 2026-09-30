"""Versioned .icproj archives: JSON manifest plus non-pickled NumPy arrays.

Data and rendered traces are embedded, so moving/deleting the original files
cannot break recall. Members are read in memory, never extracted. Saving is
atomic. Future versions are rejected explicitly rather than guessed.
"""

import base64
import binascii
import io
import json
import math
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Final

import numpy as np
from numpy.typing import NDArray

from interconnect_studio.core import (
    DataFile,
    DataFormatError,
    Marker,
    Network,
    PlotKind,
    PlotModel,
    Trace,
    TraceRecipe,
    ViewLayout,
    ViewType,
)
from interconnect_studio.core.project import ProjectFile, ProjectSnapshot, ProjectWindow
from interconnect_studio.io.atomic import atomic_destination
from interconnect_studio.io.dut_config import (
    dut_configuration_from_dict,
    dut_configuration_to_dict,
)

PROJECT_SUFFIX: Final[str] = ".icproj"
PROJECT_FORMAT: Final[str] = "interconnect-studio-project"
PROJECT_VERSION: Final[int] = 2
_MAX_MEMBER: Final[int] = 512 * 1024 * 1024
_MAX_TOTAL: Final[int] = 2 * 1024 * 1024 * 1024


class _ArrayWriter:
    def __init__(self, archive: zipfile.ZipFile) -> None:
        self.archive = archive
        self.count = 0

    def add(self, array: NDArray[Any]) -> str:
        if array.nbytes > _MAX_MEMBER - 1024:
            raise DataFormatError("Project array exceeds the supported member size.")
        name = f"arrays/{self.count}.npy"
        self.count += 1
        buffer = io.BytesIO()
        np.save(buffer, array, allow_pickle=False)
        self.archive.writestr(name, buffer.getvalue())
        return name


def write_project(snapshot: ProjectSnapshot, path: str | Path) -> None:
    """Atomically write a complete workspace, including complex z0 and trace data."""

    destination = Path(path)
    if destination.suffix.lower() != PROJECT_SUFFIX:
        raise DataFormatError(f"Project files must use {PROJECT_SUFFIX}.")
    with (
        atomic_destination(destination) as temporary,
        zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive,
    ):
        arrays = _ArrayWriter(archive)
        document = {
            "format": PROJECT_FORMAT,
            "version": PROJECT_VERSION,
            "geometry": base64.b64encode(snapshot.geometry).decode("ascii"),
            "dock_state": base64.b64encode(snapshot.dock_state).decode("ascii"),
            "files": [_file_document(item, arrays) for item in snapshot.files],
            "windows": [_window_document(window, arrays) for window in snapshot.windows],
        }
        manifest = json.dumps(document, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(manifest) > 16 * 1024 * 1024:
            raise DataFormatError("Project manifest is too large.")
        archive.writestr("manifest.json", manifest)
        entries = archive.infolist()
        if len(entries) > 100_000 or sum(entry.file_size for entry in entries) > _MAX_TOTAL:
            raise DataFormatError("Project exceeds the supported archive size.")


def _file_document(item: ProjectFile, arrays: _ArrayWriter) -> dict[str, Any]:
    data = item.data_file
    network = data.network
    return {
        "id": data.id,
        "name": data.name,
        "source_path": str(data.source_path) if data.source_path is not None else None,
        "imported_at": data.imported_at.isoformat() if data.imported_at is not None else None,
        "frequencies": arrays.add(network.frequencies_hz),
        "s": arrays.add(network.s),
        "z0": [network.z0.real, network.z0.imag],
        "port_names": list(network.port_names) if network.port_names is not None else None,
        "dut_configuration": (
            dut_configuration_to_dict(item.dut_configuration)
            if item.dut_configuration is not None
            else None
        ),
    }


def _window_document(window: ProjectWindow, arrays: _ArrayWriter) -> dict[str, Any]:
    return {
        "number": window.number,
        "file_id": window.file_id,
        "view_type": window.view_type.name,
        "template": window.template,
        "rows": window.layout.rows,
        "cols": window.layout.cols,
        "plot_ranges": list(window.plot_ranges),
        "plot_autorange": list(window.plot_autorange),
        "plots": [
            {
                "kind": plot.kind.value,
                "title": plot.title,
                "x_label": plot.x_label,
                "y_label": plot.y_label,
                "traces": [_trace_document(trace, window.file_id, arrays) for trace in plot.traces],
                "markers": [
                    {
                        "number": m.number,
                        "trace_index": m.trace_index,
                        "x": m.x,
                        "reference_id": m.reference_id,
                    }
                    for m in plot.markers
                ],
            }
            for plot in window.layout.plots
        ],
    }


def _trace_document(trace: Trace, file_id: str, arrays: _ArrayWriter) -> dict[str, Any]:
    recipe = trace.recipe
    return {
        "name": trace.name,
        "x": arrays.add(trace.x),
        "y": arrays.add(trace.y),
        "x_unit": trace.x_unit,
        "y_unit": trace.y_unit,
        "source_id": trace.source_id or file_id,
        "recipe": None
        if recipe is None
        else {
            "response_port": recipe.response_port,
            "source_port": recipe.source_port,
            "data_format": recipe.data_format,
        },
    }


def read_project(path: str | Path) -> ProjectSnapshot:
    """Validate an entire archive before returning any state to the application."""

    try:
        with zipfile.ZipFile(Path(path)) as archive:
            entries = archive.infolist()
            if len(entries) > 100_000 or len({entry.filename for entry in entries}) != len(entries):
                raise DataFormatError("Project has duplicate or too many archive members.")
            if (
                any(entry.file_size > _MAX_MEMBER for entry in entries)
                or sum(entry.file_size for entry in entries) > _MAX_TOTAL
            ):
                raise DataFormatError("Project exceeds the supported archive size.")
            if archive.getinfo("manifest.json").file_size > 16 * 1024 * 1024:
                raise DataFormatError("Project manifest is too large.")
            document = json.loads(archive.read("manifest.json"))
            if not isinstance(document, dict) or document.get("format") != PROJECT_FORMAT:
                raise DataFormatError("Not an Interconnect Studio project.")
            if type(document.get("version")) is not int or document["version"] not in (1, 2):
                raise DataFormatError(f"Unsupported project version: {document.get('version')!r}.")
            files = tuple(_read_file(item, archive) for item in document["files"])
            windows = tuple(_read_window(item, archive) for item in document["windows"])
            return ProjectSnapshot(
                files=files,
                windows=windows,
                geometry=base64.b64decode(document["geometry"], validate=True),
                dock_state=base64.b64decode(document["dock_state"], validate=True),
            )
    except DataFormatError:
        raise
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        IndexError,
        EOFError,
        zipfile.BadZipFile,
        RuntimeError,
        binascii.Error,
    ) as exc:
        raise DataFormatError(f"Cannot read project {Path(path).name}: {exc}") from exc


def _array(archive: zipfile.ZipFile, name: str) -> NDArray[Any]:
    if not isinstance(name, str) or not name.startswith("arrays/") or not name.endswith(".npy"):
        raise DataFormatError("Invalid project array member.")
    buffer = io.BytesIO(archive.read(name))
    version = np.lib.format.read_magic(buffer)
    if version == (1, 0):
        shape, _fortran, dtype = np.lib.format.read_array_header_1_0(buffer)
    elif version == (2, 0):
        shape, _fortran, dtype = np.lib.format.read_array_header_2_0(buffer)
    else:
        raise DataFormatError("Unsupported project array header.")
    size = math.prod(shape) * dtype.itemsize
    if dtype not in (np.dtype("float64"), np.dtype("complex128")) or size > _MAX_MEMBER:
        raise DataFormatError("Invalid project array type or size.")
    if size != len(buffer.getbuffer()) - buffer.tell():
        raise DataFormatError("Project array payload does not match its shape.")
    buffer.seek(0)
    result: NDArray[Any] = np.load(buffer, allow_pickle=False)
    return result


def _read_file(item: dict[str, Any], archive: zipfile.ZipFile) -> ProjectFile:
    configuration = (
        dut_configuration_from_dict(item["dut_configuration"])
        if item["dut_configuration"] is not None
        else None
    )
    reference = item["z0"]
    if not isinstance(reference, list) or len(reference) != 2:
        raise DataFormatError("Invalid project reference impedance.")
    network = Network(
        _array(archive, item["frequencies"]),
        _array(archive, item["s"]),
        z0=complex(*reference),
        port_names=tuple(item["port_names"]) if item["port_names"] is not None else None,
    )
    data = DataFile(
        id=item["id"],
        name=item["name"],
        network=network,
        source_path=Path(item["source_path"]) if item["source_path"] is not None else None,
        imported_at=datetime.fromisoformat(item["imported_at"]) if item["imported_at"] else None,
        port_group=configuration.port_group if configuration is not None else None,
    )
    return ProjectFile(data, configuration)


def _read_window(item: dict[str, Any], archive: zipfile.ZipFile) -> ProjectWindow:
    plots = tuple(
        PlotModel(
            kind=PlotKind(plot["kind"]),
            title=plot["title"],
            x_label=plot["x_label"],
            y_label=plot["y_label"],
            traces=tuple(_read_trace(trace, archive) for trace in plot["traces"]),
            markers=tuple(Marker(**marker) for marker in plot.get("markers", [])),
        )
        for plot in item["plots"]
    )
    return ProjectWindow(
        number=item["number"],
        file_id=item["file_id"],
        view_type=ViewType[item["view_type"]],
        layout=ViewLayout(rows=item["rows"], cols=item["cols"], plots=plots),
        template=item["template"],
        plot_ranges=tuple(
            tuple(bounds) if bounds is not None else None for bounds in item["plot_ranges"]
        ),
        plot_autorange=tuple(tuple(axes) for axes in item["plot_autorange"]),
    )


def _read_trace(item: dict[str, Any], archive: zipfile.ZipFile) -> Trace:
    recipe = item["recipe"]
    return Trace(
        name=item["name"],
        x=_array(archive, item["x"]),
        y=_array(archive, item["y"]),
        x_unit=item["x_unit"],
        y_unit=item["y_unit"],
        source_id=item["source_id"],
        recipe=TraceRecipe(**recipe) if recipe is not None else None,
    )
