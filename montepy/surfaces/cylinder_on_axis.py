# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from .surface_type import SurfaceType
from .surface import Surface, InitInput
from montepy.exceptions import *
from montepy.utilities import *

from typing import Union


def _enforce_positive_radius(self, value):
    if value < 0.0:
        raise ValueError(f"Radius must be positive. {value} given")


class CylinderOnAxis(Surface):
    """Represents surfaces: CX, CY, CZ

    .. versionchanged:: 1.0.0

        Added number parameter

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    surface_type: Union[SurfaceType, str]
        The surface_type to set for this object
    """

    def _load_constants(self):
        if len(self.surface_constants) != 1:
            raise ValueError("CylinderOnAxis only accepts one surface_constant")
        self._radius = self._surface_constants[0]

    @make_prop_val_node(
        "_radius", (float, int), float, validator=_enforce_positive_radius
    )
    def radius(self):
        """The radius of the cylinder

        Returns
        -------
        float
        """
        pass

    @staticmethod
    def _allowed_surface_types():
        return {SurfaceType.CX, SurfaceType.CY, SurfaceType.CZ}

    def validate(self):
        super().validate()
        if self.radius is None:
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
