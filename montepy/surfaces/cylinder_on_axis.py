# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from .surface_type import SurfaceType
from .surface import Surface
from montepy.errors import *


class CylinderOnAxis(Surface):
    """
    Represents surfaces: CX, CY, CZ

    :param input_card: The Card object representing the input
    :type input_card: Card
    :param comments: The Comments that proceeded this card or were inside of this if any
    :type Comments: list
    """

    def __init__(self, input_card=None, comments=None):
        self._radius = None
        super().__init__(input_card, comments)
        ST = SurfaceType
        if input_card:
            if self.surface_type not in [ST.CX, ST.CY, ST.CZ]:
                raise ValueError("CylinderOnAxis must be of surface_type: CX, CY, CZ")
            if len(self.surface_constants) != 1:
                raise ValueError("CylinderOnAxis only accepts one surface_constant")
            self._radius = self.surface_constants[0]
        else:
            self._surface_constants = [None]

    @property
    def radius(self):
        """
        The radius of the cylinder

        :rtype: float
        """
        return self._radius

    @radius.setter
    def radius(self, radius):
        if not isinstance(radius, float):
            raise TypeError("radius must be a float")
        if radius <= 0.0:
            raise ValueError("radius must be larger than 0")
        self._mutated = True
        self._radius = radius

    def validate(self):
        super().validate()
        if not self.radius:
            raise IllegalState(f"Surface: {self.number} does not have a radius set.")

    def find_duplicate_surfaces(self, surfaces, tolerance):
        ret = []
        # do not assume transform and periodic surfaces are the same.
        if not self.old_periodic_surface:
            for surface in surfaces:
                if surface != self and surface.surface_type == self.surface_type:
                    if not surface.old_periodic_surface:
                        if abs(self.radius - surface.radius) < tolerance:
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
