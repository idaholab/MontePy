# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import re

import montepy
from montepy.utilities import *
from montepy.data_inputs import (
    data_input,
    fill,
    importance,
    lattice_input,
    material,
    mode,
    thermal_scattering,
    universe_input,
    volume,
)
from montepy.data_inputs import transform

PREFIX_MATCHES = {
    fill.Fill,
    importance.Importance,
    lattice_input.LatticeInput,
    material.Material,
    mode.Mode,
    thermal_scattering.ThermalScatteringLaw,
    transform.Transform,
    volume.Volume,
    universe_input.UniverseInput,
}

VERBOTEN = {"de", "sdef"}


@args_checked
def parse_data(input: montepy.mcnp_object.InitInput, *, jit_parse: bool = True):
    """Parses the data input as the appropriate object if it is supported.

    Parameters
    ----------
    input : Input | str
        the Input object for this Data input

    Returns
    -------
    DataInput
        the parsed DataInput object
    """

    base_input = data_input.DataInput(input, fast_parse=True)
    prefix = base_input.prefix
    if base_input.prefix in VERBOTEN:
        return data_input.ForbiddenDataInput(input)
    for DataClass in PREFIX_MATCHES:
        if prefix == DataClass._class_prefix():
            return DataClass(input, jit_parse=jit_parse)
    return data_input.DataInput(input, jit_parse=jit_parse)
