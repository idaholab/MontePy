# Copyright 2024-2026, Battelle Energy Alliance, LLC All Rights Reserved.
from .surface import CylinderParAxis as Parent
import warnings


class CylinderParAxis(Parent):
    """Represents surfaces C/X, C/Y, C/Z: an infinite cylinder whose axis is
    parallel to a coordinate axis but offset from it.

    The surface equation (e.g. for C/Z) is:

    .. math::

        (x - x_0)^2 + (y - y_0)^2 - R^2 = 0

    .. tip::

        Since version 1.4.0 this has not been the preferred class for working with ``C/X``, ``C/Y``, and ``C/Z`` surfaces.
        Instead :class:`~montepy.XCylinderParAxis`, :class:`~montepy.YCylinderParAxis`, and :class:`~montepy.ZCylinderParAxis` are preferred.
        There is no plan at this time to deprecate this class, but its use is not going to be promoted.

    .. versionchanged:: 1.0.0

        Added number parameter

    .. deprecated:: 1.4.0

       Access this class through ``montepy.CylinderParAxis`` instead.

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
            "Submodule access to this class is deprecated. Use montepy.CylinderParAxis instead.",
            category=DeprecationWarning,
        )
        super().__init__(*args, **kwargs)
