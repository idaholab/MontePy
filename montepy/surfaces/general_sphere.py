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


class GeneralSphere(Surface):
    """Represents surface S: a general sphere

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def _load_constants(self):
        if len(self.surface_constants) != 4:
            raise ValueError(
                f"A {self.__class__.__name__} must have exactly 4 surface_constants"
            )
        self._coordinates = self._surface_constants[:3]
        self._radius = self._surface_constants[3]

    @staticmethod
    def _allowed_surface_types():
        return {SurfaceType.S}

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
    @needs_full_ast
    def coordinates(self):
        """The three coordinates for the sphere center

        :rytpe: tuple
        """
        return tuple(c.value for c in self._coordinates)

    @coordinates.setter
    @needs_full_cst
    @args_checked
    def coordinates(self, coordinates: ty.Iterable[ty.Real]):
        if len(coordinates) != 3:
            raise ValueError("coordinates must have exactly three elements")
        for i, val in enumerate(coordinates):
            self._coordinates[i].value = val

    def validate(self):
        super().validate()
        if self.radius is None:
            raise IllegalState(f"Surface: {self.number} does not have a radius set.")
        if any({c is None for c in self.coordinates}):
            raise IllegalState(f"Surface: {self.number} does not have coordinates set.")

    @args_checked
    def find_duplicate_surfaces(
        self, surfaces: montepy.Surfaces, tolerance: ty.PositiveReal
    ):  # pragma: no cover
        """Duplicate sphere finding is not yet implemented"""
        return []
