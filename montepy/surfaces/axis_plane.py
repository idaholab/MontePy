# Copyright 2024-2026, Battelle Energy Alliance, LLC All Rights Reserved.
from .surface import AxisPlane as Parent
import warnings


class AxisPlane(Parent):
    """Represents surfaces PX, PY, PZ: a plane normal to a coordinate axis.

    The surface equation (e.g. for PZ) is:

    .. math::

        z - d = 0

    .. tip::

        Since version 1.4.0 this has not been the preferred class for working with ``PX``, ``PY``, and ``PZ`` surfaces.
        Instead :class:`~montepy.XPlane`, :class:`~montepy.YPlane`, and :class:`~montepy.ZPlane` are preferred.
        There is no plan at this time to deprecate this class, but its use is not going to be promoted.

    .. versionchanged:: 1.0.0

        Added number parameter

    .. deprecated:: 1.4.0

       Access this class through ``montepy.AxisPlane`` instead.

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
            "Submodule access to this class is deprecated. Use montepy.AxisPlane instead.",
            category=DeprecationWarning,
        )
        super().__init__(*args, **kwargs)
