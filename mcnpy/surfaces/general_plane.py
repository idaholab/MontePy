from mcnpy.errors import *
from mcnpy.surfaces.surface_type import SurfaceType
from mcnpy.surfaces.surface import Surface


class GeneralPlane(Surface):
    """
    Represents P

    :param input: The Input object representing the input
    :type input: Input
    :param comments: The Comments that proceeded this card or were inside of this if any
    :type Comments: list
    """

    def __init__(self, input=None, comment=None):
        super().__init__(input, comment)
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
