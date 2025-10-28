# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations

import montepy
from .surface import Surface, InitInput
from .surface_type import SurfaceType
from montepy.exceptions import *
import montepy.types as ty
from montepy.utilities import *


def _enforce_positive_radius(self, value):
    if value < 0.0:
        raise ValueError(f"Radius must be positive. {value} given")


class CylinderParAxis(Surface):
    """Represents surfaces: C/X, C/Y, C/Z

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

    COORDINATE_PAIRS = {
        SurfaceType.C_X: {0: "y", 1: "z"},
        SurfaceType.C_Y: {0: "x", 1: "z"},
        SurfaceType.C_Z: {0: "x", 1: "y"},
    }
    """Which coordinate is what value for each cylinder type."""

    @args_checked
    def __init__(
        self,
        input: InitInput = None,
        number: ty.PositiveInt = None,
        surface_type: SurfaceType | str = None,
    ):
        self._coordinates = [
            self._generate_default_node(float, None),
            self._generate_default_node(float, None),
        ]
        self._radius = self._generate_default_node(float, None)
        super().__init__(input, number, surface_type)
        if len(self.surface_constants) != 3:
            raise ValueError("CylinderParAxis must have exactly 3 surface_constants")
        self._coordinates = self._surface_constants[0:2]
        self._radius = self._surface_constants[2]

    @staticmethod
    def _number_of_params():
        return 3

    @staticmethod
    def _allowed_surface_types():
        return {SurfaceType.C_X, SurfaceType.C_Y, SurfaceType.C_Z}

    @property
    def coordinates(self):
        """The two coordinates for this cylinder to center on.

        :rytpe: tuple
        """
        return (self._coordinates[0].value, self._coordinates[1].value)

    @coordinates.setter
    @args_checked
    def coordinates(self, coordinates: ty.Iterable[ty.Real]):
        if len(coordinates) != 2:
            raise ValueError("coordinates must have exactly two elements")
        for i, val in enumerate(coordinates):
            self._coordinates[i].value = val

    @make_prop_val_node(
        "_radius", (ty.Real,), float, validator=_enforce_positive_radius
    )
    def radius(self):
        """The radius of the cylinder.

        Returns
        -------
        float
        """
        pass

    def validate(self):
        super().validate()
        if self.radius is None:
            raise IllegalState(f"Surface: {self.number} does not have a radius set.")
        if any({c is None for c in self.coordinates}):
            raise IllegalState(f"Surface: {self.number} does not have coordinates set.")

    @args_checked
    def find_duplicate_surfaces(
        self, surfaces: montepy.Surfaces, tolerance: ty.PositiveReal
    ):
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
