# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.errors import *
from montepy.surfaces.surface_type import SurfaceType
from montepy.surfaces.surface import Surface


class GeneralPlane(Surface):
    """
    Represents P

    :param input_card: The Card object representing the input
    :type input_card: Card
    :param comments: The Comments that proceeded this card or were inside of this if any
    :type Comments: list
    """

    def __init__(self, input_card=None, comments=None):
        super().__init__(input_card, comments)
        if input_card:
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
