# Copyright 2026, Battelle Energy Alliance, LLC All Rights Reserved.
from .surface_type import SurfaceType
from .surface import Surface, InitInput
from montepy.exceptions import *
from montepy.utilities import *

from typing import Union


def _enforce_positive_radius(self, value):
    if value < 0.0:
        raise ValueError(f"Radius must be positive. {value} given")


class SphereAtOrigin(Surface):
    """Represents surface SO: a sphere at the origin

    ..versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def __init__(
        self,
        input: InitInput = None,
        number: int = None,
    ):
        self._location = self._generate_default_node(float, None)
        self._radius = self._generate_default_node(float, None)
        super().__init__(input, number)
        if len(self.surface_constants) != 1:
            raise ValueError(
                f"{self.__class__.__name__} must have exactly 1 surface_constant"
            )
        self._radius = self._surface_constants[0]

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

    def validate(self):
        super().validate()
        if self.radius is None:  # pragma: no cover
            raise IllegalState(f"Surface: {self.number} does not have a radius set.")

    def find_duplicate_surfaces(self, surfaces, tolerance):
        """Duplicate sphere finding is not yet implemented"""
        return []
