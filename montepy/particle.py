# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from enum import unique, Enum


@unique
class Particle(str, Enum):
    """Supported MCNP supported particles.

    Taken from :manual62:`46`.
    """

    NEUTRON = "N"
    PHOTON = "P"
    ELECTRON = "E"
    NEGATIVE_MUON = "|"
    ANTI_NEUTRON = "Q"
    ELECTRON_NEUTRINO = "U"
    MUON_NEUTRINO = "V"
    POSITRON = "F"
    PROTON = "H"
    LAMBDA_BARYON = "L"
    POSITIVE_SIGMA_BARYON = "+"
    NEGATIVE_SIGMA_BARYON = "-"
    CASCADE = "X"
    NEGATIVE_CASCADE = "Y"
    OMEGA_BARYON = "O"
    POSITIVE_MUON = "!"
    ANTI_ELECTRON_NEUTRINO = "<"
    ANTI_MUON_NEUTRINO = ">"
    ANTI_PROTON = "G"
    POSITIVE_PION = "/"
    NEUTRAL_PION = "Z"
    POSITIVE_KAON = "K"
    KAON_SHORT = "%"
    KAON_LONG = "^"
    ANTI_LAMBDA_BARYON = "B"
    ANTI_POSITIVE_SIGMA_BARYON = "_"
    ANTI_NEGATIVE_SIGMA_BARYON = "~"
    ANTI_CASCADE = "C"
    POSITIVE_CASCADE = "W"
    ANTI_OMEGA = "@"
    DEUTERON = "D"
    TRITON = "T"
    HELION = "S"
    ALPHA_PARTICLE = "A"
    NEGATIVE_PION = "*"
    NEGATIVE_KAON = "?"
    HEAVY_ION = "#"

    def __lt__(self, other):
        return self.value < other.value

    def __str__(self):
        return self.name.lower()

    def __eq__(self, other):
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)


@unique
class LibraryType(str, Enum):
    """Enum to represent the possible types that a nuclear data library can be.

    .. versionadded:: 1.0.0

    Taken from :manual63:`5.6.1`.
    """

    def __new__(cls, value, particle=None):
        obj = str.__new__(cls)
        obj._value_ = value
        obj._particle_ = particle
        return obj

    NEUTRON = ("NLIB", Particle.NEUTRON)
    PHOTO_ATOMIC = ("PLIB", None)
    PHOTO_NUCLEAR = ("PNLIB", None)
    ELECTRON = ("ELIB", Particle.ELECTRON)
    PROTON = ("HLIB", Particle.PROTON)
    ALPHA_PARTICLE = ("ALIB", Particle.ALPHA_PARTICLE)
    HELION = ("SLIB", Particle.HELION)
    TRITON = ("TLIB", Particle.TRITON)
    DEUTERON = ("DLIB", Particle.DEUTERON)

    def __str__(self):
        return self.name.lower()

    def __lt__(self, other):
        return self.value < other.value

    def __eq__(self, other):
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)
