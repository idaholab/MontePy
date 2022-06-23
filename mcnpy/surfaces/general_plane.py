from mcnpy.surfaces.surface_type import SurfaceType
from mcnpy.surfaces.surface import Surface


class GeneralPlane(Surface):
    """
    Represents P
    """

    def __init__(self, input_card, comment=None):
        super().__init__(input_card, comment)
        if self.surface_type != SurfaceType.P:
            raise ValueError("A GeneralPlane must be a surface of type P")
        if len(self.surface_constants) not in {4, 9}:
            raise ValueError("A GeneralPlane must have either 4 or 9 surface constants")
