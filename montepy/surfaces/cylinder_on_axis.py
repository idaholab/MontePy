# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from .surface_type import SurfaceType
from .surface import Surface
from montepy.errors import *
from montepy.utilities import *


def _enforce_positive_radius(self, value):
    if value < 0.0:
        raise ValueError(f"Radius must be positive. {value} given")


class CylinderOnAxis(Surface):
    """
    Represents surfaces: CX, CY, CZ

    :param input: The Input object representing the input
    :type input: Input
    """

    def __init__(self, input=None):
        self._radius = self._generate_default_node(float, None)
        super().__init__(input)
        ST = SurfaceType
        if input:
            if self.surface_type not in [ST.CX, ST.CY, ST.CZ]:
                raise ValueError("CylinderOnAxis must be of surface_type: CX, CY, CZ")
            if len(self.surface_constants) != 1:
                raise ValueError("CylinderOnAxis only accepts one surface_constant")
            self._radius = self._surface_constants[0]
        else:
            self._surface_constants = [self._radius]

    @make_prop_val_node(
        "_radius", (float, int), float, validator=_enforce_positive_radius
    )
    def radius(self):
        """
        The radius of the cylinder

        :rtype: float
        """
        pass

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
