# Copyright 2026, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations

import montepy
from .surface_type import SurfaceType
from .surface import Surface, InitInput
from montepy.exceptions import *
from montepy.utilities import *
import montepy.types as ty


def _enforce_positive_radius(self, value):
    if value < 0.0:
        raise ValueError(f"Radius must be positive. {value} given")


class SphereOnAxis(Surface):
    """Represents surfaces SX, SY, and SZ: spheres on axes

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    surface_type: Union[SurfaceType, str]
        The surface_type to set for this object
    """

    COORDINATE = {SurfaceType.SX: "x", SurfaceType.SY: "y", SurfaceType.SZ: "z"}

    @args_checked
    def __init__(
        self,
        input: InitInput = None,
        number: ty.PositiveInt = None,
        surface_type: SurfaceType | str = None,
    ):
        self._location = self._generate_default_node(float, None)
        self._radius = self._generate_default_node(float, None)
        super().__init__(input, number, surface_type)
        if len(self.surface_constants) != 2:
            raise ValueError(
                f"{self.__class__.__name__} must have exactly 2 surface_constants"
            )
        self._location, self._radius = self._surface_constants

    @staticmethod
    def _number_of_params():
        return 2

    @make_prop_val_node(
        "_radius", (float, int), float, validator=_enforce_positive_radius
    )
    def radius(self):
        """The radius of the sphere

        Returns
        -------
        float
        """
        pass

    @make_prop_val_node("_location", (float, int), float)
    def location(self):
        """The location of the center of the sphere in space

        Returns
        -------
        float
        """
        pass

    @staticmethod
    def _allowed_surface_types():
        return {SurfaceType.SX, SurfaceType.SY, SurfaceType.SZ}

    def validate(self):
        super().validate()
        if self.radius is None:
            raise IllegalState(f"Surface: {self.number} does not have a radius set.")
        if self.location is None:
            raise IllegalState(f"Surface: {self.number} does not have a location set.")

    @args_checked
    def find_duplicate_surfaces(
        self, surfaces: montepy.Surfaces, tolerance: ty.PositiveReal
    ):  # pragma: no cover
        """Duplicate sphere finding is not yet implemented"""
        return []
