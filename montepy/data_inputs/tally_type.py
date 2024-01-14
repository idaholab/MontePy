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
