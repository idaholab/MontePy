# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.surfaces.surface import (
    ArbitraryPolyhedron,
    AxisAlignedQuadric,
    AxisPlane,
    Box,
    ConeOnAxis,
    ConeParAxis,
    CylinderOnAxis,
    CylinderParAxis,
    Ellipsoid,
    GeneralPlane,
    GeneralQuadric,
    GeneralSphere,
    InitInput,
    RectangularParallelepiped,
    RightCircularCylinder,
    RightEllipticalCylinder,
    RightHexagonalPrism,
    SphereMacrobody,
    SphereAtOrigin,
    SphereOnAxis,
    Surface,
    Torus,
    TruncatedRightCone,
    Wedge,
)
from montepy.surfaces.surface_type import SurfaceType

_ST = SurfaceType

# Specific axis-variant classes (e.g. future XCylinder, YPlane) take
# precedence over the generic grouped classes below.  Add entries here
# when those classes are defined.
_SPECIFIC_DISPATCH: dict = {}

# Generic grouped classes: one class handles a family of surface types.
_GENERIC_DISPATCH: dict = {
    _ST.CX: CylinderOnAxis,
    _ST.CY: CylinderOnAxis,
    _ST.CZ: CylinderOnAxis,
    _ST.C_X: CylinderParAxis,
    _ST.C_Y: CylinderParAxis,
    _ST.C_Z: CylinderParAxis,
    _ST.PX: AxisPlane,
    _ST.PY: AxisPlane,
    _ST.PZ: AxisPlane,
    _ST.P: GeneralPlane,
    _ST.SO: SphereAtOrigin,
    _ST.S: GeneralSphere,
    _ST.SX: SphereOnAxis,
    _ST.SY: SphereOnAxis,
    _ST.SZ: SphereOnAxis,
    _ST.KX: ConeOnAxis,
    _ST.KY: ConeOnAxis,
    _ST.KZ: ConeOnAxis,
    _ST.K_X: ConeParAxis,
    _ST.K_Y: ConeParAxis,
    _ST.K_Z: ConeParAxis,
    _ST.SQ: AxisAlignedQuadric,
    _ST.GQ: GeneralQuadric,
    _ST.TX: Torus,
    _ST.TY: Torus,
    _ST.TZ: Torus,
    _ST.BOX: Box,
    _ST.RPP: RectangularParallelepiped,
    _ST.SPH: SphereMacrobody,
    _ST.RCC: RightCircularCylinder,
    _ST.RHP: RightHexagonalPrism,
    _ST.HEX: RightHexagonalPrism,
    _ST.REC: RightEllipticalCylinder,
    _ST.TRC: TruncatedRightCone,
    _ST.ELL: Ellipsoid,
    _ST.WED: Wedge,
    _ST.ARB: ArbitraryPolyhedron,
}


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
    buffer_surface = Surface(input)
    cls = _SPECIFIC_DISPATCH.get(buffer_surface.surface_type) or _GENERIC_DISPATCH.get(
        buffer_surface.surface_type
    )
    if cls is None:
        return buffer_surface
    return cls(input)


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
