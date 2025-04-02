# Copyright 2024 - 2025, Battelle Energy Alliance, LLC All Rights Reserved.
from enum import Enum, unique
from warnings import warn


def _lattice_deprecation_warning():
    warn(
        message="lattice.Lattice is deprecated in favor of lattice.LatticeType",
        category=DeprecationWarning,
    )


@unique
class LatticeType(Enum):
    """Represents the options for the lattice ``LAT``."""

    HEXAHEDRA = 1
    """Hexhedra are solids with six faces.

    One such solid is a rectangular prism.
    """
    HEXAGONAL = 2
    """Hexagonal prism are solids with eight faces."""


class Lattice(Enum):
    """Deprecated"""

    @property
    def HEXAHEDRA(self):
        _lattice_deprecation_warning()
        return LatticeType.HEXAHEDRA

    @property
    def HEXAGONAL(self):
        _lattice_deprecation_warning()
        return LatticeType.HEXAGONAL
