# Copyright 2026, Battelle Energy Alliance, LLC All Rights Reserved.
from .surface import GeneralSphere as Parent
import warnings


class GeneralSphere(Parent):
    """Represents surface S: a general sphere.

    The surface equation is:

    .. math::

        (x - x_0)^2 + (y - y_0)^2 + (z - z_0)^2 - R^2 = 0

    .. versionadded:: 1.3.0

    .. deprecated:: 1.4.0

       Access this class through ``montepy.GeneralSphere`` instead.

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Submodule access to this class is deprecated. Use montepy.GeneralSphere instead.",
            category=DeprecationWarning,
        )
        super().__init__(*args, **kwargs)
