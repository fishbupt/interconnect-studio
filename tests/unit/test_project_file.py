import io
import json
import zipfile
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from interconnect_studio.algorithms.mixed_mode import DEFAULT_FOUR_PORT_TOPOLOGY
from interconnect_studio.core import (
    DataFile,
    DataFormatError,
    Network,
    PlotModel,
    ProjectFile,
    ProjectSnapshot,
    ProjectWindow,
    Trace,
    TraceRecipe,
    ViewLayout,
    ViewType,
)
from interconnect_studio.io import read_project, write_project


def sample() -> ProjectSnapshot:
    network = Network(
        [1e6, 2e6], np.zeros((2, 4, 4)), 75 + 2j, port_names=("TX+", "RX+", "TX-", "RX-")
    )
    configuration = DEFAULT_FOUR_PORT_TOPOLOGY.dut_configuration()
    data = DataFile("file-7", "芯片.s4p", network, source_path=Path("missing.s4p"))
    trace = Trace(
        "SDD21",
        [1e6, 2e6],
        [-np.inf, -5.0],
        x_unit="Hz",
        y_unit="dB",
        recipe=TraceRecipe(1, 0, "log_mag"),
    )
    layout = ViewLayout(2, 2).with_plot(0, 1, PlotModel(traces=(trace,), title="差分损耗"))
    window = ProjectWindow(
        3,
        data.id,
        ViewType.FREQUENCY_DOMAIN_BALANCED,
        layout,
        template="saved layout",
        plot_ranges=((0.0, 3e6, -20.0, 0.0),) * 4,
    )
    return ProjectSnapshot((ProjectFile(data, configuration),), (window,), b"geometry", b"docks")


def test_project_roundtrip_embeds_data_traces_and_configuration(tmp_path: Path) -> None:
    snapshot = sample()
    path = tmp_path / "channel.icproj"
    write_project(snapshot, path)
    result = read_project(path)
    actual = result.files[0]
    np.testing.assert_array_equal(actual.data_file.network.s, snapshot.files[0].data_file.network.s)
    assert actual.data_file.network.z0 == 75 + 2j
    assert actual.data_file.network.port_names == snapshot.files[0].data_file.network.port_names
    assert actual.dut_configuration == snapshot.files[0].dut_configuration
    assert actual.data_file.source_path == Path("missing.s4p")
    saved_window = result.windows[0]
    assert saved_window.number == 3
    assert saved_window.layout.rows == 2
    assert saved_window.template == "saved layout"
    trace = saved_window.layout.plots[1].traces[0]
    np.testing.assert_array_equal(trace.y, [-np.inf, -5.0])
    assert trace.recipe == TraceRecipe(1, 0, "log_mag")
    assert trace.source_id == "file-7"
    assert saved_window.plot_ranges == snapshot.windows[0].plot_ranges
    assert result.geometry == b"geometry" and result.dock_state == b"docks"


def rewrite_manifest(path: Path, change: object) -> None:
    with zipfile.ZipFile(path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    document = json.loads(entries["manifest.json"])
    change(document)
    entries["manifest.json"] = json.dumps(document).encode()
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)


@pytest.mark.parametrize("field,value", [("format", "other"), ("version", 99), ("version", True)])
def test_project_rejects_unknown_format_or_version(
    tmp_path: Path, field: str, value: object
) -> None:
    path = tmp_path / "bad.icproj"
    write_project(sample(), path)
    rewrite_manifest(path, lambda data: data.update({field: value}))
    with pytest.raises(DataFormatError):
        read_project(path)


def test_project_rejects_dangling_window_reference(tmp_path: Path) -> None:
    path = tmp_path / "bad.icproj"
    write_project(sample(), path)
    rewrite_manifest(path, lambda data: data["windows"][0].update({"file_id": "missing"}))
    with pytest.raises(DataFormatError, match="missing data file"):
        read_project(path)


def test_project_rejects_object_arrays_without_pickle(tmp_path: Path) -> None:
    path = tmp_path / "bad.icproj"
    write_project(sample(), path)
    with zipfile.ZipFile(path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    buffer = io.BytesIO()
    np.save(buffer, np.asarray([{"bad": 1}], dtype=object))
    entries["arrays/0.npy"] = buffer.getvalue()
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    with pytest.raises(DataFormatError, match="array type"):
        read_project(path)


def test_failed_project_replace_preserves_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "channel.icproj"
    write_project(sample(), path)
    before = path.read_bytes()

    def fail(*_args: object) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr("interconnect_studio.io.atomic.os.replace", fail)
    with pytest.raises(OSError):
        write_project(replace(sample(), geometry=b"new"), path)
    assert path.read_bytes() == before
    assert len(list(tmp_path.iterdir())) == 1


def test_empty_project_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "empty.icproj"
    write_project(ProjectSnapshot(), path)
    assert read_project(path) == ProjectSnapshot()
