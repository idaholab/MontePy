# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from enum import Enum, unique


@unique
class BlockType(Enum):
    """
    An enumeration for the different blocks in an input file.
    """

    CELL = 0
    """
    The first block that details Cell information.
    """
    SURFACE = 1
    """
    The second block that details Surface information.
    """
    DATA = 2
    """
    The third block that provides additional information
    and data.
    """
