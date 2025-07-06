# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.surfaces.axis_plane import AxisPlane
from montepy.surfaces.surface import Surface, InitInput
from montepy.surfaces.surface_type import SurfaceType
from montepy.surfaces.cylinder_on_axis import CylinderOnAxis
from montepy.surfaces.cylinder_par_axis import CylinderParAxis
from montepy.surfaces.general_plane import GeneralPlane


def parse_surface(input: InitInput, *, jit_parse: bool = False):
    """Builds a Surface object for the type of Surface

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input

    Returns
    -------
    Surface
        A Surface object properly parsed. If supported a sub-class of
        Surface will be given.
    """
    ST = SurfaceType
    buffer_surface = Surface._jit_light_init(input)
    type_of_surface = buffer_surface.surface_type
    for SurfaceClass in {CylinderOnAxis, CylinderParAxis, AxisPlane, GeneralPlane}:
        if type_of_surface in SurfaceClass._allowed_surface_types():
            if jit_parse:
                return SurfaceClass._jit_light_init(input)
            return SurfaceClass(input)
    return Surface(input)


surface_builder = parse_surface
"""Alias for :func:`parse_surface`.

:deprecated: 1.0.0
    Renamed to be :func:`parse_surface` to be more pythonic.

Parameters
----------
input : Union[Input, str]
    The Input object representing the input

Returns
-------
Surface
    A Surface object properly parsed. If supported a sub-class of
    Surface will be given.
"""
