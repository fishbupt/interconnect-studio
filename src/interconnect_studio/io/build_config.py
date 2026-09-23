"""Build configuration file of PLTS "Build with a Config File".

The file is a CSV table (PLTS help, *Importing Data*):

.. code-block:: text

    folder,C:\\Users\\me\\s4pFiles
    s4p_file_1,thru.s4p,[1 2 3 4],[1 2 3 4]
    s4p_file_2,next.s4p,[1 2 3 4],[5 6 7 8]

The first row gives the folder holding the files, absolute or relative to
the configuration file. Each further row gives a file index (a free label),
the file name, the file ports to take and, in the same order, the DUT ports
they become. Port numbers are 1-based as in the file.
"""

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from interconnect_studio.core import DataFormatError
from interconnect_studio.io.touchstone import read_text_file

_PORT_LIST: Final[re.Pattern[str]] = re.compile(r"^\[\s*(\d+(?:[\s,;]+\d+)*)\s*\]$")


@dataclass(frozen=True, slots=True)
class BuildConfigEntry:
    """One source file of a build: which of its ports land on which DUT ports.

    Ports are 1-based, as written in the file.
    """

    label: str
    path: Path
    source_ports: tuple[int, ...]
    destination_ports: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class BuildConfig:
    """Parsed build configuration."""

    folder: Path
    entries: tuple[BuildConfigEntry, ...]

    @property
    def n_ports(self) -> int:
        """DUT port count: the highest destination port."""

        return max(port for entry in self.entries for port in entry.destination_ports)


def read_build_config(path: str | Path) -> BuildConfig:
    """Read a PLTS build configuration CSV."""

    config_path = Path(path)
    rows = [
        [cell.strip() for cell in row]
        for row in csv.reader(read_text_file(config_path, "Build config").splitlines())
        if any(cell.strip() for cell in row)
    ]
    if not rows or rows[0][0].lower() != "folder" or len(rows[0]) < 2 or not rows[0][1]:
        raise DataFormatError("The first row of a build config must be 'folder,<path>'.")
    folder = Path(rows[0][1])
    if not folder.is_absolute():
        folder = config_path.parent / folder

    entries = []
    for row_number, row in enumerate(rows[1:], start=2):
        cells = [cell for cell in row if cell]
        if len(cells) != 4:
            raise DataFormatError(
                f"Row {row_number} needs index, file name, source ports and destination ports."
            )
        source = _ports(cells[2], row_number)
        destination = _ports(cells[3], row_number)
        if len(source) != len(destination):
            raise DataFormatError(
                f"Row {row_number} maps {len(source)} source ports to {len(destination)} "
                "destination ports."
            )
        if len(set(destination)) != len(destination):
            raise DataFormatError(f"Row {row_number} repeats a destination port.")
        entries.append(BuildConfigEntry(cells[0], folder / cells[1], source, destination))
    if not entries:
        raise DataFormatError("Build config lists no files.")
    return BuildConfig(folder=folder, entries=tuple(entries))


def _ports(text: str, row_number: int) -> tuple[int, ...]:
    match = _PORT_LIST.match(text)
    if match is None:
        raise DataFormatError(f"Row {row_number}: expected a port list like [1 2 3 4], got {text}.")
    ports = tuple(int(value) for value in re.split(r"[\s,;]+", match.group(1)))
    if any(port < 1 for port in ports):
        raise DataFormatError(f"Row {row_number}: port numbers start at 1.")
    return ports
