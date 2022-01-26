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
        assert self.surface_type in [ST.PX, ST.PY, ST.PZ]
        assert len(self.surface_constants) == 1
        self.__location = self.surface_constants[0]

    @property
    def location(self):
        """
        The location of the plane in space.

        :rtype: float
        """
        return self.__location

    @location.setter
    def location(self, location):
        assert isinstance(location, float)
        self.__location = location
        self._Surface__surface_constants[0] = location

    def find_duplicate_surfaces(self, surfaces, tolerance):
        ret = []
        # do not assume transform and periodic surfaces are the same.
        if not self.old_periodic_surface:
            for surface in surfaces:
                if surface != self and surface.surface_type == self.surface_type:
                    if not self.old_periodic_surface:
                        if abs(self.location - surface.location) < tolerance:
                            if self.old_transform_number:
                                if surface.old_transform_number:
                                    if self.transform.equivalent(surface.transform):
                                        ret.append(surface)
                            else:
                                ret.append(surface)
            return ret
        else:
            return []
