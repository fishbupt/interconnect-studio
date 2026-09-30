"""Explicit, non-mutating frequency-domain export workflow."""

import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from interconnect_studio.algorithms.network import remap_ports, renormalize, subset_frequency_range
from interconnect_studio.core import InputValidationError, Network
from interconnect_studio.io.atomic import atomic_destination
from interconnect_studio.io.network_writers import (
    write_citifile,
    write_text_network,
    write_touchstone2,
)
from interconnect_studio.io.touchstone import (
    TouchstoneFormat,
    TouchstoneFrequencyUnit,
    write_touchstone,
)
from interconnect_studio.services.import_service import FrequencyRange

logger = logging.getLogger(__name__)


class ExportFileType(StrEnum):
    """Frequency-domain output formats."""

    TOUCHSTONE = "Touchstone 1.x"
    TOUCHSTONE2 = "Touchstone 2.0"
    CITIFILE = "CITIfile"
    CSV = "Text (comma delimited)"
    TAB = "Text (tab delimited)"


@dataclass(frozen=True, slots=True)
class ExportOptions:
    """Output choices; port_order is new-port -> old-port, 0-based.

    frequency_range is in Hz and keeps existing measured points. References
    change only when renormalize_to_50 is explicitly requested for CITIfile.
    """

    file_type: ExportFileType = ExportFileType.TOUCHSTONE
    data_format: TouchstoneFormat = "ri"
    frequency_unit: TouchstoneFrequencyUnit = "hz"
    frequency_range: FrequencyRange | None = None
    port_order: tuple[int, ...] | None = None
    renormalize_to_50: bool = False


class ExportService:
    """Prepare a copy and atomically write a complete S-parameter matrix."""

    @staticmethod
    def destination(path: str | Path, n_ports: int, file_type: ExportFileType) -> Path:
        """Return the actual output path, with the selected format's suffix."""

        suffix = {
            ExportFileType.TOUCHSTONE: f".s{n_ports}p",
            ExportFileType.TOUCHSTONE2: ".ts",
            ExportFileType.CITIFILE: ".cti",
            ExportFileType.CSV: ".csv",
            ExportFileType.TAB: ".txt",
        }[file_type]
        return Path(path).with_suffix(suffix)

    def prepare(self, network: Network, options: ExportOptions) -> Network:
        """Apply range, permutation and explicitly requested reference conversion."""

        prepared = network
        if options.frequency_range is not None:
            selected = options.frequency_range
            prepared = subset_frequency_range(prepared, selected.start_hz, selected.stop_hz)
        if options.port_order is not None:
            prepared = remap_ports(prepared, options.port_order)
        if options.renormalize_to_50:
            if options.file_type is not ExportFileType.CITIFILE:
                raise InputValidationError("The 50-ohm conversion is only for CITIfile export.")
            prepared = renormalize(prepared, 50.0)
        return prepared

    def export(self, network: Network, path: str | Path, options: ExportOptions) -> Path:
        """Export without modifying the source; return the actual written path."""

        prepared = self.prepare(network, options)
        target = self.destination(path, prepared.n_ports, options.file_type)
        if options.file_type is ExportFileType.TOUCHSTONE:
            with atomic_destination(target) as temporary:
                write_touchstone(
                    prepared,
                    temporary,
                    data_format=options.data_format,
                    frequency_unit=options.frequency_unit,
                    precision=17,
                )
        elif options.file_type is ExportFileType.TOUCHSTONE2:
            write_touchstone2(
                prepared,
                target,
                data_format=options.data_format,
                frequency_unit=options.frequency_unit,
            )
        elif options.file_type is ExportFileType.CITIFILE:
            write_citifile(prepared, target)
        else:
            write_text_network(
                prepared,
                target,
                "comma" if options.file_type is ExportFileType.CSV else "tab",
                frequency_unit=options.frequency_unit,
            )
        logger.info("Exported %s (%d ports, %d points)", target, prepared.n_ports, prepared.n_freq)
        return target
