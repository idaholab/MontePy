# Copyright 2024-2026, Battelle Energy Alliance, LLC All Rights Reserved.

from enum import unique, Enum
from typing import NamedTuple, Optional


class _TallyKey(NamedTuple):
    """The identity of a :class:`TallyType` member.

    ``modulo`` is the last digit of the card's number (``None`` for a card
    that doesn't dispatch by trailing digit at all, e.g. a future ``FMESH``
    entry). ``modifier`` is the classifier's leading symbol, if any (e.g.
    ``"+"`` for MCNP's ``+F6``/``+F8`` variants) -- this is what lets two
    members share the same ``mnemonic``/``modulo`` (``+F6`` vs plain ``F6``)
    while staying distinct under :func:`~enum.unique`.
    """

    mnemonic: str
    modulo: Optional[int]
    modifier: Optional[str] = None

    def __repr__(self):
        body = str(self.modulo) if self.modulo is not None else self.mnemonic
        return f"{self.modifier}{body}" if self.modifier else body


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
    """

    CURRENT = _TallyKey("F", 1)
    SURFACE_FLUX = _TallyKey("F", 2)
    CELL_FLUX = _TallyKey("F", 4)
    DETECTOR = _TallyKey("F", 5)
    ENERGY_DEPOSITION = _TallyKey("F", 6)
    COLLISION_HEATING = _TallyKey("F", 6, "+")
    FISSION_ENERGY_DEPOSITION = _TallyKey("F", 7)
    ENERGY_DETECTOR_PULSE = _TallyKey("F", 8)
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


@unique
class Score(Enum):
    """The physical quantity a :class:`~montepy.Tally` scores.

    A shallow analog of OpenMC's tally scores: for MontePy this is just the
    quantity implied by the tally type (e.g. F4 always scores
    :class:`Score.FLUX`). If an FM tally-multiplier card is linked to the
    tally, :attr:`~montepy.Tally.scores` returns a list of
    :class:`~montepy.data_inputs.tally_multiplier.MultiplierScore` instead of
    this enum -- see :attr:`~montepy.Tally.multiplier`.

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
