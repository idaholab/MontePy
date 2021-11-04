from enum import Enum, unique

@unique
class BlockType(Enum):
    CELL = 0
    SURFACE = 1
    DATA = 2
