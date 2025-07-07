# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from typing import Union
import warnings

import montepy
from montepy.exceptions import *
from montepy.surfaces.surface_type import SurfaceType
from montepy.surfaces.surface import Surface, InitInput


class GeneralPlane(Surface):
    """Represents P

    .. versionchanged:: 1.0.0

        Added number parameter

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def __init__(
        self,
        input: InitInput = None,
        number: int = None,
    ):
        super().__init__(input, number)
        if input:
            if self.surface_type != SurfaceType.P:
                raise ValueError("A GeneralPlane must be a surface of type P")
            self._enforce_constants()

    def validate(self):
        super().validate()
        self._enforce_constants(_validation_call=True)

    def _enforce_constants(self, _validation_call=False):
        if len(self.surface_constants) not in {4, 9}:
            message = f"A GeneralPlane must have either 4 or 9 surface constants. {len(self.surface_constants)} constants are provided."
            if len(self.surface_constants) < 9:
                if not _validation_call:
                    raise ValueError(message)
                else:
                    raise IllegalState(message)
            else:
                warnings.warn(message, SurfaceConstantsWarning)
