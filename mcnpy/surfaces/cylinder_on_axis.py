from .surface_type import SurfaceType
from .surface import Surface
from mcnpy.errors import *
from mcnpy.utilities import *


class CylinderOnAxis(Surface):
    """
    Represents surfaces: CX, CY, CZ

    :param input: The Input object representing the input
    :type input: Input
    :param comments: The Comments that proceeded this card or were inside of this if any
    :type Comments: list
    """

    def __init__(self, input=None, comments=None):
        self._radius = None
        super().__init__(input, comments)
        ST = SurfaceType
        if input:
            if self.surface_type not in [ST.CX, ST.CY, ST.CZ]:
                raise ValueError("CylinderOnAxis must be of surface_type: CX, CY, CZ")
            if len(self.surface_constants) != 1:
                raise ValueError("CylinderOnAxis only accepts one surface_constant")
            self._radius = self.surface_constants[0]
        else:
            self._surface_constants = [None]

    @make_prop_val_node("_radius", (float, int), float)
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
