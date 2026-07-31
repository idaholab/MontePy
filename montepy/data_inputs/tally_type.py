# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.

from enum import unique, Enum


@unique
class TallyType(Enum):
    """ """

    CURRENT = 1
    SURFACE_FLUX = 2
    CELL_FLUX = 4
    DETECTOR = 5
    ENERGY_DEPOSITION = 6
    FISSION_ENERGY_DEPOSITION = 7
    ENERGY_DETECTOR_PULSE = 8


@unique
class Score(Enum):
    """The physical quantity a :class:`~montepy.data_inputs.tally.Tally` scores.

    A shallow analog of OpenMC's tally scores: for MontePy this is just the
    quantity implied by the tally type digit (e.g. F4 always scores
    :class:`Score.FLUX`), not something derived from FM tally-multiplier
    cards, which aren't modeled yet.
    """

    CURRENT = 1
    FLUX = 2
    ENERGY_DEPOSITION = 6
    FISSION_ENERGY_DEPOSITION = 7
    PULSE_HEIGHT = 8
