from enum import Enum, unique


@unique
class Lattice(Enum):
    """
    Represents the options for the lattice ``LAT``.
    """

    HEXAHEDRA = 1
    """
    Hexhedra are solids with six faces.

    One such solid is a rectangular prism.
    """
    HEXAGONAL = 2
    """
    Hexagonal prism are solids with eight faces.
    """
