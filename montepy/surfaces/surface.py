# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
import copy
from typing import Union
from numbers import Real

import montepy
from montepy.errors import *
from montepy.data_inputs import transform
from montepy.input_parser.surface_parser import SurfaceParser
from montepy.numbered_mcnp_object import Numbered_MCNP_Object, InitInput
from montepy.surfaces import half_space
from montepy.surfaces.surface_type import SurfaceType
from montepy.utilities import *


class Surface(Numbered_MCNP_Object):
    """Object to hold a single MCNP surface

    .. versionchanged:: 1.0.0

        Added number parameter

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    _parser = SurfaceParser()

    def __init__(
        self,
        input: InitInput = None,
        number: int = None,
    ):
        self._CHILD_OBJ_MAP = {
            "periodic_surface": Surface,
            "transform": transform.Transform,
        }
        self._BLOCK_TYPE = montepy.input_parser.block_type.BlockType.SURFACE
        self._number = self._generate_default_node(int, -1)
        super().__init__(input, self._parser, number)
        self._periodic_surface = None
        self._old_periodic_surface = self._generate_default_node(int, None)
        self._transform = None
        self._old_transform_number = self._generate_default_node(int, None)
        self._is_reflecting = False
        self._is_white_boundary = False
        self._surface_constants = []
        self._surface_type = self._generate_default_node(str, None)
        self._modifier = self._generate_default_node(str, None)
        # surface number
        if input:
            self._number = self._tree["surface_num"]["number"]
            self._number._convert_to_int()
            self._old_number = copy.deepcopy(self._number)
            if "modifier" in self._tree["surface_num"]:
                self._modifier = self._tree["surface_num"]["modifier"]
                if self._modifier.value == "*":
                    self._is_reflecting = True
                elif "+" in self._number.token:
                    self._is_white_boundary = True
                    self._number._token = self._number.token.replace("+", "")
                    self._modifier = self._generate_default_node(str, "+", None)
                    self._tree["surface_num"].nodes["modifier"] = self._modifier
            try:
                assert self._number.value > 0
            except AssertionError:
                raise MalformedInputError(
                    input,
                    f"{self._number.value} could not be parsed as a valid surface number.",
                )
            if self._tree["pointer"].value is not None:
                val = self._tree["pointer"]
                val.is_negatable_identifier = True
                if val.is_negative:
                    self._old_periodic_surface = val
                else:
                    self._old_transform_number = val
            self._surface_type = self._tree["surface_type"]
            # parse surface mnemonic
            try:
                # enforce enums
                self._surface_type._convert_to_enum(SurfaceType, switch_to_upper=True)
            # this should never be reached due to SLY rules.
            # still if it is somehow reached this error is more helpful to the user.
            except ValueError:  # pragma: no cover
                raise MalformedInputError(
                    input,
                    f"{self._surface_type.value} could not be parsed as a surface type mnemonic.",
                )
            # parse the parameters
            for entry in self._tree["data"]:
                self._surface_constants.append(entry)

    @make_prop_val_node("_surface_type", (SurfaceType, str), SurfaceType)
    def surface_type(self):
        """The mnemonic for the type of surface.

        E.g. CY, PX, etc.

        Returns
        -------
        SurfaceType
        """
        pass

    @property
    def is_reflecting(self):
        """If true this surface is a reflecting boundary.

        Returns
        -------
        bool
        """
        return self._is_reflecting

    @is_reflecting.setter
    def is_reflecting(self, reflect):
        if not isinstance(reflect, bool):
            raise TypeError("is_reflecting must be set to a bool")
        self._is_reflecting = reflect

    @property
    def is_white_boundary(self):
        """If true this surface is a white boundary.

        Returns
        -------
        bool
        """
        return self._is_white_boundary

    @is_white_boundary.setter
    def is_white_boundary(self, white):
        if not isinstance(white, bool):
            raise TypeError("is_white_boundary must be set to a bool")
        self._is_white_boundary = white

    @property
    def surface_constants(self):
        """The constants defining the surface

        Returns
        -------
        list
        """
        ret = []
        for val in self._surface_constants:
            ret.append(val.value)
        return ret

    @surface_constants.setter
    def surface_constants(self, constants):
        if not isinstance(constants, list):
            raise TypeError("surface_constants must be a list")
        if len(constants) != len(self._surface_constants):
            raise ValueError(f"Cannot change the length of the surface constants.")
        for constant in constants:
            if not isinstance(constant, Real):
                raise TypeError(
                    f"The surface constant provided: {constant} must be a float"
                )
        for i, value in enumerate(constants):
            self._surface_constants[i].value = value

    @make_prop_val_node("_old_transform_number")
    def old_transform_number(self):
        """The transformation number for this surface in the original file.

        Returns
        -------
        int
        """
        pass

    @make_prop_val_node("_old_periodic_surface")
    def old_periodic_surface(self):
        """The surface number this is periodic with reference to in the original file.

        Returns
        -------
        int
        """
        pass

    @make_prop_pointer("_periodic_surface", types=(), deletable=True)
    def periodic_surface(self):
        """The surface that this surface is periodic with respect to

        Returns
        -------
        Surface
        """
        pass

    @make_prop_pointer("_transform", transform.Transform, deletable=True)
    def transform(self):
        """The Transform object that translates this surface

        Returns
        -------
        Transform
        """
        pass

    @make_prop_val_node("_old_number")
    def old_number(self):
        """The surface number that was used in the read file

        Returns
        -------
        int
        """
        pass

    @property
    def cells(self):
        """A generator of Cells that use this surface.

        Returns
        -------
        generator
        """
        if self._problem:
            for cell in self._problem.cells:
                if self in cell.surfaces:
                    yield cell

    def __str__(self):
        return f"SURFACE: {self.number}, {self.surface_type}"

    def __repr__(self):
        return (
            f"SURFACE: {self.number}, {self.surface_type}, "
            f"periodic surface: {self.periodic_surface}, "
            f"transform: {self.transform}, "
            f"constants: {self.surface_constants}"
        )

    def update_pointers(self, surfaces, data_inputs):
        """Updates the internal pointers to the appropriate objects.

        Right now only periodic surface links will be made.
        Eventually transform pointers should be made.

        Parameters
        ----------
        surfaces : Surfaces
            A Surfaces collection of the surfaces in the problem.
        data_cards : list
            the data_cards in the problem.
        """
        if self.old_periodic_surface:
            try:
                self._periodic_surface = surfaces[self.old_periodic_surface]
            except KeyError:
                raise BrokenObjectLinkError(
                    "Surface",
                    self.number,
                    "Periodic Surface",
                    self.old_periodic_surface,
                )
        if self.old_transform_number:
            for input in data_inputs:
                if isinstance(input, transform.Transform):
                    if input.number == self.old_transform_number:
                        self._transform = input
            if not self.transform:
                raise BrokenObjectLinkError(
                    "Surface",
                    self.number,
                    "Transform",
                    self.old_transform_number,
                )

    def validate(self):
        if self.surface_type is None:
            raise IllegalState(
                f"Surface: {self.number} does not have a surface type set."
            )

    def _update_values(self):
        modifier = self._tree["surface_num"]["modifier"]
        if self.is_reflecting:
            modifier.value = "*"
        elif self.is_white_boundary:
            modifier.value = "+"
        if self.transform is not None:
            self._old_transform_number.value = self.transform.number
            self._old_transform_number.is_negative = False
            self._tree.nodes["pointer"] = self._old_transform_number
        elif self.periodic_surface is not None:
            self._old_periodic_surface.value = self.periodic_surface.number
            self._old_periodic_surface.is_negative = True
            self._tree.nodes["pointer"] = self._old_periodic_surface

    def __lt__(self, other):
        return self.number < other.number

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return (
            self.number == other.number
            and self.surface_type == other.surface_type
            and self.is_reflecting == other.is_reflecting
            and self.is_white_boundary == other.is_white_boundary
            and self.surface_constants == other.surface_constants
        )

    def __ne__(self, other):
        return not self == other

    def find_duplicate_surfaces(self, surfaces, tolerance):
        """Finds all surfaces that are effectively the same as this one.

        Parameters
        ----------
        surfaces : list
            a list of the surfaces to compare against this one.
        tolerance : float
            the amount of relative error to allow

        Returns
        -------
        list
            A list of the surfaces that are identical
        """
        return []

    def __neg__(self):
        if self.number <= 0:
            raise IllegalState(
                f"Surface number must be set for a surface to be used in a geometry definition."
            )
        return half_space.UnitHalfSpace(self, False, False)

    def __pos__(self):
        if self.number <= 0:
            raise IllegalState(
                f"Surface number must be set for a surface to be used in a geometry definition."
            )
        return half_space.UnitHalfSpace(self, True, False)
