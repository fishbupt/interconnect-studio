"""Generate the mixed-mode golden cases from a coupled transmission-line model.

The model is a symmetric pair of coupled transmission lines, the canonical
physical shape of a differential interconnect. It is built from circuit
theory (a 4-port open-circuit impedance matrix) so that the reference
mixed-mode response can be written down independently, from the even- and
odd-mode two-port formulas, without going through the mixed-mode transform
under test.

Modal decomposition of a symmetric pair
--------------------------------------
Ports are 0 = line A near, 1 = line A far, 2 = line B near, 3 = line B far.

Under even excitation (both conductors driven alike) each line behaves as a
transmission line of characteristic impedance ``z_even``; under odd
excitation as one of ``z_odd``. Writing the two excitations against the
symmetric 4-port impedance matrix gives

    Z_aa = (z_even coth(theta_even) + z_odd coth(theta_odd)) / 2
    Z_ab = (z_even csch(theta_even) + z_odd csch(theta_odd)) / 2   same line
    Z_ac = (z_even coth(theta_even) - z_odd coth(theta_odd)) / 2   cross, same end
    Z_ad = (z_even csch(theta_even) - z_odd csch(theta_odd)) / 2   cross, other end

Reference mixed-mode response
-----------------------------
The differential mode is the odd mode: its voltage is ``2 * v_odd`` and its
current ``i_odd``, so it is a two-port line of impedance ``2 * z_odd``
referenced to ``2 * z0``. The common mode is the even mode, a line of
``z_even / 2`` referenced to ``z0 / 2``. Both ratios equal the single-ended
ones, so the modal two-port coefficients referenced to ``z0`` are already
the answer:

    Sdd11 = S11(z_odd,  theta_odd,  z0)      Sdd21 = S21(z_odd,  theta_odd,  z0)
    Scc11 = S11(z_even, theta_even, z0)      Scc21 = S21(z_even, theta_even, z0)

and a symmetric pair converts no energy between modes.

Case 002 adds an intra-pair skew: an ideal matched line of delay ``tau`` on
port 3 only, which multiplies row and column 3 by ``a = exp(-j 2 pi f tau)``.
Expanding the mixed-mode combinations under that scaling gives

    Sdd21 = Sodd21  (1 + a) / 2        Scd21 = Sodd21  (1 - a) / 2
    Scc21 = Seven21 (1 + a) / 2        Sdc21 = Seven21 (1 - a) / 2

while the port-1 reflections are untouched.

Run with ``uv run python scripts/generate_golden_mixed_mode.py``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

import numpy as np
from numpy.typing import NDArray

from interconnect_studio.algorithms.mixed_mode import to_mixed_mode, topology_by_id
from interconnect_studio.core import Mode, Network
from interconnect_studio.io.touchstone import read_touchstone, write_touchstone

SPEED_OF_LIGHT_M_S: Final[float] = 299_792_458.0
GOLDEN_ROOT: Final[Path] = Path(__file__).resolve().parent.parent / "golden_data" / "mixed_mode"
TOPOLOGY_ID: Final[str] = "through_1_2_3_4"

D: Final[Mode] = Mode.DIFFERENTIAL
C: Final[Mode] = Mode.COMMON

# Reference key -> (response mode, source mode, response port, source port).
PARAMETERS: Final[dict[str, tuple[Mode, Mode, int, int]]] = {
    "sdd11": (D, D, 0, 0),
    "sdd21": (D, D, 1, 0),
    "scc11": (C, C, 0, 0),
    "scc21": (C, C, 1, 0),
    "scd21": (C, D, 1, 0),
    "sdc21": (D, C, 1, 0),
}


@dataclass(frozen=True, slots=True)
class CoupledPair:
    """A symmetric coupled pair, in SI units except where named otherwise.

    ``alpha_sqrt_f`` and ``alpha_f`` are the conductor and dielectric loss
    coefficients in Np/m when frequency is expressed in GHz; ``loss_odd`` and
    ``loss_even`` scale them per mode (the odd mode crowds current, so it
    loses slightly more).
    """

    length_m: float = 0.1524  # 6 inch
    z_odd_ohm: float = 46.0  # 92 ohm differential, a realistic near-100 board
    z_even_ohm: float = 61.0
    eps_eff_odd: float = 3.20  # microstrip: the odd mode is the faster one
    eps_eff_even: float = 3.55
    alpha_sqrt_f: float = 0.43
    alpha_f: float = 0.136
    loss_odd: float = 1.10
    loss_even: float = 0.95
    z0_ohm: float = 50.0

    def theta(
        self,
        frequencies_hz: NDArray[np.float64],
        *,
        even: bool,
    ) -> NDArray[np.complex128]:
        """Complex electrical length gamma*l of one mode, dimensionless."""

        frequencies_ghz = frequencies_hz / 1.0e9
        eps_eff = self.eps_eff_even if even else self.eps_eff_odd
        loss_scale = self.loss_even if even else self.loss_odd
        alpha_np_m = (
            self.alpha_sqrt_f * np.sqrt(frequencies_ghz) + self.alpha_f * frequencies_ghz
        ) * loss_scale
        beta_rad_m = 2.0 * np.pi * frequencies_hz * np.sqrt(eps_eff) / SPEED_OF_LIGHT_M_S
        return (alpha_np_m + 1j * beta_rad_m).astype(np.complex128) * self.length_m


def line_two_port(
    z_line_ohm: float,
    theta: NDArray[np.complex128],
    z_reference_ohm: float,
) -> tuple[NDArray[np.complex128], NDArray[np.complex128]]:
    """Return (S11, S21) of a uniform transmission line, shape (n_freq,)."""

    sinh, cosh = np.sinh(theta), np.cosh(theta)
    denominator = (
        2.0 * z_line_ohm * z_reference_ohm * cosh
        + (z_line_ohm**2 + z_reference_ohm**2) * sinh
    )
    s11 = (z_line_ohm**2 - z_reference_ohm**2) * sinh / denominator
    s21 = 2.0 * z_line_ohm * z_reference_ohm / denominator
    return s11, s21


def coupled_pair_network(
    pair: CoupledPair,
    frequencies_hz: NDArray[np.float64],
    *,
    skew_s: float = 0.0,
) -> Network:
    """Build the single-ended 4-port from the modal impedance matrix."""

    theta_odd = pair.theta(frequencies_hz, even=False)
    theta_even = pair.theta(frequencies_hz, even=True)

    coth_odd, coth_even = np.cosh(theta_odd) / np.sinh(theta_odd), np.cosh(theta_even) / np.sinh(
        theta_even
    )
    csch_odd, csch_even = 1.0 / np.sinh(theta_odd), 1.0 / np.sinh(theta_even)

    diagonal = (pair.z_even_ohm * coth_even + pair.z_odd_ohm * coth_odd) / 2.0
    same_line = (pair.z_even_ohm * csch_even + pair.z_odd_ohm * csch_odd) / 2.0
    cross_same_end = (pair.z_even_ohm * coth_even - pair.z_odd_ohm * coth_odd) / 2.0
    cross_other_end = (pair.z_even_ohm * csch_even - pair.z_odd_ohm * csch_odd) / 2.0

    z_matrix = np.zeros((frequencies_hz.size, 4, 4), dtype=np.complex128)
    for row in range(4):
        z_matrix[:, row, row] = diagonal
    for row, column in ((0, 1), (1, 0), (2, 3), (3, 2)):
        z_matrix[:, row, column] = same_line
    for row, column in ((0, 2), (2, 0), (1, 3), (3, 1)):
        z_matrix[:, row, column] = cross_same_end
    for row, column in ((0, 3), (3, 0), (1, 2), (2, 1)):
        z_matrix[:, row, column] = cross_other_end

    identity = np.eye(4)
    s = (z_matrix - pair.z0_ohm * identity) @ np.linalg.inv(z_matrix + pair.z0_ohm * identity)

    if skew_s != 0.0:
        delay = np.exp(-2j * np.pi * frequencies_hz * skew_s)
        scaling = np.ones((frequencies_hz.size, 4), dtype=np.complex128)
        scaling[:, 3] = delay
        s = scaling[:, :, None] * s * scaling[:, None, :]

    return Network(frequencies_hz, s, z0=pair.z0_ohm)


def reference_mixed_mode(
    pair: CoupledPair,
    frequencies_hz: NDArray[np.float64],
    *,
    skew_s: float = 0.0,
) -> dict[str, NDArray[np.complex128]]:
    """Closed-form mixed-mode reference, derived in this module's docstring."""

    odd11, odd21 = line_two_port(
        pair.z_odd_ohm, pair.theta(frequencies_hz, even=False), pair.z0_ohm
    )
    even11, even21 = line_two_port(
        pair.z_even_ohm, pair.theta(frequencies_hz, even=True), pair.z0_ohm
    )
    delay = np.exp(-2j * np.pi * frequencies_hz * skew_s)

    return {
        "frequencies_hz": frequencies_hz.astype(np.complex128),
        "sdd11": odd11,
        "sdd21": odd21 * (1.0 + delay) / 2.0,
        "scc11": even11,
        "scc21": even21 * (1.0 + delay) / 2.0,
        "scd21": odd21 * (1.0 - delay) / 2.0,
        "sdc21": even21 * (1.0 - delay) / 2.0,
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def achieved_metrics(
    input_path: Path,
    reference: dict[str, NDArray[np.complex128]],
) -> dict[str, dict[str, float]]:
    """Accuracy of the shipped implementation against the reference.

    This is a record of where the case stood when it was approved, not the
    reference itself; the regression test recomputes it and compares against
    the tolerance in ``config.json``.
    """

    mixed = to_mixed_mode(read_touchstone(input_path), topology_by_id(TOPOLOGY_ID).port_group)
    metrics: dict[str, dict[str, float]] = {}
    for key, (response_mode, source_mode, response_port, source_port) in PARAMETERS.items():
        actual = mixed.mode_parameter(response_mode, source_mode, response_port, source_port)
        error = actual - reference[key]
        expected = reference[key]
        significant = np.abs(expected) > 1.0e-12
        magnitude_error_db = np.zeros_like(np.abs(error))
        phase_error_deg = np.zeros_like(np.abs(error))
        if significant.any():
            magnitude_error_db[significant] = 20.0 * np.log10(
                np.abs(actual[significant]) / np.abs(expected[significant])
            )
            phase_error_deg[significant] = np.degrees(
                np.angle(actual[significant] / expected[significant])
            )
        metrics[key] = {
            "max_abs_error": float(np.abs(error).max()),
            "rms_error": float(np.sqrt(np.mean(np.abs(error) ** 2))),
            "max_magnitude_error_db": float(np.abs(magnitude_error_db).max()),
            "max_phase_error_deg": float(np.abs(phase_error_deg).max()),
        }
    return metrics


def write_case(
    case_directory: Path,
    input_name: str,
    pair: CoupledPair,
    frequencies_hz: NDArray[np.float64],
    *,
    skew_s: float,
) -> None:
    (case_directory / "input").mkdir(parents=True, exist_ok=True)
    (case_directory / "reference").mkdir(parents=True, exist_ok=True)

    input_path = case_directory / "input" / input_name
    reference_path = case_directory / "reference" / "result.npz"

    network = coupled_pair_network(pair, frequencies_hz, skew_s=skew_s)
    write_touchstone(network, input_path, data_format="ri", frequency_unit="ghz")

    reference = reference_mixed_mode(pair, frequencies_hz, skew_s=skew_s)
    np.savez(reference_path, **reference)

    config = {
        "algorithm": "to_mixed_mode",
        "reference": "ANALYTICAL",
        "reference_version": "coupled transmission-line modal decomposition",
        "topology": "through_1_2_3_4",
        "parameters": {**asdict(pair), "skew_s": skew_s},
        "tolerance": {"rtol": 1.0e-9, "atol": 1.0e-12},
        "input_sha256": _sha256(input_path),
        "reference_sha256": _sha256(reference_path),
    }
    (case_directory / "config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (case_directory / "metrics.json").write_text(
        json.dumps(achieved_metrics(input_path, reference), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    frequencies_hz = np.arange(1, 201, dtype=np.float64) * 0.1e9
    pair = CoupledPair()

    write_case(
        GOLDEN_ROOT / "Case001_coupled_pair",
        "coupled_pair.s4p",
        pair,
        frequencies_hz,
        skew_s=0.0,
    )
    write_case(
        GOLDEN_ROOT / "Case002_coupled_pair_skew",
        "coupled_pair_skew.s4p",
        pair,
        frequencies_hz,
        skew_s=2.0e-12,
    )


if __name__ == "__main__":
    main()
