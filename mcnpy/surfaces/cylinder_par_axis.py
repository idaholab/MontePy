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

    def __init__(self, input, comment=None):
        """
        :param input: The Input object representing the input
        :type input: Input
        :param comment: the Comment object representing the
                        preceding comment block.
        :type comment: Comment
        """
        super().__init__(input, comment)
        ST = SurfaceType
        if self.surface_type not in [ST.C_X, ST.C_Y, ST.C_Z]:
            raise ValueError(
                "CylinderParAxis must be a surface of types: C/X, C/Y, C/Z"
            )
        if len(self.surface_constants) != 3:
            raise ValueError("CylinderParAxis must have exactly 3 surface_constants")
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
        if not isinstance(coordinates, list):
            raise TypeError("coordinates must be a list")
        if len(coordinates) != 2:
            raise ValueError("coordinates must have exactly two elements")
        self._mutated = True
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
        if not isinstance(radius, float):
            raise TypeError("radius must be a float")
        if radius <= 0.0:
            raise ValueError("radius must be greater than 0")
        self._mutated = True
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
