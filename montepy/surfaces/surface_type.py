# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from enum import unique, Enum


# @unique
class SurfaceType(str, Enum):
    """
    An enumeration of the surface types allowed.

    :param value: The shorthand used by MCNP
    :type value: str
    :param description: The human readable description of the surface.
    :type description: str
    """

    def __new__(cls, value, description):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.description = description
        return obj

    def __str__(self):
        return self.value

    # planes
    P = ("P", "general plane")
    PX = ("PX", "plane normal to x-axis")
    PY = ("PY", "plane normal to y-axis")
    PZ = ("PZ", "plane normal to z-axis")
    # spheres
    SO = ("SO", "sphere centered at origin")
    S = ("S", "general sphere")
    SX = ("SX", "sphere centered on x-axis")
    SY = ("SY", "sphere centered on y-axis")
    SZ = ("SZ", "sphere centered on z-axis")
    # cylinder
    C_X = ("C/X", "cylinder parallel to x-axis")
    C_Y = ("C/Y", "cylinder parallel to y-axis")
    C_Z = ("C/Z", "cylinder parallel to z-axis")
    CX = ("CX", "cylinder on x-axis")
    CY = ("CY", "cylinder on y-axis")
    CZ = ("CZ", "cylinder on z-axis")
    # cone
    K_X = ("K/X", "cone parallel to x-axis")
    K_Y = ("K/Y", "cone parallel to y-axis")
    K_Z = ("K/Z", "cone parallel to z-axis")
    KX = ("KX", "cone on x-axis")
    KY = ("KY", "cone on y-axis")
    KZ = ("KZ", "cone on z-axis")
    # generalized 3D conics
    SQ = ("SQ", "ellipsoid, hyperboloid, or paraboloid parallel to an axis")
    GQ = (
        "GQ",
        "cylinder, cone, ellipsoid hyperboloid, or parabaloid not parallel to an axis",
    )
    # Torus
    TX = ("TX", "elliptical torus parallel to x-axis")
    TY = ("TY", "elliptical torus parallel to y-axis")
    TZ = ("TZ", "elliptical torus parallel to z-axis")
    # by points
    X = ("X", "axisymmetric surface defined by points")
    Y = ("Y", "axisymmetric surface defined by points")
    Z = ("Z", "axisymmetric surface defined by points")
    # macrobodies
    BOX = ("BOX", "orthogonal box")
    RPP = ("RPP", "rectangular parallelepiped")
    SPH = ("SPH", "sphere")
    RCC = ("RCC", "right circular cylinder")
    RHP = ("RHP", "right hexagonal prism")
    HEX = ("HEX", "right hexagonal prism")
    REC = ("REC", "right elliptical cylinder")
    TRC = ("TRC", "truncated right-angle cone")
    ELL = ("ELL", "ellipsoid")
    WED = ("WED", "wedge")
    ARB = ("ARB", "arbitrary polyhedron")
