# Copyright 2026, Battelle Energy Alliance, LLC All Rights Reserved.

"""
Material instances and their related objects
"""

import openmc
import montepy.data_inputs.nuclide


class OpenmcCompatNuclide(montepy.data_inputs.nuclide.Nuclide):
    """A nuclide converted from OpenMC

    Parameters
    ----------
    omc_nuclide : openmc.Nuclide
        The existing nuclide in an OpenMC material.
    library : str
        Cross section library suffix (e.g. "00c")
    """
    def __init__(self, omc_nuclide: openmc.Nuclide, library):
        super().__init__(name=omc_nuclide.name, library=library)



