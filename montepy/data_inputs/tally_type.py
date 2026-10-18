# Copyright 2024-2026, Battelle Energy Alliance, LLC All Rights Reserved.

from enum import unique, Enum
from typing import NamedTuple, Optional


class _TallyKey(NamedTuple):
    """The identity of a :class:`TallyType` member.

    A :class:`~typing.NamedTuple` rather than a dataclass: it needs to be
    hashable (an ``Enum`` member's value is looked up in a dict internally)
    and immutable, which a plain :class:`~typing.NamedTuple` gives for free.

    Attributes
    ----------
    mnemonic : str
        The card mnemonic, e.g. ``"F"``.
    modulo : int, optional
        The last digit of the card's number (``None`` for a card that
        doesn't dispatch by trailing digit at all, e.g. a future ``FMESH``
        entry).
    modifier : str, optional
        The classifier's leading symbol, if any (e.g. ``"+"`` for MCNP's
        ``+F6``/``+F8`` variants, or ``"*"`` for its ``*Fn`` variants) -- this
        is what lets two members share the same ``mnemonic``/``modulo``
        (``+F6`` vs plain ``F6``) while staying distinct under
        :func:`~enum.unique`.
    """

    mnemonic: str
    modulo: Optional[int]
    modifier: Optional[str] = None

    def __repr__(self):
        # Overridden so TallyType's own repr (which embeds repr(self.value))
        # shows the friendly "+6" instead of the raw
        # _TallyKey(mnemonic='F', modulo=6, modifier='+').
        body = str(self.modulo) if self.modulo is not None else self.mnemonic
        return f"{self.modifier}{body}" if self.modifier else body


@unique
class TallyUnits(Enum):
    """The units of a :class:`~montepy.Tally`'s result, per MCNP tally type.

    These are the units in the MCNP 6.3 manual's tally type table
    (:manual63:`5.9.1`). They are per source particle, and assume the source
    is in particles.

    .. versionadded:: 1.6.0b4
    """

    PARTICLES = "particles"
    PARTICLES_PER_CM2 = "particles/cm2"
    MEV = "MeV"
    MEV_PER_CM2 = "MeV/cm2"
    MEV_PER_G = "MeV/g"
    JERKS_PER_G = "jerks/g"
    PULSES = "pulses"
    CHARGE = "charge"


@unique
class TallyType(Enum):
    """The MCNP tally type: which mnemonic/digit/modifier combination an
    input uses (e.g. the last digit of an F-card's number, or a leading
    ``+`` for a modified variant like ``+F6``).

    .. versionadded:: 1.6.0b2
    .. versionchanged:: 1.6.0b3
        Values changed from a bare digit to a ``(mnemonic, modulo, modifier)``
        tuple, so a modifier-prefixed variant (e.g. ``+F6`` collision
        heating vs. plain ``F6`` energy deposition) can be a distinct member
        that still shares its digit with the unmodified card -- and so this
        enum can eventually grow to cover non-``F``-card tallies (e.g.
        ``FMESH``) without another redesign.
    .. versionchanged:: 1.6.0b4
        Added the ``*`` variants (e.g. ``*F4``). Every valid combination is a
        member, even when two map to the same :class:`~montepy.Tally`
        class, as ``F6`` and ``*F6`` do.
    """

    CURRENT = _TallyKey("F", 1)
    ENERGY_CURRENT = _TallyKey("F", 1, "*")
    """.. versionadded:: 1.6.0b4"""
    SURFACE_FLUX = _TallyKey("F", 2)
    SURFACE_ENERGY_FLUX = _TallyKey("F", 2, "*")
    """.. versionadded:: 1.6.0b4"""
    CELL_FLUX = _TallyKey("F", 4)
    CELL_ENERGY_FLUX = _TallyKey("F", 4, "*")
    """.. versionadded:: 1.6.0b4"""
    ENERGY_DEPOSITION = _TallyKey("F", 6)
    ENERGY_DEPOSITION_JERKS = _TallyKey("F", 6, "*")
    """.. versionadded:: 1.6.0b4"""
    COLLISION_HEATING = _TallyKey("F", 6, "+")
    FISSION_ENERGY_DEPOSITION = _TallyKey("F", 7)
    FISSION_ENERGY_DEPOSITION_JERKS = _TallyKey("F", 7, "*")
    """.. versionadded:: 1.6.0b4"""
    ENERGY_DETECTOR_PULSE = _TallyKey("F", 8)
    DETECTOR_ENERGY_DEPOSITION = _TallyKey("F", 8, "*")
    """.. versionadded:: 1.6.0b4"""
    CHARGE_DEPOSITION = _TallyKey("F", 8, "+")

    @property
    def mnemonic(self) -> str:
        """The card mnemonic, e.g. ``"F"``."""
        return self.value.mnemonic

    @property
    def modulo(self) -> Optional[int]:
        """The last digit of the card's number, if it dispatches by digit."""
        return self.value.modulo

    @property
    def modifier(self) -> Optional[str]:
        """The classifier's leading modifier symbol, if any (e.g. ``"+"``)."""
        return self.value.modifier

    @property
    def units(self) -> TallyUnits:
        """The units of this tally type's result.

        .. versionadded:: 1.6.0b4
        """
        return _UNITS[self]


