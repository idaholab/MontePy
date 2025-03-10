# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.

import montepy
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
import re

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


def parse_data(input: montepy.mcnp_object.InitInput):
    """Parses the data input as the appropriate object if it is supported.

    Parameters
    ----------
    input : Union[Input, str]
        the Input object for this Data input

    Returns
    -------
    DataInput
        the parsed DataInput object
    """

    base_input = data_input.DataInput(input, fast_parse=True)
    prefix = base_input.prefix
    for data_class in PREFIX_MATCHES:
        if prefix == data_class._class_prefix():
            return data_class(input)
    return data_input.DataInput(input, prefix=prefix)
