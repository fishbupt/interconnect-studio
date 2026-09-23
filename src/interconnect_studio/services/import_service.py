"""Import application service: PLTS "File > Import" workflows.

- Import a Single File: read one frequency-domain file, optionally narrowed
  to a frequency subset.
- Import Multiple Files (Build a File): assemble one network from parameters
  or ports of several single-ended files.
- Build with a Config File: the same, driven by a PLTS build config CSV.

Time-domain import, differential / single-ended-to-differential mapping and
resampling (changing points or step) are not supported yet; see
``docs/PRODUCT.md`` FR-001.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from interconnect_studio.algorithms.network import (
    ParameterAssignment,
    build_network,
    port_assignments,
    subset_frequency_range,
)
from interconnect_studio.core import (
    DataFormatError,
    InputValidationError,
    Network,
    PortGroup,
)
from interconnect_studio.io import (
    ImportFileType,
    guess_file_type,
    read_build_config,
    read_network,
    write_touchstone,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FrequencyRange:
    """Inclusive frequency range in Hz for "Limit Data Range: Subset"."""

    start_hz: float
    stop_hz: float


@dataclass(frozen=True, slots=True)
class ImportedNetwork:
    """Result of an import: the network, its display name and its source file.

    ``source_path`` is ``None`` for networks built from several files.
    ``port_group`` records the DUT configuration chosen at import; it is
    ``None`` when the data is treated as plain single-ended ports.
    """

    name: str
    network: Network
    source_path: Path | None = None
    port_group: PortGroup | None = None


@dataclass(frozen=True, slots=True)
class BuildSource:
    """One file of a multiple-file build."""

    path: Path
    network: Network


class ImportService:
    """Reads, narrows and builds networks for the import dialogs."""

    def read(self, path: str | Path, file_type: ImportFileType) -> Network:
        """Read a file without narrowing, e.g. to show its range in a dialog."""

        return read_network(path, file_type)

    def import_single(
        self,
        path: str | Path,
        file_type: ImportFileType,
        frequency_range: FrequencyRange | None = None,
    ) -> ImportedNetwork:
        """Import one file; ``frequency_range`` None means "All"."""

        file_path = Path(path)
        network = self._narrow(read_network(file_path, file_type), frequency_range)
        logger.info("Imported %s (%d ports, %d points)", file_path, network.n_ports, network.n_freq)
        return ImportedNetwork(name=file_path.name, network=network, source_path=file_path)

    def build(
        self,
        sources: Sequence[BuildSource],
        n_ports: int,
        assignments: Sequence[ParameterAssignment],
        name: str,
        frequency_range: FrequencyRange | None = None,
    ) -> ImportedNetwork:
        """Assemble a network from several files' parameters."""

        network = build_network([source.network for source in sources], n_ports, assignments)
        network = self._narrow(network, frequency_range)
        logger.info("Built %s from %d files (%d ports)", name, len(sources), n_ports)
        return ImportedNetwork(name=name, network=network)

    def build_from_config(
        self,
        config_path: str | Path,
        frequency_range: FrequencyRange | None = None,
    ) -> ImportedNetwork:
        """Build a network as described by a PLTS build config CSV.

        The type of each listed file is taken from its name (``.sNp``, ``.ts``,
        ``.cti`` / ``.cit``, ``.csv``).
        """

        path = Path(config_path)
        config = read_build_config(path)
        sources: list[BuildSource] = []
        assignments: list[ParameterAssignment] = []
        for index, entry in enumerate(config.entries):
            file_type = guess_file_type(entry.path)
            if file_type is None:
                raise DataFormatError(
                    f"Cannot tell the file type of {entry.path.name}; use .sNp, .ts, .cti "
                    "or .csv files in a build config."
                )
            network = read_network(entry.path, file_type)
            if max(entry.source_ports) > network.n_ports:
                raise InputValidationError(
                    f"{entry.path.name} has {network.n_ports} ports but the config uses port "
                    f"{max(entry.source_ports)}."
                )
            sources.append(BuildSource(path=entry.path, network=network))
            assignments.extend(
                port_assignments(
                    index,
                    [port - 1 for port in entry.source_ports],
                    [port - 1 for port in entry.destination_ports],
                )
            )
        return self.build(
            sources,
            config.n_ports,
            assignments,
            name=f"{path.stem}.s{config.n_ports}p",
            frequency_range=frequency_range,
        )

    def export_touchstone(self, network: Network, path: str | Path) -> Path:
        """Write a network as Touchstone 1.x, fixing the suffix to ``.sNp``."""

        target = Path(path).with_suffix(f".s{network.n_ports}p")
        write_touchstone(network, target)
        logger.info("Exported %s", target)
        return target

    @staticmethod
    def _narrow(network: Network, frequency_range: FrequencyRange | None) -> Network:
        if frequency_range is None:
            return network
        return subset_frequency_range(network, frequency_range.start_hz, frequency_range.stop_hz)
