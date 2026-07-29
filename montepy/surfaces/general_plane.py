# Copyright 2024-2026, Battelle Energy Alliance, LLC All Rights Reserved.
from .surface import GeneralPlane as Parent
import warnings


class GeneralPlane(Parent):
    """Represents surface P: a general plane.

    The surface equation is:

    .. math::

        Ax + By + Cz - D = 0

    May also be defined by three points (9 surface constants).

    .. versionchanged:: 1.0.0

        Added number parameter

    .. deprecated:: 1.4.0

       Access this class through ``montepy.GeneralPlane`` instead.

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Submodule access to this class is deprecated. Use montepy.GeneralPlane instead.",
            category=DeprecationWarning,
        )
        super().__init__(*args, **kwargs)
