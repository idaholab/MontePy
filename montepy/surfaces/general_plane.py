# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from typing import Union
import warnings

import montepy
from montepy.errors import *
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
            if len(self.surface_constants)>9:
                warnings.warn(f"There were {len(self.surface_constants)} constants. A GeneralPlane must have either 4 or 9 surface constants. MontePy will ignore extra constants provided.")
                super().__init__(input, number, max_constants=9)
            elif len(self.surface_constants) not in {4, 9}:
                raise ValueError(
                    "A GeneralPlane must have either 4 or 9 surface constants"
                )

    def validate(self):
        super().validate()
        if len(self.surface_constants) not in {4, 9}:
            raise IllegalState(
                f"Surface: {self.number} does not have constants set properly."
            )
