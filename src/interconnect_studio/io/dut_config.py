"""DUT configuration files: one JSON document per configuration.

Layout (``version`` 1)::

    {
      "format": "interconnect-studio-dut-config",
      "version": 1,
      "name": "Through 1-2, 3-4",
      "n_ports": 4,
      "port_labels": ["Port 1", "Port 2", "Port 3", "Port 4"],
      "lines": [{"name": "Pair 1", "near": [0, 2], "far": [1, 3]}]
    }

Ports are 0-based as everywhere inside the program; the UI displays them
1-based. ``far`` may be empty.

PLTS stores the same information in ``.dcf``, whose layout is not
published, so this is our own format under our own suffix. A ``.dcf``
written by PLTS cannot be read here and is not claimed to be.
"""

import json
from pathlib import Path
from typing import Any, Final

from interconnect_studio.core import (
    DataFormatError,
    DutConfiguration,
    InputValidationError,
    Line,
    PortGroup,
)

DUT_CONFIG_FORMAT: Final[str] = "interconnect-studio-dut-config"
DUT_CONFIG_VERSION: Final[int] = 1
DUT_CONFIG_SUFFIX: Final[str] = ".dutcfg"


def dut_configuration_to_dict(configuration: DutConfiguration) -> dict[str, Any]:
    """JSON-ready form of a DUT configuration."""

    return {
        "format": DUT_CONFIG_FORMAT,
        "version": DUT_CONFIG_VERSION,
        "name": configuration.name,
        "n_ports": configuration.n_ports,
        "port_labels": list(configuration.port_labels),
        "lines": [
            {"name": line.name, "near": list(line.near), "far": list(line.far)}
            for line in configuration.port_group.lines
        ],
    }


def dut_configuration_from_dict(document: Any) -> DutConfiguration:
    """Rebuild a DUT configuration from its JSON form.

    Every domain rule is enforced by ``DutConfiguration`` itself, so a file
    that parses cannot produce an invalid configuration.
    """

    if not isinstance(document, dict):
        raise DataFormatError("A DUT configuration file must contain a JSON object.")
    if document.get("format") != DUT_CONFIG_FORMAT:
        raise DataFormatError(
            f"Not a DUT configuration file: format is {document.get('format')!r}."
        )
    version = document.get("version")
    if version != DUT_CONFIG_VERSION:
        raise DataFormatError(
            f"Unsupported DUT configuration version {version!r}; expected "
            f"{DUT_CONFIG_VERSION}."
        )

    try:
        lines = tuple(
            Line(
                name=str(line["name"]),
                near=tuple(int(port) for port in line["near"]),
                far=tuple(int(port) for port in line.get("far", ())),
            )
            for line in document["lines"]
        )
        configuration = DutConfiguration(
            name=str(document["name"]),
            n_ports=int(document["n_ports"]),
            port_group=PortGroup(lines=lines),
            port_labels=tuple(str(label) for label in document["port_labels"]),
        )
    # InputValidationError subclasses ValueError, so it has to be caught
    # first or a well-formed file describing an impossible DUT would be
    # reported as malformed JSON.
    except InputValidationError as exc:
        raise DataFormatError(f"Invalid DUT configuration: {exc}") from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise DataFormatError(f"Malformed DUT configuration file: {exc}") from exc

    return configuration


def write_dut_configuration(configuration: DutConfiguration, path: str | Path) -> None:
    """Write a DUT configuration as JSON."""

    file_path = Path(path)
    try:
        file_path.write_text(
            json.dumps(dut_configuration_to_dict(configuration), indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise DataFormatError(f"Unable to write DUT configuration: {file_path}") from exc


def read_dut_configuration(path: str | Path) -> DutConfiguration:
    """Read a DUT configuration written by ``write_dut_configuration``."""

    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DataFormatError(f"Unable to read DUT configuration: {file_path}") from exc
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DataFormatError(f"{file_path.name} is not valid JSON: {exc}") from exc
    return dut_configuration_from_dict(document)
