"""Saved templates: store them, list them, and lay a data file out with one."""

import logging
from pathlib import Path

from interconnect_studio.algorithms.network import create_s_parameter_trace
from interconnect_studio.core import (
    DataFormatError,
    InputValidationError,
    Network,
    PlotModel,
    ViewLayout,
    ViewTemplate,
)
from interconnect_studio.io import TEMPLATE_SUFFIX, read_template, write_template

logger = logging.getLogger(__name__)


class TemplateService:
    """Templates kept as ``<name>.json`` files in one folder.

    The folder need not exist until the first template is saved.
    """

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    @property
    def directory(self) -> Path:
        """Folder the templates are kept in."""

        return self._directory

    def path_of(self, name: str) -> Path:
        """File a template of this name is kept in."""

        return self._directory / f"{name}{TEMPLATE_SUFFIX}"

    def list_templates(self) -> tuple[ViewTemplate, ...]:
        """Every readable template, sorted by name; unreadable files are skipped."""

        if not self._directory.is_dir():
            return ()
        templates = []
        for path in sorted(self._directory.glob(f"*{TEMPLATE_SUFFIX}")):
            try:
                templates.append(read_template(path))
            except DataFormatError as exc:
                logger.warning("Skipped template %s: %s", path, exc)
        return tuple(sorted(templates, key=lambda template: template.name.casefold()))

    def exists(self, name: str) -> bool:
        """Whether a template of this name is saved."""

        return self.path_of(name.strip()).exists()

    def save(self, template: ViewTemplate, overwrite: bool = False) -> Path:
        """Save a template; refuses to replace one unless ``overwrite``."""

        path = self.path_of(template.name)
        if path.exists() and not overwrite:
            raise InputValidationError(f"Template {template.name} already exists.")
        self._directory.mkdir(parents=True, exist_ok=True)
        write_template(template, path)
        logger.info("Saved template %s to %s", template.name, path)
        return path

    def apply(self, template: ViewTemplate, network: Network, file_name: str) -> ViewLayout:
        """Lay a network out as the template does, recomputing every trace.

        Raises ``InputValidationError`` if the network lacks a port a trace
        needs.
        """

        if network.n_ports < template.required_ports:
            raise InputValidationError(
                f"Template {template.name} needs {template.required_ports} ports; "
                f"{file_name} has {network.n_ports}."
            )
        plots = tuple(
            PlotModel(
                traces=tuple(
                    create_s_parameter_trace(
                        network, recipe.response_port, recipe.source_port, recipe.data_format
                    )
                    for recipe in plot.traces
                ),
                kind=plot.kind,
                title=plot.title_for(file_name),
                x_label=plot.x_label,
                y_label=plot.y_label,
            )
            for plot in template.plots
        )
        return ViewLayout(rows=template.rows, cols=template.cols, plots=plots)
