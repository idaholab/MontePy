# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
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

DATA_CLASSES = {
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

PREFIX_MATCHES = {c._class_prefix(): c for c in DATA_CLASSES}

VERBOTEN = {"de", "sdef", "fmesh"}


def parse_data(
    input: montepy.mcnp_object.InitInput,
    problem: montepy.MCNP_Problem = None,
    *,
    jit_parse: bool = True,
):
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
    DataClass = PREFIX_MATCHES.get(prefix)
    if DataClass is not None:
        if issubclass(DataClass, montepy.data_inputs.cell_modifier.CellModifierInput):
            return DataClass(input, problem=problem, jit_parse=jit_parse)
        return DataClass(input, jit_parse=jit_parse)
    return data_input.DataInput(input, prefix=prefix, jit_parse=jit_parse)
