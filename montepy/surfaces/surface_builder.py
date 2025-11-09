# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import montepy
from montepy.utilities import *
from montepy.surfaces.axis_plane import AxisPlane
from montepy.surfaces.surface import Surface, InitInput
from montepy.surfaces.surface_type import SurfaceType
from montepy.surfaces.cylinder_on_axis import CylinderOnAxis
from montepy.surfaces.cylinder_par_axis import CylinderParAxis
from montepy.surfaces.general_plane import GeneralPlane


#@args_checked
def parse_surface(input: InitInput, *, jit_parse: bool = True):
    """Builds a Surface object for the type of Surface

    Parameters
    ----------
    input : Input | str
        The Input object representing the input

    Returns
    -------
    Surface
        A Surface object properly parsed. If supported a sub-class of
        Surface will be given.
    """
    ST = SurfaceType
    if isinstance(input, str):
        input = montepy.input_parser.mcnp_input.Input(
            input.split("\n"), montepy.input_parser.block_type.BlockType.SURFACE
        )
    buffer_surface = Surface(input)
    type_of_surface = buffer_surface.surface_type
    for SurfaceClass in {CylinderOnAxis, CylinderParAxis, AxisPlane, GeneralPlane}:
        if type_of_surface in SurfaceClass._allowed_surface_types():
            return SurfaceClass(input, jit_parse=jit_parse)
    return Surface(input, jit_parse=jit_parse)


surface_builder = parse_surface
"""Alias for :func:`parse_surface`.

:deprecated: 1.0.0
    Renamed to be :func:`parse_surface` to be more pythonic.

Parameters
----------
input : Input | str
    The Input object representing the input

Returns
-------
Surface
    A Surface object properly parsed. If supported a sub-class of
    Surface will be given.
"""
