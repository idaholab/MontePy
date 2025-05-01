# Copyright 2024 - 2025, Battelle Energy Alliance, LLC All Rights Reserved.
from enum import Enum, unique
from warnings import warn


@unique
class LatticeType(Enum):
    """Represents the options for the lattice ``LAT``."""

    HEXAHEDRAL = 1
    """Hexhedra are solids with six faces.

    One such solid is a rectangular prism.
    """
    HEXAGONAL = 2
    """Hexagonal prism are solids with eight faces."""


class __DeprecatedLattice:
    """Helper for deprecated Enum behavior"""

    @property
    def HEXAHEDRA(self):
        warn(
            message="Lattice.HEXAHEDRA is deprecated in favor of LatticeType.HEXAHEDRAL",
            category=DeprecationWarning,
        )
        return LatticeType.HEXAHEDRAL

    @property
    def HEXAGONAL(self):
        warn(
            message="Lattice.HEXAGONAL is deprecated in favor of LatticeType.HEXAGONAL",
            category=DeprecationWarning,
        )
        return LatticeType.HEXAGONAL


Lattice = __DeprecatedLattice()
