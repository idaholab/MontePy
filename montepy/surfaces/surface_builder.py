# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.surfaces.surface import (
    AxisPlane,
    CylinderOnAxis,
    CylinderParAxis,
    GeneralPlane,
    GeneralSphere,
    InitInput,
    SphereAtOrigin,
    SphereOnAxis,
    Surface,
)
from montepy.surfaces.surface_type import SurfaceType


def parse_surface(input: InitInput):
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
    buffer_surface = Surface(input)
    type_of_surface = buffer_surface.surface_type
    if type_of_surface in [ST.C_X, ST.C_Y, ST.C_Z]:
        return CylinderParAxis(input)
    elif type_of_surface in [ST.CX, ST.CY, ST.CZ]:
        return CylinderOnAxis(input)
    elif type_of_surface in [ST.PX, ST.PY, ST.PZ]:
        return AxisPlane(input)
    elif type_of_surface == ST.P:
        return GeneralPlane(input)
    elif type_of_surface == ST.S:
        return GeneralSphere(input)
    elif type_of_surface == ST.SO:
        return SphereAtOrigin(input)
    elif type_of_surface in [ST.SX, ST.SY, ST.SZ]:
        return SphereOnAxis(input)
    else:
        return buffer_surface


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
