# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
import copy

import montepy
from montepy.data_inputs import transform
from montepy.exceptions import *
from montepy.input_parser.surface_parser import JitSurfParser, SurfaceParser
from montepy.input_parser import syntax_node
from montepy.numbered_mcnp_object import Numbered_MCNP_Object, InitInput
from montepy.surfaces import half_space
from montepy.surfaces.surface_type import SurfaceType
from montepy.utilities import *
import montepy.types as ty


def _surf_type_validator(self, surf_type):
    if surf_type not in self._allowed_surface_types():
        raise ValueError(
            f"{type(self).__name__} must be a surface of type: {[e.value for e in self._allowed_surface_types()]}"
        )


class Surface(Numbered_MCNP_Object):
    """Object to hold a single MCNP surface

    .. versionchanged:: 1.0.0

        Added number parameter

    Parameters
    ----------
    input : Input | str
        The Input object representing the input
    number : int
        The number to set for this object.
    surface_type: SurfaceType | str
        The surface_type to set for this object
    """

    _JitParser = JitSurfParser

    @args_checked
    def __init__(
        self,
        input: InitInput = None,
        number: ty.PositiveInt = None,
        surface_type: SurfaceType | str = None,
        *,
        jit_parse: bool = True,
    ):
        super().__init__(
            input,
            jit_parse=jit_parse,
            number=number,
            surface_type=surface_type,
        )

    @staticmethod
    def _parser():
        return SurfaceParser()

    def _init_blank(self):
        self._CHILD_OBJ_MAP = {
            "periodic_surface": Surface,
            "transform": transform.Transform,
        }
        self._BLOCK_TYPE = montepy.input_parser.block_type.BlockType.SURFACE
        self._periodic_surface = None
        self._old_periodic_surface = self._generate_default_node(int, None)
        self._old_periodic_surface.is_negatable_identifier = True
        self._transform = None
        self._old_transform_number = self._generate_default_node(int, None)
        self._old_transform_number.is_negatable_identifier = True
        self._is_reflecting = False
        self._is_white_boundary = False
        self._surface_constants = []
        self._surface_type = self._generate_default_node(str, None)
        self._modifier = self._generate_default_node(str, None)

    def _parse_tree(self):
        self._number = self._tree["surface_num"]["number"]
        self._number.convert_to_int()
        self._old_number = copy.deepcopy(self._number)
        if "modifier" in self._tree["surface_num"]:
            self._modifier = self._tree["surface_num"]["modifier"]
            if self._modifier.value == "*":
                self._is_reflecting = True
            elif self._number.token and "+" in self._number.token:
                self._is_white_boundary = True
                self._number._token = self._number.token.replace("+", "")
                self._modifier = self._generate_default_node(str, "+", None, True)
                self._tree["surface_num"].nodes["modifier"] = self._modifier
        # parse the parameters
        for entry in self._tree["data"]:
            self._surface_constants.append(entry)
        self._enforce_values()
        self._load_constants()

    def _jit_light_init(self, input: Input):
        super()._jit_light_init(input)
        self._enforce_values()
        return self

    def _enforce_values(self):
        try:
            if self.number is not None:
                assert self.number > 0
        except AssertionError:
            raise MalformedInputError(
                input,
                f"{self._number.value} could not be parsed as a valid surface number.",
            )
        if hasattr(self, "_tree"):
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
            self._surface_type.convert_to_enum(
                SurfaceType, allow_none=True, switch_to_upper=True
            )
        # this should never be reached due to SLY rules.
        # still if it is somehow reached this error is more helpful to the user.
        except ValueError:  # pragma: no cover
            raise MalformedInputError(
                input,
                f"{self._surface_type.value} could not be parsed as a surface type mnemonic.",
            )
        if (
            self.surface_type is not None
            and self.surface_type not in self._allowed_surface_types()
        ):
            raise ValueError(
                f"{type(self).__name__} must be a surface of type: {[e.value for e in self._allowed_surface_types()]}"
            )

    def _load_constants(self):
        pass

    @staticmethod
    def _number_of_params():
        """
        The number of defaults parameters to load into the syntax tree.

        Returns
        -------
        int
        """
        return 1

    @staticmethod
    def _allowed_surface_types():
        """ "
        The allowed surface types for this surface type.

        Returns
        -------
        set[SurfaceType]
        """
        return set(SurfaceType)

    def _generate_default_tree(
        self, number: int = None, surface_type: SurfaceType | str = None
    ):
        """
        Creates a default syntax tree.

        Parameters
        ----------
        number: int
            the default number for the syntax tree, should be passed from __init__
        surface_type: SurfaceType | str
            The surface_type to set for this object

        Other Parameters
        ----------------
        self._number_of_params: int
            the number of surface constants in the default syntax tree.
        """
        data = syntax_node.ListNode("surf list")
        for _ in range(self._number_of_params()):
            data.append(self._generate_default_node(float, None))
        num = self._generate_default_node(int, number)
        num.is_negatable_identifier = True
        pointer = self._generate_default_node(int, None)
        pointer.is_negatable_identifier = True
        if surface_type is not None:
            if isinstance(surface_type, SurfaceType):
                surface_type = surface_type.value
        surf_type = self._generate_default_node(str, surface_type)
        surf_num = syntax_node.SyntaxNode(
            "surf_num",
            {
                "modifier": syntax_node.ValueNode(None, str, never_pad=True),
                "number": num,
            },
        )
        self._tree = syntax_node.SyntaxNode(
            "Surf tree",
            {
                "start_pad": syntax_node.PaddingNode(),
                "surface_num": surf_num,
                "pointer": pointer,
                "surface_type": surf_type,
                "data": data,
            },
        )

    @make_prop_val_node(
        "_surface_type", (SurfaceType, str), SurfaceType, validator=_surf_type_validator
    )
    def surface_type(self):
        """The mnemonic for the type of surface.

        E.g. CY, PX, etc.

        Returns
        -------
        SurfaceType
        """
        pass

    @make_prop_pointer("_is_reflecting", bool)
    @needs_full_tree
    def is_reflecting(self):
        """If true this surface is a reflecting boundary.

        Returns
        -------
        bool
        """
        pass

    @make_prop_pointer("_is_white_boundary", bool)
    @needs_full_tree
    def is_white_boundary(self):
        """If true this surface is a white boundary.

        Returns
        -------
        bool
        """
        pass

    @property
    @needs_full_tree
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
    @args_checked
    @needs_full_tree
    def surface_constants(self, constants: ty.Iterable[ty.Real]):
        if len(constants) != len(self._surface_constants):
            raise ValueError(f"Cannot change the length of the surface constants.")
        for i, value in enumerate(constants):
            self._surface_constants[i].value = value

    @make_prop_val_node("_old_transform_number")
    @needs_full_tree
    def old_transform_number(self):
        """The transformation number for this surface in the original file.

        Returns
        -------
        int
        """
        pass

    @make_prop_val_node("_old_periodic_surface")
    @needs_full_tree
    def old_periodic_surface(self):
        """The surface number this is periodic with reference to in the original file.

        Returns
        -------
        int
        """
        pass

    @prop_pointer_from_problem(
        "_periodic_surface",
        "old_periodic_surface",
        "surfaces",
        types=(),
        deletable=True,
    )
    @needs_full_tree
    def periodic_surface(self):
        """The surface that this surface is periodic with respect to

        Returns
        -------
        Surface
        """
        pass

    @prop_pointer_from_problem(
        "_transform",
        "old_transform_number",
        "tranforms",
        transform.Transform,
        deletable=True,
    )
    @needs_full_tree
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
        boundary = "None"
        if self.is_reflecting:
            boundary = "Reflective"
        elif self.is_white_boundary:
            boundary = "White"
        return (
            f"SURFACE: {self.number}, {self.surface_type}, "
            f"periodic surface: {self.periodic_surface}, "
            f"transform: {self.transform}, "
            f"constants: {self.surface_constants}, "
            f"Boundary: {boundary}"
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
        if self.number is None or self.number < 1:
            raise IllegalState(
                f"Surface: {self.number} does not have a valid number set."
            )
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
        else:
            modifier.value = ""
        if self.transform is not None:
            self._old_transform_number.value = self.transform.number
            self._old_transform_number.is_negative = False
            self._tree.nodes["pointer"] = self._old_transform_number
        elif self.periodic_surface is not None:
            self._old_periodic_surface.value = self.periodic_surface.number
            self._old_periodic_surface.is_negative = True
            self._tree.nodes["pointer"] = self._old_periodic_surface
        else:
            self._tree.nodes["pointer"].value = None

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

    @args_checked
    def find_duplicate_surfaces(
        self, surfaces: montepy.Surfaces, tolerance: ty.PositiveReal
    ):
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
        if not self.number or self.number <= 0:
            raise IllegalState(
                f"Surface number must be set for a surface to be used in a geometry definition."
            )
        return half_space.UnitHalfSpace(self, False, False)

    def __pos__(self):
        if not self.number or self.number <= 0:
            raise IllegalState(
                f"Surface number must be set for a surface to be used in a geometry definition."
            )
        return half_space.UnitHalfSpace(self, True, False)
