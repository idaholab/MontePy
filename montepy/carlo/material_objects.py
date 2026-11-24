# Copyright 2026, Battelle Energy Alliance, LLC All Rights Reserved.

"""
Material instances and their related objects
"""

import warnings
import openmc
import montepy.data_inputs.nuclide
import montepy.data_inputs.material
import montepy.data_inputs.thermal_scattering


class OpenmcCompatMaterial(montepy.data_inputs.material.Material):
    """A nuclide converted from OpenMC

    Parameters
    ----------
    omc_mat : openmc.Material
        The existing
    xs_library : str
        Cross section library suffix for all nuclides unless overridden
    xs_overrides : dict of {str : str} or None
        Mapping of {nuclide : xs_library} for specific nuclides
    tsl_library : str or None
        Thermal scattering law library suffix (e.g. "40t")
    """

    def __init__(
        self,
        omc_mat: openmc.Material,
        xs_library: str,
        xs_overrides: dict[str, str] = None,
        tsl_library: str = None,
    ):
        if xs_overrides is None:
            xs_overrides = {}
        super().__init__(number=omc_mat.id)
        namestr = f"Material {omc_mat.id}"
        if omc_mat.name:
            namestr += f'" ({omc_mat.name})"'
        # Get all the material components
        if not omc_mat.nuclides:
            raise ValueError(f"{namestr} has no nuclides.")
        for name, frac, frac_type in omc_mat.nuclides:
            suffix = xs_overrides.get(name, xs_library)
            nuc = montepy.data_inputs.nuclide.Nuclide(name, library=suffix)
            self.add_nuclide(nuc, frac)
        if frac_type == "wo":
            self.is_atom_fraction = False
        # Thermal scattering law, still being implemented
        if omc_mat._sab:
            warnings.warn("Thermal Scattering Laws are not yet implemented!")
        for sab, frac in omc_mat._sab:  # not exposed by OpenMC
            if frac != 1.0:
                raise ValueError(
                    f"{namestr} has {sab} at a fraction of {frac}. "
                    "Partial S(a,b) tables are not permitted in MCNP."
                )
            # law = suffix_matching_function(sab, tsl_library)
            # self.add_thermal_scattering(law)
