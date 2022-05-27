from mcnpy.surfaces.surface_type import SurfaceType
from mcnpy.surfaces.surface import Surface


class GeneralPlane(Surface):
    """
    Represents P
    """

    def __init__(self, input_card, comment=None):
        super().__init__(input_card, comment)
        assert self.surface_type == SurfaceType.P
        assert len(self.surface_constants) in {4, 9}
