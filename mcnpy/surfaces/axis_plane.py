from .surface_type import SurfaceType
from .surface import Surface


class AxisPlane(Surface):
    """
    Represents PX, PY, PZ
    """

    COORDINATE = {SurfaceType.PX: "x", SurfaceType.PY: "y", SurfaceType.PZ: "z"}

    def __init__(self, input_card, comment=None):
        """
        :param input_card: The Card object representing the input
        :type input_card: Card
        :param comment: the Comment object representing the
                        preceding comment block.
        :type comment: Comment
        """
        super().__init__(input_card, comment)
        ST = SurfaceType
        if self.surface_type not in [ST.PX, ST.PY, ST.PZ]:
            raise ValueError("AxisPlane must be a surface of type: PX, PY, or PZ")
        if len(self.surface_constants) != 1:
            raise ValueError("AxisPlane must have exactly 1 surface constant")
        self._location = self.surface_constants[0]

    @property
    def location(self):
        """
        The location of the plane in space.

        :rtype: float
        """
        return self._location

    @location.setter
    def location(self, location):
        if not isinstance(location, float):
            raise TypeError("location must be a float")
        self._mutated = True
        self._location = location
        self._surface_constants[0] = location

    def find_duplicate_surfaces(self, surfaces, tolerance):
        ret = []
        # do not assume transform and periodic surfaces are the same.
        if not self.old_periodic_surface:
            for surface in surfaces:
                if surface != self and surface.surface_type == self.surface_type:
                    if not self.old_periodic_surface:
                        if abs(self.location - surface.location) < tolerance:
                            if self.transform:
                                if surface.transform:
                                    if self.transform.equivalent(
                                        surface.transform, tolerance
                                    ):
                                        ret.append(surface)
                            else:
                                if surface.transform is None:
                                    ret.append(surface)
            return ret
        else:
            return []
