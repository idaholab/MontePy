# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.

from .surface_type import SurfaceType
from .surface import Surface, InitInput
from montepy.errors import *
from montepy.utilities import *

from typing import Union


class AxisPlane(Surface):
    """Represents PX, PY, PZ

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

    COORDINATE = {SurfaceType.PX: "x", SurfaceType.PY: "y", SurfaceType.PZ: "z"}

    def __init__(
        self,
        input: InitInput = None,
        number: int = None,
        surface_type: Union[SurfaceType, str] = None,
    ):
        self._location = self._generate_default_node(float, None)
        super().__init__(input, number, surface_type)
        if len(self.surface_constants) != 1:
            raise ValueError("AxisPlane must have exactly 1 surface constant")
        self._location = self._surface_constants[0]

    @make_prop_val_node("_location", (float, int), float)
    def location(self):
        """The location of the plane in space.

        Returns
        -------
        float
        """
        pass

    @staticmethod
    def _allowed_surface_types():
        return {SurfaceType.PX, SurfaceType.PY, SurfaceType.PZ}

    def validate(self):
        super().validate()
        if self.location is None:
            raise IllegalState(f"Surface: {self.number} does not have a location set.")

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
