"""Template files: one JSON document per saved template.

Layout (``version`` 1)::

    {
      "format": "interconnect-studio-template",
      "version": 1,
      "name": "channel",
      "view_type": "FREQUENCY_DOMAIN_SINGLE_ENDED",
      "n_ports": 4,
      "rows": 1,
      "cols": 2,
      "plots": [
        {"kind": "cartesian", "title": null, "x_label": "Frequency",
         "y_label": "Log Mag",
         "traces": [{"response_port": 1, "source_port": 0, "data_format": "log_mag"}]}
      ]
    }

``view_type`` is the ``ViewType`` member name; ports are 0-based as in
``TraceRecipe``; ``title`` ``null`` means "the data file's name". The
template's name is also the file name, ``<name>.json``.
"""

import json
from pathlib import Path
from typing import Any, Final

from interconnect_studio.core import (
    DataFormatError,
    InputValidationError,
    PlotKind,
    TemplatePlot,
    TraceRecipe,
    ViewTemplate,
    ViewType,
)

TEMPLATE_FORMAT: Final[str] = "interconnect-studio-template"
TEMPLATE_VERSION: Final[int] = 1
TEMPLATE_SUFFIX: Final[str] = ".json"


def template_to_dict(template: ViewTemplate) -> dict[str, Any]:
    """JSON-ready form of a template."""

    return {
        "format": TEMPLATE_FORMAT,
        "version": TEMPLATE_VERSION,
        "name": template.name,
        "view_type": template.view_type.name,
        "n_ports": template.n_ports,
        "rows": template.rows,
        "cols": template.cols,
        "plots": [
            {
                "kind": plot.kind.value,
                "title": plot.title,
                "x_label": plot.x_label,
                "y_label": plot.y_label,
                "traces": [
                    {
                        "response_port": recipe.response_port,
                        "source_port": recipe.source_port,
                        "data_format": recipe.data_format,
                    }
                    for recipe in plot.traces
                ],
            }
            for plot in template.plots
        ],
    }


def template_from_dict(data: object) -> ViewTemplate:
    """Template from its JSON form; raises ``DataFormatError`` if malformed."""

    try:
        if not isinstance(data, dict) or data.get("format") != TEMPLATE_FORMAT:
            raise DataFormatError("Not an Interconnect Studio template.")
        if data.get("version") != TEMPLATE_VERSION:
            raise DataFormatError(f"Unsupported template version: {data.get('version')!r}.")
        plots = tuple(
            TemplatePlot(
                traces=tuple(
                    TraceRecipe(
                        response_port=trace["response_port"],
                        source_port=trace["source_port"],
                        data_format=trace["data_format"],
                    )
                    for trace in plot["traces"]
                ),
                kind=PlotKind(plot["kind"]),
                title=plot["title"],
                x_label=plot["x_label"],
                y_label=plot["y_label"],
            )
            for plot in data["plots"]
        )
        return ViewTemplate(
            name=data["name"],
            view_type=ViewType[data["view_type"]],
            n_ports=data["n_ports"],
            rows=data["rows"],
            cols=data["cols"],
            plots=plots,
        )
    except DataFormatError:
        raise
    except (InputValidationError, KeyError, TypeError, ValueError) as exc:
        raise DataFormatError(f"Malformed template: {exc}") from exc


def write_template(template: ViewTemplate, path: Path) -> None:
    """Write a template file (UTF-8 JSON), replacing any existing one."""

    text = json.dumps(template_to_dict(template), indent=2, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")


def read_template(path: Path) -> ViewTemplate:
    """Read a template file; raises ``DataFormatError`` if it is not one."""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DataFormatError(f"Cannot read template {path.name}: {exc}") from exc
    return template_from_dict(data)
