# Copyright 2024-2026, Battelle Energy Alliance, LLC All Rights Reserved.
from .surface import SphereOnAxis as Parent
import warnings


class SphereOnAxis(Parent):
    """Represents surfaces SX, SY, SZ: a sphere centered on a coordinate axis.

    The surface equation (e.g. for SX) is:

    .. math::

        (x - x_0)^2 + y^2 + z^2 - R^2 = 0

    .. tip::

        Since version 1.4.0 this has not been the preferred class for working with ``SX``, ``SY``, and ``SZ`` surfaces.
        Instead :class:`~montepy.XSphere`, :class:`~montepy.YSphere`, and :class:`~montepy.ZSphere` are preferred.
        There is no plan at this time to deprecate this class, but its use is not going to be promoted.

    .. versionadded:: 1.3.0

    .. deprecated:: 1.4.0

       Access this class through ``montepy.SphereOnAxis`` instead.

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
            "Submodule access to this class is deprecated. Use montepy.SphereOnAxis instead.",
            category=DeprecationWarning,
        )
        super().__init__(*args, **kwargs)
