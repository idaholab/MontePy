from enum import Enum, unique


@unique
class Lattice(Enum):
    """
    Represents the options for the lattice ``LAT``.

    Hexhedra is similar to a rectangular prism.
    Hexagonal must be a hexagonal prism.
    """

    HEXAHEDRA = 1
    HEXAGONAL = 2
