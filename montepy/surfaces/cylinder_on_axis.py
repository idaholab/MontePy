# Copyright 2024-2026, Battelle Energy Alliance, LLC All Rights Reserved.
from .surface import CylinderOnAxis as Parent
import warnings


class CylinderOnAxis(Parent):
    """Represents surfaces CX, CY, CZ: an infinite cylinder whose axis lies on
    a coordinate axis.

    The surface equation (e.g. for CZ) is:

    .. math::

        x^2 + y^2 - R^2 = 0

    .. tip::

        Since version 1.4.0 this has not been the preferred class for working with ``CX``, ``CY``, and ``CZ`` surfaces.
        Instead :class:`~montepy.XCylinder`, :class:`~montepy.YCylinder`, and :class:`~montepy.ZCylinder` are preferred.
        There is no plan at this time to deprecate this class, but its use is not going to be promoted.

    .. versionchanged:: 1.0.0

        Added number parameter

    .. deprecated:: 1.4.0

       Access this class through ``montepy.CylinderOnAxis`` instead.

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    surface_type : Union[SurfaceType, str]
        The surface_type to set for this object
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Submodule access to this class is deprecated. Use montepy.CylinderOnAxis instead.",
            category=DeprecationWarning,
        )
        super().__init__(*args, **kwargs)
