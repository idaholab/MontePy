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
    tally,
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
    tally.Tally,
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

    try:
        bare_tree = data_input.DataInput._peek_light_parse(input)
        prefix = bare_tree.nodes["classifier"].prefix.value.lower()
    except Exception:
        # The JIT light parser isn't fully robust and can fail on valid
        # syntax. Fall back to building a real DataInput: its own
        # JIT-with-fallback-to-full-parse handling in _parse_input will
        # reliably determine the prefix instead of guessing.
        base_input = data_input.DataInput(input, fast_parse=True)
        prefix = base_input.prefix
    if prefix in VERBOTEN:
        return data_input.ForbiddenDataInput(input)
    DataClass = PREFIX_MATCHES.get(prefix)
    if DataClass is not None:
        if DataClass is tally.Tally:
            return tally.Tally.from_input(input, jit_parse=jit_parse)
        if issubclass(DataClass, montepy.data_inputs.cell_modifier.CellModifierInput):
            return DataClass(input, problem=problem, jit_parse=jit_parse)
        return DataClass(input, jit_parse=jit_parse)
    return data_input.DataInput(input, prefix=prefix, jit_parse=jit_parse)
