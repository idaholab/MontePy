from .surface_type import SurfaceType
from .surface import Surface
from mcnpy.errors import *


class CylinderParAxis(Surface):
    """
    Represents surfaces: C/X, C/Y, C/Z

    :param input_card: The Card object representing the input
    :type input_card: Card
    :param comments: The Comments that proceeded this card or were inside of this if any
    :type Comments: list
    """

    COORDINATE_PAIRS = {
        SurfaceType.C_X: {0: "y", 1: "z"},
        SurfaceType.C_Y: {0: "x", 1: "z"},
        SurfaceType.C_Z: {0: "x", 1: "y"},
    }
    """Which coordinate is what value for each cylinder type.
    """

    def __init__(self, input_card=None, comments=None):
        self._coordinates = None
        self._radius = None
        super().__init__(input_card, comments)
        ST = SurfaceType
        if input_card:
            if self.surface_type not in [ST.C_X, ST.C_Y, ST.C_Z]:
                raise ValueError(
                    "CylinderParAxis must be a surface of types: C/X, C/Y, C/Z"
                )
            if len(self.surface_constants) != 3:
                raise ValueError(
                    "CylinderParAxis must have exactly 3 surface_constants"
                )
            self._coordinates = self.surface_constants[0:2]
            self._radius = self.surface_constants[2]
        else:
            self._surface_constants = [None] * 3

    @property
    def coordinates(self):
        """
        The two coordinates for this cylinder to center on.

        :rytpe: list
        """
        return self._coordinates

    @coordinates.setter
    def coordinates(self, coordinates):
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

    def validate(self):
        super().validate()
        if not self.radius:
            raise IllegalState(f"Surface: {self.number} does not have a radius set.")
        if not self.coordinates:
            raise IllegalState(f"Surface: {self.number} does not have coordinates set.")

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
