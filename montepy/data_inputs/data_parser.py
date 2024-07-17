# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
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


def parse_data(input):
    """
    Parses the data input as the appropriate object if it is supported.

    .. versionchanged:: 0.2.0
        Removed the ``comment`` parameter, as it's in the syntax tree directly now.

    :param input: the Input object for this Data input
    :type input: Input
    :return: the parsed DataInput object
    :rtype: DataInput
    """

    base_input = data_input.DataInput(input, fast_parse=True)
    prefix = base_input.prefix
    for data_class in PREFIX_MATCHES:
        if prefix == data_class._class_prefix():
            return data_class(input)
    return data_input.DataInput(input, prefix=prefix)
