from .surface_type import SurfaceType
from .surface import Surface


class CylinderParAxis(Surface):
    """
    Represents surfaces: C/X, C/Y, C/Z
    """

    COORDINATE_PAIRS = {
        SurfaceType.C_X: {0: "y", 1: "z"},
        SurfaceType.C_Y: {0: "x", 1: "z"},
        SurfaceType.C_Z: {0: "x", 1: "y"},
    }

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
        assert self.surface_type in [ST.C_X, ST.C_Y, ST.C_Z]
        assert len(self.surface_constants) == 3
        self._coordinates = self.surface_constants[0:2]
        self._radius = self.surface_constants[2]

    @property
    def coordinates(self):
        """
        The two coordinates for this cylinder to center on.

        :rytpe: list
        """
        return self._coordinates

    @coordinates.setter
    def coordinates(self, coordinates):
        """
        :param coordinates: the coordinates, must be 2 long.
        """
        assert len(coordinates) == 2
        self._coordinates = coordinates
        self._surface_constants[0:2] = coordinates

    @property
    def radius(self):
        """
        The radius of the cylinder.

        :rtype: float
        """
        return self._radius

    @radius.setter
    def radius(self, radius):
        assert isinstance(radius, float)
        assert radius > 0
        self._radius = radius
        self._surface_constants[2] = radius

    def find_duplicate_surfaces(self, surfaces, tolerance):
        ret = []
        # do not assume transform and periodic surfaces are the same.
        if not self.old_periodic_surface:
            for surface in surfaces:
                if surface != self and surface.surface_type == self.surface_type:
                    if not self.old_periodic_surface:
                        match = True
                        if abs(self.radius - surface.radius) >= tolerance:
                            match = False
                        for i, coordinate in enumerate(self.coordinates):
                            if abs(coordinate - surface.coordinates[i]) >= tolerance:
                                match = False
                        if match:
                            if self.old_transform_number:
                                if surface.old_transform_number:
                                    if self.transform.equivalent(
                                        surface.transform, tolerance
                                    ):
                                        ret.append(surface)
                            else:
                                ret.append(surface)
            return ret
        else:
            return []
