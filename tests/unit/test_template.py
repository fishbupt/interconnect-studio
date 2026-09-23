import json
from pathlib import Path

import numpy as np
import pytest

from interconnect_studio.algorithms.network import create_s_parameter_trace
from interconnect_studio.core import (
    DataFormatError,
    InputValidationError,
    Network,
    PlotKind,
    PlotModel,
    TemplatePlot,
    Trace,
    TraceRecipe,
    ViewLayout,
    ViewTemplate,
    ViewType,
)
from interconnect_studio.io import read_template, write_template
from interconnect_studio.services import TemplateService

FD_SE = ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED


def network(n_ports: int, scale: float = 1.0) -> Network:
    frequencies = np.array([1.0e9, 2.0e9, 3.0e9])
    s = np.full((3, n_ports, n_ports), 0.1 * scale, dtype=np.complex128)
    return Network(frequencies_hz=frequencies, s=s, z0=50.0)


def layout_of(net: Network, file_name: str) -> ViewLayout:
    s21 = create_s_parameter_trace(net, 1, 0, "log_mag")
    s11 = create_s_parameter_trace(net, 0, 0, "log_mag")
    first = PlotModel(traces=(s11, s21), title=file_name, x_label="Frequency", y_label="Log Mag")
    second = PlotModel(
        traces=(create_s_parameter_trace(net, 0, 0, "smith"),),
        kind=PlotKind.SMITH,
        title="Match",
    )
    return ViewLayout(rows=1, cols=3, plots=(first, second, PlotModel()))


def saved_template(name: str = "channel") -> ViewTemplate:
    net = network(2)
    return ViewTemplate.from_layout(name, FD_SE, 2, layout_of(net, "dut.s2p"), "dut.s2p")


def test_traces_record_how_they_were_computed() -> None:
    trace = create_s_parameter_trace(network(2), 1, 0, "phase")

    assert trace.recipe == TraceRecipe(1, 0, "phase")
    assert Trace("t", [1.0], [0.0]).recipe is None


def test_from_layout_keeps_grid_recipes_and_file_named_titles() -> None:
    template = saved_template()

    assert (template.rows, template.cols, template.n_ports) == (1, 3, 2)
    assert template.label == "channel (2p)"
    assert template.plots[0].traces == (TraceRecipe(0, 0, "log_mag"), TraceRecipe(1, 0, "log_mag"))
    assert template.plots[0].title is None
    assert template.plots[1].title == "Match"
    assert template.plots[1].kind is PlotKind.SMITH
    assert template.plots[2] == TemplatePlot(title="")
    assert template.required_ports == 2


def test_from_layout_rejects_traces_without_recipe() -> None:
    layout = ViewLayout(rows=1, cols=1, plots=(PlotModel(traces=(Trace("t", [1.0], [0.0]),)),))

    with pytest.raises(InputValidationError, match="cannot be saved"):
        ViewTemplate.from_layout("x", FD_SE, 1, layout, "f")


@pytest.mark.parametrize("name", ["", "  ", "a/b", "a:b", ".hidden", 'q"'])
def test_template_names_must_be_usable_file_names(name: str) -> None:
    with pytest.raises(InputValidationError):
        ViewTemplate(name, FD_SE, 1, 1, 1, (TemplatePlot(),))


def test_template_needs_one_plot_per_cell_and_enough_ports() -> None:
    with pytest.raises(InputValidationError, match="needs 2 plots"):
        ViewTemplate("t", FD_SE, 1, 1, 2, (TemplatePlot(),))
    with pytest.raises(InputValidationError, match="use port 2"):
        ViewTemplate("t", FD_SE, 1, 1, 1, (TemplatePlot(traces=(TraceRecipe(1, 0, "phase"),)),))


def test_template_file_round_trip(tmp_path: Path) -> None:
    template = saved_template()
    path = tmp_path / "channel.json"

    write_template(template, path)

    assert read_template(path) == template
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["format"] == "interconnect-studio-template"
    assert data["version"] == 1
    assert data["view_type"] == "FREQUENCY_DOMAIN_SINGLE_ENDED"
    assert data["plots"][0]["title"] is None
    assert data["plots"][0]["traces"][1] == {
        "response_port": 1,
        "source_port": 0,
        "data_format": "log_mag",
    }


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        '{"format": "other"}',
        '{"format": "interconnect-studio-template", "version": 99}',
        '{"format": "interconnect-studio-template", "version": 1, "name": "x"}',
    ],
)
def test_malformed_template_files_are_rejected(tmp_path: Path, content: str) -> None:
    path = tmp_path / "bad.json"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(DataFormatError):
        read_template(path)


def test_service_saves_lists_and_refuses_to_overwrite(tmp_path: Path) -> None:
    service = TemplateService(tmp_path / "templates")
    assert service.list_templates() == ()

    service.save(saved_template("zeta"))
    service.save(saved_template("Alpha"))
    (tmp_path / "templates" / "broken.json").write_text("{", encoding="utf-8")

    assert [t.name for t in service.list_templates()] == ["Alpha", "zeta"]
    assert service.exists("zeta")
    with pytest.raises(InputValidationError, match="already exists"):
        service.save(saved_template("zeta"))
    service.save(saved_template("zeta"), overwrite=True)


def test_apply_recomputes_traces_for_another_file() -> None:
    other = network(4, scale=5.0)

    layout = TemplateService(Path(".")).apply(saved_template(), other, "other.s4p")

    assert (layout.rows, layout.cols) == (1, 3)
    first = layout.plots[0]
    assert first.title == "other.s4p"
    assert [trace.name for trace in first.traces] == ["S11 Log Mag", "S21 Log Mag"]
    expected = create_s_parameter_trace(other, 1, 0, "log_mag")
    np.testing.assert_allclose(first.traces[1].y, expected.y)
    assert layout.plots[1].title == "Match"
    assert layout.plots[1].kind is PlotKind.SMITH
    assert layout.plots[2].traces == ()


def test_apply_needs_the_ports_the_traces_use() -> None:
    with pytest.raises(InputValidationError, match="needs 2 ports; one.s1p has 1"):
        TemplateService(Path(".")).apply(saved_template(), network(1), "one.s1p")
