"""Change a network's reference impedance.

The wave definition is pseudo wave / traveling wave (Marks & Williams), as
decided in ``ALGORITHM_GUIDE.md`` §11. It is exposed as an explicit
parameter rather than assumed, because pseudo and power waves disagree
once the reference impedance is complex, and silently picking one would be
the kind of hidden convention this project forbids.

Derivation
----------
``Network`` carries one scalar reference impedance for all ports (see
``DOMAIN_MODEL.md`` §5), which makes the transform a closed form rather
than a matrix congruence.

For pseudo waves ``a = (k/2)(V + z I)`` and ``b = (k/2)(V - z I)``, so with
a scalar reference the normalisation ``k`` cancels and

    S = (Z - z) (Z + z)^-1        Z = z (I + S) (I - S)^-1

Eliminating ``Z`` between the old reference ``z1`` and the new ``z2``, and
dividing through by ``z1 + z2``:

    S' = (S + r I) (I + r S)^-1        r = (z1 - z2) / (z1 + z2)

``r`` is the reflection coefficient one reference impedance presents to
the other. Going through ``r`` instead of forming ``Z`` keeps an ideal
open or short finite, where ``(I - S)`` would be singular.

For a passive network ``rho(r S) <= |r| < 1``, so ``I + r S`` is
invertible; a network that makes it singular is not one this transform can
describe, and says so.
"""

from enum import StrEnum
from typing import Final

import numpy as np
from numpy.typing import NDArray

from interconnect_studio.core import InputValidationError, Network


class SParameterDefinition(StrEnum):
    """Which wave amplitudes the S-parameters are defined against.

    The two agree exactly at a real reference impedance and differ only
    at a complex one, which is why the choice only ever shows up with
    lossy fixture impedances.
    """

    PSEUDO = "pseudo"
    """Pseudo / traveling wave (Marks & Williams). The project default."""

    POWER = "power"
    """Power wave (Kurokawa). Specified but not implemented; see §11."""


DEFAULT_S_DEFINITION: Final[SParameterDefinition] = SParameterDefinition.PSEUDO


def renormalize(
    network: Network,
    new_z0: complex,
    *,
    s_def: SParameterDefinition = DEFAULT_S_DEFINITION,
) -> Network:
    """Return the network referenced to ``new_z0`` instead of its own.

    Parameters
    ----------
    network:
        Source network; it is read, never modified.
    new_z0:
        New reference impedance in ohms, for every port. Must be finite
        with a positive real part, as a physical reference impedance is.
    s_def:
        Wave definition. Only ``PSEUDO`` is implemented.

    Returns
    -------
    Network
        A new Network with the same frequencies (Hz, shape ``(n_freq,)``),
        the same port names, S of shape ``(n_freq, n_port, n_port)``, and
        ``z0`` set to ``new_z0``.

    Raises
    ------
    InputValidationError
        If ``new_z0`` is not a usable reference impedance, or if the
        transform is singular at some frequency.
    NotImplementedError
        If ``s_def`` is ``POWER``.

    Notes
    -----
    Renormalisation moves no energy, so a passive network stays passive
    and a reciprocal one stays reciprocal. Both are worth checking with
    ``check_passivity`` / ``check_reciprocity`` after a chain of
    transforms.
    """

    if s_def is SParameterDefinition.POWER:
        raise NotImplementedError(
            "Power-wave renormalisation is specified in ALGORITHM_GUIDE.md §11 "
            "but not implemented; use SParameterDefinition.PSEUDO."
        )

    old_z0 = network.z0
    target = _validate_reference_impedance(new_z0, "new_z0")
    _validate_reference_impedance(old_z0, "network.z0")

    reflection = (old_z0 - target) / (old_z0 + target)
    return Network(
        network.frequencies_hz,
        _transform(network.s, reflection),
        z0=target,
        port_names=network.port_names,
    )


def _transform(
    s: NDArray[np.complex128],
    reflection: complex,
) -> NDArray[np.complex128]:
    """Apply ``(S + r I)(I + r S)^-1`` over the frequency axis.

    Solved rather than inverted: ``X B = A`` is ``B.T X.T = A.T``.
    """

    identity = np.eye(s.shape[1], dtype=np.complex128)
    numerator = s + reflection * identity
    denominator = identity + reflection * s
    try:
        transposed = np.linalg.solve(
            denominator.transpose(0, 2, 1),
            numerator.transpose(0, 2, 1),
        )
    except np.linalg.LinAlgError as exc:
        raise InputValidationError(
            "Renormalisation is singular for this network: no reference impedance "
            "change can describe it. A passive network cannot reach this state."
        ) from exc
    return np.ascontiguousarray(transposed.transpose(0, 2, 1))


def _validate_reference_impedance(z0: complex, name: str) -> complex:
    value = complex(z0)
    if not np.isfinite(value.real) or not np.isfinite(value.imag):
        raise InputValidationError(f"{name} must be finite.")
    if value.real <= 0.0:
        raise InputValidationError(
            f"{name} must have a positive real part, got {value}."
        )
    return value
