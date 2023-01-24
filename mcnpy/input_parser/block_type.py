from enum import Enum, unique


@unique
class BlockType(Enum):
    """
    Enum for all of the blocks allowed in MCNP.
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
