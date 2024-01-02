# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from enum import Enum, unique


@unique
class Particle(Enum):
    """
    Supported MCNP supported particles.

    Taken from Table 2-2 of LA-UR-17-29981.
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
