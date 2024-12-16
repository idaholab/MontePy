# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from typing import Union

import montepy
from montepy.errors import *
from montepy.surfaces.surface_type import SurfaceType
from montepy.surfaces.surface import Surface, InitInput


class GeneralPlane(Surface):
    """
    Represents P

    .. versionchanged:: 1.0.0

        Added number parameter

    :param input: The Input object representing the input
    :type input: Input
    :param input: The Input object representing the input
    :type input: Union[Input, str]
    :param number: The number to set for this object.
    :type number: int
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
            if len(self.surface_constants) not in {4, 9}:
                raise ValueError(
                    "A GeneralPlane must have either 4 or 9 surface constants"
                )

    def validate(self):
        super().validate()
        if len(self.surface_constants) not in {4, 9}:
            raise IllegalState(
                f"Surface: {self.number} does not have constants set properly."
            )