@unique
class Score(Enum):
    """The physical quantity a :class:`~montepy.Tally` scores.

    A shallow analog of OpenMC's tally scores: for MontePy this is just the
    quantity implied by the tally type (e.g. F4 always scores
    :class:`Score.FLUX`). If an FM tally-multiplier card is linked to the
    tally, :attr:`~montepy.Tally.scores` returns a list of
    :class:`~montepy.data_inputs.tally_multiplier.MultiplierScore` instead of
    this enum -- see :attr:`~montepy.Tally.multiplier`.

    ``Score`` is deliberately coarser than :class:`TallyType`: several tally
    types report the same physical quantity, so they collapse to one
    ``Score`` (``SURFACE_FLUX`` and ``CELL_FLUX`` are two distinct
    ``TallyType`` members that both report ``Score.FLUX`` -- flux is flux,
    whether it's tallied at a surface or in a cell). ``TallyType`` answers "how is this number dispatched," while
    ``Score`` answers "what quantity does it report" -- they aren't
    redundant.

    .. versionadded:: 1.6.0b2
    """

    CURRENT = 1
    FLUX = 2
    ENERGY_DEPOSITION = 6
    FISSION_ENERGY_DEPOSITION = 7
    PULSE_HEIGHT = 8
    COLLISION_HEATING = 9
    """.. versionadded:: 1.6.0b3"""
    CHARGE_DEPOSITION = 10
    """.. versionadded:: 1.6.0b3"""
    ENERGY_CURRENT = 11
    """.. versionadded:: 1.6.0b4"""
    ENERGY_FLUX = 12
    """.. versionadded:: 1.6.0b4"""


_UNITS = {
    TallyType.CURRENT: TallyUnits.PARTICLES,
    TallyType.ENERGY_CURRENT: TallyUnits.MEV,
    TallyType.SURFACE_FLUX: TallyUnits.PARTICLES_PER_CM2,
    TallyType.SURFACE_ENERGY_FLUX: TallyUnits.MEV_PER_CM2,
    TallyType.CELL_FLUX: TallyUnits.PARTICLES_PER_CM2,
    TallyType.CELL_ENERGY_FLUX: TallyUnits.MEV_PER_CM2,
    TallyType.ENERGY_DEPOSITION: TallyUnits.MEV_PER_G,
    TallyType.ENERGY_DEPOSITION_JERKS: TallyUnits.JERKS_PER_G,
    TallyType.COLLISION_HEATING: TallyUnits.MEV_PER_G,
    TallyType.FISSION_ENERGY_DEPOSITION: TallyUnits.MEV_PER_G,
    TallyType.FISSION_ENERGY_DEPOSITION_JERKS: TallyUnits.JERKS_PER_G,
    TallyType.ENERGY_DETECTOR_PULSE: TallyUnits.PULSES,
    TallyType.DETECTOR_ENERGY_DEPOSITION: TallyUnits.MEV,
    TallyType.CHARGE_DEPOSITION: TallyUnits.CHARGE,
}
