# Copyright 2024-2026, Battelle Energy Alliance, LLC All Rights Reserved.
from .surface import SphereAtOrigin as Parent
import warnings


class SphereAtOrigin(Parent):
    """Represents surface SO: a sphere centered at the origin.

    The surface equation is:

    .. math::

        x^2 + y^2 + z^2 - R^2 = 0

    .. versionadded:: 1.3.0

    .. deprecated:: 1.4.0

       Access this class through ``montepy.SphereAtOrigin`` instead.

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Submodule access to this class is deprecated. Use montepy.SphereAtOrigin instead.",
            category=DeprecationWarning,
        )
        super().__init__(*args, **kwargs)
