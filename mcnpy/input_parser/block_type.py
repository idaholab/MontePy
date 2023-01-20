from enum import Enum, unique


@unique
class BlockType(Enum):
    """
    An enumeration for the different blocks in an input file.
    """

    CELL = 0
    SURFACE = 1
    DATA = 2
