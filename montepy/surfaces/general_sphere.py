# Copyright 2026, Battelle Energy Alliance, LLC All Rights Reserved.
from .surface_type import SurfaceType
from .surface import Surface, InitInput
from montepy.exceptions import *
from montepy.utilities import *

from numbers import Real
from typing import Union


def _enforce_positive_radius(self, value):
    if value < 0.0:
        raise ValueError(f"Radius must be positive. {value} given")


class GeneralSphere(Surface):
    """Represents surface S: a general sphere

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
        self._coordinates = [
            self._generate_default_node(float, None),
            self._generate_default_node(float, None),
            self._generate_default_node(float, None),
        ]
        self._radius = self._generate_default_node(float, None)
        super().__init__(input, number)
        if input and self.surface_type != SurfaceType.S:
            raise ValueError(f"A {self.__class__.__name__} must be a surface of type S")
        if len(self.surface_constants) != 4:
            raise ValueError(
                f"A {self.__class__.__name__} must have exactly 4 surface_constants"
            )
        self._coordinates = self._surface_constants[:3]
        self._radius = self._surface_constants[3]

    @staticmethod
    def _number_of_params():
        return 4

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

    @property
    def coordinates(self):
        """The three coordinates for the sphere center

        :rytpe: tuple
        """
        return tuple(c.value for c in self._coordinates)

    @coordinates.setter
    def coordinates(self, coordinates):
        if not isinstance(coordinates, (list, tuple)):
            raise TypeError("coordinates must be a list")
        if len(coordinates) != 3:
            raise ValueError("coordinates must have exactly three elements")
        for val in coordinates:
            if not isinstance(val, Real):
                raise TypeError(f"Coordinate must be a number. {val} given.")
        for i, val in enumerate(coordinates):
            self._coordinates[i].value = val

    def validate(self):
        super().validate()
        if self.radius is None:
            raise IllegalState(f"Surface: {self.number} does not have a radius set.")
        if any({c is None for c in self.coordinates}):
            raise IllegalState(f"Surface: {self.number} does not have coordinates set.")

    def find_duplicate_surfaces(self, surfaces, tolerance):
        """Duplicate sphere finding is not yet implemented"""
        return []
