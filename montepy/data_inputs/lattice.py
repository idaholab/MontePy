# Copyright 2024 - 2025, Battelle Energy Alliance, LLC All Rights Reserved.
from enum import Enum
from warnings import warn


class LatticeType(Enum):
    """Represents the options for the lattice ``LAT``."""

    RECTANGULAR = 1
    """A rectangular prism is a type of hexahedron: solid with six faces."""
    HEXAHEDRAL = RECTANGULAR
    """Hexhedra are solids with six faces.
    
    One such solid is a rectangular prism.
    """
    HEXAGONAL = 2
    """Hexagonal prisms are solids with eight faces."""


class __DeprecatedLattice:
    """Helper for deprecated Enum behavior"""

    @property
    def HEXAHEDRA(self):
        warn(
            message="Lattice.HEXAHEDRA is deprecated in favor of LatticeType.RECTANGULAR",
            category=DeprecationWarning,
        )
        return LatticeType.RECTANGULAR

    @property
    def HEXAGONAL(self):
        warn(
            message="Lattice.HEXAGONAL is deprecated in favor of LatticeType.HEXAGONAL",
            category=DeprecationWarning,
        )
        return LatticeType.HEXAGONAL


Lattice = __DeprecatedLattice()
