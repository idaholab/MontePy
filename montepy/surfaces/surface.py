# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
import copy
from collections.abc import Callable
from dataclasses import asdict, dataclass
import math
from typing import Union
from numbers import Real
import warnings

import numpy as np
import montepy
from montepy.input_parser import syntax_node
from montepy.exceptions import *
from montepy.data_inputs import transform
from montepy.input_parser.surface_parser import SurfaceParser
from montepy.mcnp_object import _ExceptionContextAdder
from montepy.numbered_mcnp_object import Numbered_MCNP_Object, InitInput
from montepy.surfaces import half_space
from montepy.surfaces.surface_type import SurfaceType
from montepy.utilities import *


def _surf_type_validator(self, surf_type):
    if surf_type not in self._allowed_surface_types():
        raise ValueError(
            f"{type(self).__name__} must be a surface of type: {[e.value for e in self._allowed_surface_types()]}"
        )


@dataclass
class _SurfaceParamSpec:
    name: str
    start_idx: int
    description: str
    types: tuple[type, ...]
    is_tuple: bool = False
    base_type: type = None
    tuple_length: int = 1
    validator: Callable = None


@dataclass
class _ParamLoader:
    attr_name: str
    is_tuple: bool
    start_idx: int
    tuple_length: int = 1


@dataclass
class _SurfaceTypeSpec:
    surface_types: Set[SurfaceType]
    num_param_values: int
    params: list[_SurfaceParamSpec]
    equation: Callable = None


class _SurfaceClassFactory(_ExceptionContextAdder):
    def __new__(cls, name, bases, namespace, spec: SurfaceTypeSpec = None, **kwargs):
        if spec is None:
            return super().__new__(cls, name, bases, namespace, **kwargs)
        param_loaders = []
        _SurfaceClassFactory.build_params_props(namespace, spec, param_loaders)
        namespace["_PARAM_LOADERS"] = param_loaders
        namespace["_NUM_PARAMS"] = spec.num_param_values
        namespace["_ALLOWED_SURFACE_TYPES"] = spec.surface_types
        return super().__new__(cls, name, bases, namespace, **kwargs)

    @classmethod
    def build_params_props(metaclass, namespace, spec, param_loaders):
        for param in spec.params:
            param_loaders.append(
                _ParamLoader(
                    f"_{param.name}",
                    param.is_tuple,
                    param.start_idx,
                    param.tuple_length,
                )
            )
            if param.is_tuple:
                namespace[param.name] = metaclass.build_tuple_prop(param)
            else:
                namespace[param.name] = metaclass.build_scalar_prop(param)

    @classmethod
    def build_tuple_prop(metacls, param):
        attr_name = f"_{param.name}"
        base_func = metacls.gen_tuple_getter(attr_name)
        base_func.__name__ = param.name
        base_func.__doc__ = base_func.__doc__.format(**asdict(param))
        setter = metacls.gen_tuple_setter(
            attr_name,
            param.tuple_length,
            param.name,
            param.types,
            param.base_type,
            param.validator,
        )
        return property(base_func, setter)

    @classmethod
    def build_scalar_prop(metacls, param):
        base_func = copy.deepcopy(metacls.dummy_function)
        base_func.__name__ = param.name
        base_func.__doc__ = base_func.__doc__.format(**asdict(param))
        return make_prop_val_node(
            f"_{param.name}", param.types, param.base_type, param.validator
        )(base_func)

    def dummy_function(self) -> float:
        """
        {description}

        Returns
        -------
        float
        """

    @classmethod
    def gen_tuple_getter(meta_class, hidden_param):
        def dummy_tuple_function(self) -> float:
            """
            {description}

            Returns
            -------
            tuple[{{", ".join(["float"] * tuple_length)}}]
            """
            data = getattr(self, hidden_param)
            return tuple(x.value for x in data)

        return dummy_tuple_function

    @classmethod
    def gen_tuple_setter(
        meta_class, hidden_param, length, name, types, base_type, validator
    ):
        # singular element name: strip trailing 's' if the tuple name ends in one
        elem_name = name[:-1] if name.endswith("s") else name

        def dummy_tuple_setter(self, vals):
            if not isinstance(vals, (list, tuple)):
                raise TypeError(f"{name} must be a list or tuple")
            if len(vals) != length:
                raise ValueError(f"{name} must have exactly {length} elements")
            converted = []
            for val in vals:
                if types and not isinstance(val, (*types, Real)):
                    raise TypeError(f"{elem_name} must be a number. {val} given.")
                if base_type is not None:
                    val = base_type(val)
                if validator is not None:
                    validator(self, val)
                converted.append(val)
            for in_val, storage in zip(converted, getattr(self, hidden_param)):
                storage.value = in_val

        return dummy_tuple_setter


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
    surface_type: Union[SurfaceType, str]
        The surface_type to set for this object
    """

    _parser = SurfaceParser()
    _PARAM_LOADERS: list = []
    _NUM_PARAMS: int = 0
    _ALLOWED_SURFACE_TYPES: set = None
    _VARIABLE_NUM_PARAMS: bool = False

    def __init__(
        self,
        input: InitInput = None,
        number: int = None,
        surface_type: Union[SurfaceType, str] = None,
    ):
        self._CHILD_OBJ_MAP = {
            "periodic_surface": Surface,
            "transform": transform.Transform,
        }
        self._BLOCK_TYPE = montepy.input_parser.block_type.BlockType.SURFACE
        super().__init__(input, self._parser, number)
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
        if not input:
            self._generate_default_tree(number, surface_type)
        # surface number
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
        try:
            if input:
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
        # parse the parameters
        for entry in self._tree["data"]:
            self._surface_constants.append(entry)
        if (
            type(self) != Surface
            and not self._VARIABLE_NUM_PARAMS
            and len(self._surface_constants) != self._number_of_params()
        ):
            raise ValueError(
                f"{type(self).__name__} must be given {self._number_of_params()} surface constants, but {len(self._surface_constants)} were given"
            )
        self._load_params()

    def _load_params(self):
        for param_loader in self._PARAM_LOADERS:
            data = self._surface_constants[
                param_loader.start_idx : param_loader.start_idx
                + param_loader.tuple_length
            ]
            if param_loader.is_tuple:
                data = tuple(data)
            else:
                data = data[0]
            setattr(self, param_loader.attr_name, data)

    @classmethod
    def _number_of_params(cls):
        """
        The number of defaults parameters to load into the syntax tree.

        Returns
        -------
        int
        """
        return cls._NUM_PARAMS

    @classmethod
    def _allowed_surface_types(cls):
        """ "
        The allowed surface types for this surface type.

        Returns
        -------
        set[SurfaceType]
        """
        if cls._ALLOWED_SURFACE_TYPES is None:
            return set(SurfaceType)
        return cls._ALLOWED_SURFACE_TYPES

    def _generate_default_tree(
        self, number: int = None, surface_type: Union[SurfaceType, str] = None
    ):
        """
        Creates a default syntax tree.

        Parameters
        ----------
        number: int
            the default number for the syntax tree, should be passed from __init__
        surface_type: Union[SurfaceType, str]
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
            if not isinstance(surface_type, (SurfaceType, str)):
                raise TypeError(f"The surface_type must be of type: SurfaceType or str")
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
        if self.old_periodic_surface:
            return []
        ret = []
        # do not assume transform and periodic surfaces are the same.
        for surface in surfaces:
            if surface == self or surface.surface_type != self.surface_type:
                continue
            if surface.old_periodic_surface:
                continue
            if (self.transform is None) != (surface.transform is None):
                continue
            if self.transform and not self.transform.equivalent(
                surface.transform, tolerance
            ):
                continue
            if np.all(
                np.isclose(
                    self.surface_constants,
                    surface.surface_constants,
                    rtol=tolerance,
                )
            ):
                ret.append(surface)
        return ret

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


# ---------------------------------------------------------------------------
# Shared validators
# ---------------------------------------------------------------------------


def _enforce_positive_radius(self, value):
    if value < 0.0:
        raise ValueError(f"Radius must be positive. {value} given")


# ---------------------------------------------------------------------------
# CylinderOnAxis  (CX, CY, CZ)
# ---------------------------------------------------------------------------

_cylinder_on_axis_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.CX, SurfaceType.CY, SurfaceType.CZ},
    num_param_values=1,
    params=[
        _SurfaceParamSpec(
            name="radius",
            start_idx=0,
            description="The radius :math:`R` of the cylinder",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        )
    ],
)


class CylinderOnAxis(
    Surface, metaclass=_SurfaceClassFactory, spec=_cylinder_on_axis_spec
):
    """Represents surfaces CX, CY, CZ: an infinite cylinder whose axis lies on
    a coordinate axis.

    The surface equation (e.g. for CZ) is:

    .. math::

        x^2 + y^2 - R^2 = 0

    .. tip::

        Since version 1.4.0 this has not been the preferred class for working with ``CX``, ``CY``, and ``CZ`` surfaces.
        Instead :class:`~montepy.XCylinder`, :class:`~montepy.YCylinder`, and :class:`~montepy.ZCylinder` are preferred.
        There is no plan at this time to deprecate this class, but its use is not going to be promoted.

    .. versionchanged:: 1.0.0

        Added number parameter

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    surface_type : Union[SurfaceType, str]
        The surface_type to set for this object
    """

    def validate(self):
        super().validate()
        if self.radius is None:
            raise IllegalState(f"Surface: {self.number} does not have a radius set.")


# ---------------------------------------------------------------------------
# XCylinder, YCylinder, ZCylinder  (CX, CY, CZ — axis-specific)
# ---------------------------------------------------------------------------


class XCylinder(CylinderOnAxis):
    """Represents surface CX: an infinite cylinder whose axis is the X-axis.

    The surface equation is:

    .. math::

        y^2 + z^2 - R^2 = 0

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    _ALLOWED_SURFACE_TYPES = {SurfaceType.CX}


class YCylinder(CylinderOnAxis):
    """Represents surface CY: an infinite cylinder whose axis is the Y-axis.

    The surface equation is:

    .. math::

        x^2 + z^2 - R^2 = 0

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    _ALLOWED_SURFACE_TYPES = {SurfaceType.CY}


class ZCylinder(CylinderOnAxis):
    """Represents surface CZ: an infinite cylinder whose axis is the Z-axis.

    The surface equation is:

    .. math::

        x^2 + y^2 - R^2 = 0

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    _ALLOWED_SURFACE_TYPES = {SurfaceType.CZ}


# ---------------------------------------------------------------------------
# CylinderParAxis  (C/X, C/Y, C/Z)
# ---------------------------------------------------------------------------

_cylinder_par_axis_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.C_X, SurfaceType.C_Y, SurfaceType.C_Z},
    num_param_values=3,
    params=[
        _SurfaceParamSpec(
            name="coordinates",
            start_idx=0,
            is_tuple=True,
            tuple_length=2,
            description="The two off-axis coordinates :math:`(a_1, a_2)` of the cylinder axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="radius",
            start_idx=2,
            description="The radius :math:`R` of the cylinder",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
)


class CylinderParAxis(
    Surface, metaclass=_SurfaceClassFactory, spec=_cylinder_par_axis_spec
):
    """Represents surfaces C/X, C/Y, C/Z: an infinite cylinder whose axis is
    parallel to a coordinate axis but offset from it.

    The surface equation (e.g. for C/Z) is:

    .. math::

        (x - x_0)^2 + (y - y_0)^2 - R^2 = 0

    .. tip::

        Since version 1.4.0 this has not been the preferred class for working with ``C/X``, ``C/Y``, and ``C/Z`` surfaces.
        Instead :class:`~montepy.XCylinderParAxis`, :class:`~montepy.YCylinderParAxis`, and :class:`~montepy.ZCylinderParAxis` are preferred.
        There is no plan at this time to deprecate this class, but its use is not going to be promoted.

    .. versionchanged:: 1.0.0

        Added number parameter


    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    surface_type : Union[SurfaceType, str]
        The surface_type to set for this object
    """

    COORDINATE_PAIRS = {
        SurfaceType.C_X: {0: "y", 1: "z"},
        SurfaceType.C_Y: {0: "x", 1: "z"},
        SurfaceType.C_Z: {0: "x", 1: "y"},
    }
    """Which coordinate corresponds to which axis for each cylinder type."""

    def validate(self):
        super().validate()
        if self.radius is None:
            raise IllegalState(f"Surface: {self.number} does not have a radius set.")
        if any(c is None for c in self.coordinates):
            raise IllegalState(f"Surface: {self.number} does not have coordinates set.")


# ---------------------------------------------------------------------------
# XCylinderParAxis, YCylinderParAxis, ZCylinderParAxis  (axis-specific)
# ---------------------------------------------------------------------------

_x_cylinder_par_axis_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.C_X},
    num_param_values=3,
    params=[
        _SurfaceParamSpec(
            name="coordinates",
            start_idx=0,
            is_tuple=True,
            tuple_length=2,
            description=r"The off-axis coordinates :math:`(y_0, z_0)` of the cylinder axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=0,
            description=r"The :math:`y`-coordinate :math:`y_0` of the cylinder axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=1,
            description=r"The :math:`z`-coordinate :math:`z_0` of the cylinder axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="radius",
            start_idx=2,
            description="The radius :math:`R` of the cylinder",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
)

_y_cylinder_par_axis_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.C_Y},
    num_param_values=3,
    params=[
        _SurfaceParamSpec(
            name="coordinates",
            start_idx=0,
            is_tuple=True,
            tuple_length=2,
            description=r"The off-axis coordinates :math:`(x_0, z_0)` of the cylinder axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="x",
            start_idx=0,
            description=r"The :math:`x`-coordinate :math:`x_0` of the cylinder axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=1,
            description=r"The :math:`z`-coordinate :math:`z_0` of the cylinder axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="radius",
            start_idx=2,
            description="The radius :math:`R` of the cylinder",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
)

_z_cylinder_par_axis_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.C_Z},
    num_param_values=3,
    params=[
        _SurfaceParamSpec(
            name="coordinates",
            start_idx=0,
            is_tuple=True,
            tuple_length=2,
            description=r"The off-axis coordinates :math:`(x_0, y_0)` of the cylinder axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="x",
            start_idx=0,
            description=r"The :math:`x`-coordinate :math:`x_0` of the cylinder axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=1,
            description=r"The :math:`y`-coordinate :math:`y_0` of the cylinder axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="radius",
            start_idx=2,
            description="The radius :math:`R` of the cylinder",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
)


class XCylinderParAxis(
    CylinderParAxis, metaclass=_SurfaceClassFactory, spec=_x_cylinder_par_axis_spec
):
    """Represents surface C/X: an infinite cylinder whose axis is parallel to
    the X-axis, offset to :math:`(y_0, z_0)`.

    The surface equation is:

    .. math::

        (y - y_0)^2 + (z - z_0)^2 - R^2 = 0

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """


class YCylinderParAxis(
    CylinderParAxis, metaclass=_SurfaceClassFactory, spec=_y_cylinder_par_axis_spec
):
    """Represents surface C/Y: an infinite cylinder whose axis is parallel to
    the Y-axis, offset to :math:`(x_0, z_0)`.

    The surface equation is:

    .. math::

        (x - x_0)^2 + (z - z_0)^2 - R^2 = 0

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """


class ZCylinderParAxis(
    CylinderParAxis, metaclass=_SurfaceClassFactory, spec=_z_cylinder_par_axis_spec
):
    """Represents surface C/Z: an infinite cylinder whose axis is parallel to
    the Z-axis, offset to :math:`(x_0, y_0)`.

    The surface equation is:

    .. math::

        (x - x_0)^2 + (y - y_0)^2 - R^2 = 0

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """


# ---------------------------------------------------------------------------
# AxisPlane  (PX, PY, PZ)
# ---------------------------------------------------------------------------

_axis_plane_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.PX, SurfaceType.PY, SurfaceType.PZ},
    num_param_values=1,
    params=[
        _SurfaceParamSpec(
            name="location",
            start_idx=0,
            description="The location :math:`d` of the plane along the axis",
            types=(float, int),
            base_type=float,
        ),
    ],
)


class AxisPlane(Surface, metaclass=_SurfaceClassFactory, spec=_axis_plane_spec):
    """Represents surfaces PX, PY, PZ: a plane normal to a coordinate axis.

    The surface equation (e.g. for PZ) is:

    .. math::

        z - d = 0

    .. tip::

        Since version 1.4.0 this has not been the preferred class for working with ``PX``, ``PY``, and ``PZ`` surfaces.
        Instead :class:`~montepy.XPlane`, :class:`~montepy.YPlane`, and :class:`~montepy.ZPlane` are preferred.
        There is no plan at this time to deprecate this class, but its use is not going to be promoted.

    .. versionchanged:: 1.0.0

        Added number parameter


    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    surface_type : Union[SurfaceType, str]
        The surface_type to set for this object
    """

    COORDINATE = {SurfaceType.PX: "x", SurfaceType.PY: "y", SurfaceType.PZ: "z"}
    """Maps surface type to the axis name for the plane's location."""

    @property
    def d(self):
        """Alias for :attr:`location` following MCNP manual notation (:math:`d`).

        Returns
        -------
        float
        """
        return self.location

    @d.setter
    def d(self, value):
        self.location = value

    def validate(self):
        super().validate()
        if self.location is None:
            raise IllegalState(f"Surface: {self.number} does not have a location set.")


# ---------------------------------------------------------------------------
# XPlane, YPlane, ZPlane  (PX, PY, PZ — axis-specific)
# ---------------------------------------------------------------------------

_x_plane_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.PX},
    num_param_values=1,
    params=[
        _SurfaceParamSpec(
            name="location",
            start_idx=0,
            description="The location :math:`d` of the plane along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="x",
            start_idx=0,
            description="The :math:`x`-intercept :math:`d` of the plane",
            types=(float, int),
            base_type=float,
        ),
    ],
)

_y_plane_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.PY},
    num_param_values=1,
    params=[
        _SurfaceParamSpec(
            name="location",
            start_idx=0,
            description="The location :math:`d` of the plane along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=0,
            description="The :math:`y`-intercept :math:`d` of the plane",
            types=(float, int),
            base_type=float,
        ),
    ],
)

_z_plane_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.PZ},
    num_param_values=1,
    params=[
        _SurfaceParamSpec(
            name="location",
            start_idx=0,
            description="The location :math:`d` of the plane along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=0,
            description="The :math:`z`-intercept :math:`d` of the plane",
            types=(float, int),
            base_type=float,
        ),
    ],
)


class XPlane(AxisPlane, metaclass=_SurfaceClassFactory, spec=_x_plane_spec):
    """Represents surface PX: a plane normal to the X-axis.

    The surface equation is:

    .. math::

        x - d = 0

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """


class YPlane(AxisPlane, metaclass=_SurfaceClassFactory, spec=_y_plane_spec):
    """Represents surface PY: a plane normal to the Y-axis.

    The surface equation is:

    .. math::

        y - d = 0

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """


class ZPlane(AxisPlane, metaclass=_SurfaceClassFactory, spec=_z_plane_spec):
    """Represents surface PZ: a plane normal to the Z-axis.

    The surface equation is:

    .. math::

        z - d = 0

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """


# ---------------------------------------------------------------------------
# GeneralPlane  (P)
# ---------------------------------------------------------------------------

_general_plane_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.P},
    num_param_values=4,
    params=[
        _SurfaceParamSpec(
            name="A",
            start_idx=0,
            description="Coefficient :math:`A` in :math:`Ax + By + Cz - D = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="B",
            start_idx=1,
            description="Coefficient :math:`B` in :math:`Ax + By + Cz - D = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="C",
            start_idx=2,
            description="Coefficient :math:`C` in :math:`Ax + By + Cz - D = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="D",
            start_idx=3,
            description="Offset :math:`D` in :math:`Ax + By + Cz - D = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="normal",
            start_idx=0,
            is_tuple=True,
            tuple_length=3,
            description="Normal vector :math:`(A, B, C)` of the plane",
            types=(float, int),
            base_type=float,
        ),
    ],
)


class GeneralPlane(Surface, metaclass=_SurfaceClassFactory, spec=_general_plane_spec):
    """Represents surface P: a general plane.

    The surface equation is:

    .. math::

        Ax + By + Cz - D = 0

    May also be defined by three points (9 surface constants).

    .. versionchanged:: 1.0.0

        Added number parameter

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    _VARIABLE_NUM_PARAMS = True

    def _load_params(self):
        self._enforce_constants()
        super()._load_params()

    def validate(self):
        super().validate()
        self._enforce_constants(_validation_call=True)
        if any(c is None for c in (self.A, self.B, self.C, self.D)):
            raise IllegalState(
                f"Surface: {self.number} does not have all plane coefficients (A, B, C, D) set."
            )

    def _enforce_constants(self, _validation_call=False):
        if len(self.surface_constants) not in {4, 9}:
            message = (
                f"A GeneralPlane must have either 4 or 9 surface constants. "
                f"{len(self.surface_constants)} constants are provided."
            )
            if len(self.surface_constants) < 9:
                if not _validation_call:
                    raise ValueError(message)
                else:
                    raise IllegalState(message)
            else:
                warnings.warn(message, SurfaceConstantsWarning)


# ---------------------------------------------------------------------------
# SphereAtOrigin  (SO)
# ---------------------------------------------------------------------------

_sphere_at_origin_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.SO},
    num_param_values=1,
    params=[
        _SurfaceParamSpec(
            name="radius",
            start_idx=0,
            description="The radius :math:`R` of the sphere",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
)


class SphereAtOrigin(
    Surface, metaclass=_SurfaceClassFactory, spec=_sphere_at_origin_spec
):
    """Represents surface SO: a sphere centered at the origin.

    The surface equation is:

    .. math::

        x^2 + y^2 + z^2 - R^2 = 0

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def validate(self):
        super().validate()
        if self.radius is None:
            raise IllegalState(f"Surface: {self.number} does not have a radius set.")


# ---------------------------------------------------------------------------
# GeneralSphere  (S)
# ---------------------------------------------------------------------------

_general_sphere_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.S},
    num_param_values=4,
    params=[
        _SurfaceParamSpec(
            name="x",
            start_idx=0,
            description="The :math:`x`-coordinate of the sphere center :math:`x_0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=1,
            description="The :math:`y`-coordinate of the sphere center :math:`y_0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=2,
            description="The :math:`z`-coordinate of the sphere center :math:`z_0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="center",
            start_idx=0,
            is_tuple=True,
            tuple_length=3,
            description="Center coordinates :math:`(x_0, y_0, z_0)` of the sphere",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="coordinates",
            start_idx=0,
            is_tuple=True,
            tuple_length=3,
            description="Center coordinates :math:`(x_0, y_0, z_0)` of the sphere",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="radius",
            start_idx=3,
            description="The radius :math:`R` of the sphere",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
)


class GeneralSphere(Surface, metaclass=_SurfaceClassFactory, spec=_general_sphere_spec):
    """Represents surface S: a general sphere.

    The surface equation is:

    .. math::

        (x - x_0)^2 + (y - y_0)^2 + (z - z_0)^2 - R^2 = 0

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def validate(self):
        super().validate()
        if self.radius is None:
            raise IllegalState(f"Surface: {self.number} does not have a radius set.")
        if any(c is None for c in self.center):
            raise IllegalState(f"Surface: {self.number} does not have a center set.")


# ---------------------------------------------------------------------------
# SphereOnAxis  (SX, SY, SZ)
# ---------------------------------------------------------------------------

_sphere_on_axis_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.SX, SurfaceType.SY, SurfaceType.SZ},
    num_param_values=2,
    params=[
        _SurfaceParamSpec(
            name="location",
            start_idx=0,
            description="The location :math:`a` of the sphere center along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="radius",
            start_idx=1,
            description="The radius :math:`R` of the sphere",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
)


class SphereOnAxis(Surface, metaclass=_SurfaceClassFactory, spec=_sphere_on_axis_spec):
    """Represents surfaces SX, SY, SZ: a sphere centered on a coordinate axis.

    The surface equation (e.g. for SX) is:

    .. math::

        (x - a)^2 + y^2 + z^2 - R^2 = 0

    .. tip::

        Since version 1.4.0 this has not been the preferred class for working with ``SX``, ``SY``, and ``SZ`` surfaces.
        Instead :class:`~montepy.XSphere`, :class:`~montepy.YSphere`, and :class:`~montepy.ZSphere` are preferred.
        There is no plan at this time to deprecate this class, but its use is not going to be promoted.

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    surface_type : Union[SurfaceType, str]
        The surface_type to set for this object
    """

    COORDINATE = {SurfaceType.SX: "x", SurfaceType.SY: "y", SurfaceType.SZ: "z"}
    """Maps surface type to the axis name for the sphere's center."""

    def validate(self):
        super().validate()
        if self.location is None:
            raise IllegalState(f"Surface: {self.number} does not have a location set.")
        if self.radius is None:
            raise IllegalState(f"Surface: {self.number} does not have a radius set.")


# ---------------------------------------------------------------------------
# XSphere, YSphere, ZSphere  (SX, SY, SZ — axis-specific)
# ---------------------------------------------------------------------------

_x_sphere_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.SX},
    num_param_values=2,
    params=[
        _SurfaceParamSpec(
            name="location",
            start_idx=0,
            description="The location :math:`a` of the sphere center along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="x",
            start_idx=0,
            description="The :math:`x`-coordinate :math:`a` of the sphere center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="radius",
            start_idx=1,
            description="The radius :math:`R` of the sphere",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
)

_y_sphere_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.SY},
    num_param_values=2,
    params=[
        _SurfaceParamSpec(
            name="location",
            start_idx=0,
            description="The location :math:`a` of the sphere center along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=0,
            description="The :math:`y`-coordinate :math:`a` of the sphere center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="radius",
            start_idx=1,
            description="The radius :math:`R` of the sphere",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
)

_z_sphere_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.SZ},
    num_param_values=2,
    params=[
        _SurfaceParamSpec(
            name="location",
            start_idx=0,
            description="The location :math:`a` of the sphere center along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=0,
            description="The :math:`z`-coordinate :math:`a` of the sphere center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="radius",
            start_idx=1,
            description="The radius :math:`R` of the sphere",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
)


class XSphere(SphereOnAxis, metaclass=_SurfaceClassFactory, spec=_x_sphere_spec):
    """Represents surface SX: a sphere centered on the X-axis.

    The surface equation is:

    .. math::

        (x - a)^2 + y^2 + z^2 - R^2 = 0

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """


class YSphere(SphereOnAxis, metaclass=_SurfaceClassFactory, spec=_y_sphere_spec):
    """Represents surface SY: a sphere centered on the Y-axis.

    The surface equation is:

    .. math::

        x^2 + (y - a)^2 + z^2 - R^2 = 0

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """


class ZSphere(SphereOnAxis, metaclass=_SurfaceClassFactory, spec=_z_sphere_spec):
    """Represents surface SZ: a sphere centered on the Z-axis.

    The surface equation is:

    .. math::

        x^2 + y^2 + (z - a)^2 - R^2 = 0

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """


# ---------------------------------------------------------------------------
# ConeOnAxis  (KX, KY, KZ)
# ---------------------------------------------------------------------------

_cone_on_axis_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.KX, SurfaceType.KY, SurfaceType.KZ},
    num_param_values=2,
    params=[
        _SurfaceParamSpec(
            name="apex",
            start_idx=0,
            description="The position :math:`a` of the cone apex along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="t_squared",
            start_idx=1,
            description=r"The squared tangent of the half-angle :math:`t^2`",
            types=(float, int),
            base_type=float,
        ),
    ],
)


class ConeOnAxis(Surface, metaclass=_SurfaceClassFactory, spec=_cone_on_axis_spec):
    """Represents surfaces KX, KY, KZ: a cone whose apex lies on a coordinate axis.

    The surface equation (e.g. for KZ) is:

    .. math::

        x^2 + y^2 - t^2 (z - a)^2 = 0

    The optional third surface constant selects a single nappe
    (``+1`` upper, ``-1`` lower); omitting it gives both nappes.
    Access it via ``surface_constants[2]`` if present.

    .. tip::

        Since version 1.4.0 this has not been the preferred class for working with ``KX``, ``KY``, and ``KZ`` surfaces.
        Instead :class:`~montepy.XCone`, :class:`~montepy.YCone`, and :class:`~montepy.ZCone` are preferred.
        There is no plan at this time to deprecate this class, but its use is not going to be promoted.

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    surface_type : Union[SurfaceType, str]
        The surface_type to set for this object
    """

    COORDINATE = {SurfaceType.KX: "x", SurfaceType.KY: "y", SurfaceType.KZ: "z"}
    """Maps surface type to the axis name for the cone's apex."""

    def validate(self):
        super().validate()
        if self.apex is None:
            raise IllegalState(f"Surface: {self.number} does not have an apex set.")
        if self.t_squared is None:
            raise IllegalState(f"Surface: {self.number} does not have t_squared set.")


# ---------------------------------------------------------------------------
# XCone, YCone, ZCone  (KX, KY, KZ — axis-specific)
# ---------------------------------------------------------------------------

_x_cone_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.KX},
    num_param_values=2,
    params=[
        _SurfaceParamSpec(
            name="apex",
            start_idx=0,
            description="The position :math:`a` of the cone apex along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="x",
            start_idx=0,
            description="The :math:`x`-coordinate :math:`a` of the cone apex",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="t_squared",
            start_idx=1,
            description=r"The squared tangent of the half-angle :math:`t^2`",
            types=(float, int),
            base_type=float,
        ),
    ],
)

_y_cone_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.KY},
    num_param_values=2,
    params=[
        _SurfaceParamSpec(
            name="apex",
            start_idx=0,
            description="The position :math:`a` of the cone apex along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=0,
            description="The :math:`y`-coordinate :math:`a` of the cone apex",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="t_squared",
            start_idx=1,
            description=r"The squared tangent of the half-angle :math:`t^2`",
            types=(float, int),
            base_type=float,
        ),
    ],
)

_z_cone_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.KZ},
    num_param_values=2,
    params=[
        _SurfaceParamSpec(
            name="apex",
            start_idx=0,
            description="The position :math:`a` of the cone apex along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=0,
            description="The :math:`z`-coordinate :math:`a` of the cone apex",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="t_squared",
            start_idx=1,
            description=r"The squared tangent of the half-angle :math:`t^2`",
            types=(float, int),
            base_type=float,
        ),
    ],
)


class XCone(ConeOnAxis, metaclass=_SurfaceClassFactory, spec=_x_cone_spec):
    """Represents surface KX: a cone whose apex lies on the X-axis.

    The surface equation is:

    .. math::

        y^2 + z^2 - t^2 (x - a)^2 = 0

    The optional third surface constant selects a single nappe
    (``+1`` upper, ``-1`` lower); omitting it gives both nappes.

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """


class YCone(ConeOnAxis, metaclass=_SurfaceClassFactory, spec=_y_cone_spec):
    """Represents surface KY: a cone whose apex lies on the Y-axis.

    The surface equation is:

    .. math::

        x^2 + z^2 - t^2 (y - a)^2 = 0

    The optional third surface constant selects a single nappe
    (``+1`` upper, ``-1`` lower); omitting it gives both nappes.

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """


class ZCone(ConeOnAxis, metaclass=_SurfaceClassFactory, spec=_z_cone_spec):
    """Represents surface KZ: a cone whose apex lies on the Z-axis.

    The surface equation is:

    .. math::

        x^2 + y^2 - t^2 (z - a)^2 = 0

    The optional third surface constant selects a single nappe
    (``+1`` upper, ``-1`` lower); omitting it gives both nappes.

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """


# ---------------------------------------------------------------------------
# ConeParAxis  (K/X, K/Y, K/Z)
# ---------------------------------------------------------------------------

_cone_par_axis_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.K_X, SurfaceType.K_Y, SurfaceType.K_Z},
    num_param_values=4,
    params=[
        _SurfaceParamSpec(
            name="x",
            start_idx=0,
            description="The :math:`x`-coordinate of the cone apex :math:`x_0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=1,
            description="The :math:`y`-coordinate of the cone apex :math:`y_0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=2,
            description="The :math:`z`-coordinate of the cone apex :math:`z_0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="apex",
            start_idx=0,
            is_tuple=True,
            tuple_length=3,
            description="Apex coordinates :math:`(x_0, y_0, z_0)` of the cone",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="t_squared",
            start_idx=3,
            description=r"The squared tangent of the half-angle :math:`t^2`",
            types=(float, int),
            base_type=float,
        ),
    ],
)


class ConeParAxis(Surface, metaclass=_SurfaceClassFactory, spec=_cone_par_axis_spec):
    """Represents surfaces K/X, K/Y, K/Z: a cone whose axis is parallel to a
    coordinate axis with its apex at an arbitrary point.

    The surface equation (e.g. for K/Z) is:

    .. math::

        (x - x_0)^2 + (y - y_0)^2 - t^2 (z - z_0)^2 = 0

    The optional fifth surface constant selects a single nappe
    (``+1`` upper, ``-1`` lower); omitting it gives both nappes.
    Access it via ``surface_constants[4]`` if present.

    .. tip::

        Since version 1.4.0 this has not been the preferred class for working with ``K/X``, ``K/Y``, and ``K/Z`` surfaces.
        Instead :class:`~montepy.XConeParAxis`, :class:`~montepy.YConeParAxis`, and :class:`~montepy.ZConeParAxis` are preferred.
        There is no plan at this time to deprecate this class, but its use is not going to be promoted.

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    surface_type : Union[SurfaceType, str]
        The surface_type to set for this object
    """

    def validate(self):
        super().validate()
        if any(c is None for c in self.apex):
            raise IllegalState(f"Surface: {self.number} does not have an apex set.")
        if self.t_squared is None:
            raise IllegalState(f"Surface: {self.number} does not have t_squared set.")


# ---------------------------------------------------------------------------
# XConeParAxis, YConeParAxis, ZConeParAxis  (axis-specific)
# ---------------------------------------------------------------------------


class XConeParAxis(ConeParAxis):
    """Represents surface K/X: a cone whose axis is parallel to the X-axis
    with its apex at an arbitrary point :math:`(x_0, y_0, z_0)`.

    The surface equation is:

    .. math::

        (y - y_0)^2 + (z - z_0)^2 - t^2 (x - x_0)^2 = 0

    The optional fifth surface constant selects a single nappe
    (``+1`` upper, ``-1`` lower); omitting it gives both nappes.

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    _ALLOWED_SURFACE_TYPES = {SurfaceType.K_X}


class YConeParAxis(ConeParAxis):
    """Represents surface K/Y: a cone whose axis is parallel to the Y-axis
    with its apex at an arbitrary point :math:`(x_0, y_0, z_0)`.

    The surface equation is:

    .. math::

        (x - x_0)^2 + (z - z_0)^2 - t^2 (y - y_0)^2 = 0

    The optional fifth surface constant selects a single nappe
    (``+1`` upper, ``-1`` lower); omitting it gives both nappes.

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    _ALLOWED_SURFACE_TYPES = {SurfaceType.K_Y}


class ZConeParAxis(ConeParAxis):
    """Represents surface K/Z: a cone whose axis is parallel to the Z-axis
    with its apex at an arbitrary point :math:`(x_0, y_0, z_0)`.

    The surface equation is:

    .. math::

        (x - x_0)^2 + (y - y_0)^2 - t^2 (z - z_0)^2 = 0

    The optional fifth surface constant selects a single nappe
    (``+1`` upper, ``-1`` lower); omitting it gives both nappes.

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    _ALLOWED_SURFACE_TYPES = {SurfaceType.K_Z}


# ---------------------------------------------------------------------------
# AxisAlignedQuadric  (SQ)
# ---------------------------------------------------------------------------

_axis_aligned_quadric_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.SQ},
    num_param_values=10,
    params=[
        _SurfaceParamSpec(
            name="A",
            start_idx=0,
            description=r"Coefficient :math:`A` in :math:`A(x-x_0)^2 + B(y-y_0)^2 + C(z-z_0)^2 + D(x-x_0) + E(y-y_0) + F(z-z_0) + G = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="B",
            start_idx=1,
            description=r"Coefficient :math:`B` in :math:`A(x-x_0)^2 + B(y-y_0)^2 + C(z-z_0)^2 + D(x-x_0) + E(y-y_0) + F(z-z_0) + G = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="C",
            start_idx=2,
            description=r"Coefficient :math:`C` in :math:`A(x-x_0)^2 + B(y-y_0)^2 + C(z-z_0)^2 + D(x-x_0) + E(y-y_0) + F(z-z_0) + G = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="D",
            start_idx=3,
            description=r"Coefficient :math:`D` in :math:`A(x-x_0)^2 + B(y-y_0)^2 + C(z-z_0)^2 + D(x-x_0) + E(y-y_0) + F(z-z_0) + G = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="E",
            start_idx=4,
            description=r"Coefficient :math:`E` in :math:`A(x-x_0)^2 + B(y-y_0)^2 + C(z-z_0)^2 + D(x-x_0) + E(y-y_0) + F(z-z_0) + G = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="F",
            start_idx=5,
            description=r"Coefficient :math:`F` in :math:`A(x-x_0)^2 + B(y-y_0)^2 + C(z-z_0)^2 + D(x-x_0) + E(y-y_0) + F(z-z_0) + G = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="G",
            start_idx=6,
            description=r"Constant :math:`G` in :math:`A(x-x_0)^2 + B(y-y_0)^2 + C(z-z_0)^2 + D(x-x_0) + E(y-y_0) + F(z-z_0) + G = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="x",
            start_idx=7,
            description="The :math:`x`-coordinate of the reference point :math:`x_0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=8,
            description="The :math:`y`-coordinate of the reference point :math:`y_0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=9,
            description="The :math:`z`-coordinate of the reference point :math:`z_0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="center",
            start_idx=7,
            is_tuple=True,
            tuple_length=3,
            description="Reference point :math:`(x_0, y_0, z_0)` of the quadric",
            types=(float, int),
            base_type=float,
        ),
    ],
)


class AxisAlignedQuadric(
    Surface, metaclass=_SurfaceClassFactory, spec=_axis_aligned_quadric_spec
):
    """Represents surface SQ: an ellipsoid, hyperboloid, or paraboloid whose
    axes are parallel to the coordinate axes.

    The surface equation is:

    .. math::

        A(x-x_0)^2 + B(y-y_0)^2 + C(z-z_0)^2
        + D(x-x_0) + E(y-y_0) + F(z-z_0) + G = 0

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def validate(self):
        super().validate()
        for name in ("A", "B", "C", "D", "E", "F", "G"):
            if getattr(self, name) is None:
                raise IllegalState(
                    f"Surface: {self.number} coefficient {name} is not set."
                )
        if any(c is None for c in self.center):
            raise IllegalState(f"Surface: {self.number} does not have a center set.")


# ---------------------------------------------------------------------------
# GeneralQuadric  (GQ)
# ---------------------------------------------------------------------------

_general_quadric_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.GQ},
    num_param_values=10,
    params=[
        _SurfaceParamSpec(
            name="A",
            start_idx=0,
            description=r"Coefficient :math:`A` in :math:`Ax^2 + By^2 + Cz^2 + Dxy + Eyz + Fxz + Gx + Hy + Jz + K = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="B",
            start_idx=1,
            description=r"Coefficient :math:`B` in :math:`Ax^2 + By^2 + Cz^2 + Dxy + Eyz + Fxz + Gx + Hy + Jz + K = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="C",
            start_idx=2,
            description=r"Coefficient :math:`C` in :math:`Ax^2 + By^2 + Cz^2 + Dxy + Eyz + Fxz + Gx + Hy + Jz + K = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="D",
            start_idx=3,
            description=r"Coefficient :math:`D` in :math:`Ax^2 + By^2 + Cz^2 + Dxy + Eyz + Fxz + Gx + Hy + Jz + K = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="E",
            start_idx=4,
            description=r"Coefficient :math:`E` in :math:`Ax^2 + By^2 + Cz^2 + Dxy + Eyz + Fxz + Gx + Hy + Jz + K = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="F",
            start_idx=5,
            description=r"Coefficient :math:`F` in :math:`Ax^2 + By^2 + Cz^2 + Dxy + Eyz + Fxz + Gx + Hy + Jz + K = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="G",
            start_idx=6,
            description=r"Coefficient :math:`G` in :math:`Ax^2 + By^2 + Cz^2 + Dxy + Eyz + Fxz + Gx + Hy + Jz + K = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="H",
            start_idx=7,
            description=r"Coefficient :math:`H` in :math:`Ax^2 + By^2 + Cz^2 + Dxy + Eyz + Fxz + Gx + Hy + Jz + K = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="J",
            start_idx=8,
            description=r"Coefficient :math:`J` in :math:`Ax^2 + By^2 + Cz^2 + Dxy + Eyz + Fxz + Gx + Hy + Jz + K = 0`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="K",
            start_idx=9,
            description=r"Constant :math:`K` in :math:`Ax^2 + By^2 + Cz^2 + Dxy + Eyz + Fxz + Gx + Hy + Jz + K = 0`",
            types=(float, int),
            base_type=float,
        ),
    ],
)


class GeneralQuadric(
    Surface, metaclass=_SurfaceClassFactory, spec=_general_quadric_spec
):
    """Represents surface GQ: a general quadric surface (cylinder, cone,
    ellipsoid, hyperboloid, or paraboloid) at arbitrary orientation.

    The surface equation is:

    .. math::

        Ax^2 + By^2 + Cz^2 + Dxy + Eyz + Fxz + Gx + Hy + Jz + K = 0

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def validate(self):
        super().validate()
        for name in ("A", "B", "C", "D", "E", "F", "G", "H", "J", "K"):
            if getattr(self, name) is None:
                raise IllegalState(
                    f"Surface: {self.number} coefficient {name} is not set."
                )


# ---------------------------------------------------------------------------
# Torus  (TX, TY, TZ)
# ---------------------------------------------------------------------------

_torus_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.TX, SurfaceType.TY, SurfaceType.TZ},
    num_param_values=6,
    params=[
        _SurfaceParamSpec(
            name="x",
            start_idx=0,
            description="The :math:`x`-coordinate of the torus center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=1,
            description="The :math:`y`-coordinate of the torus center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=2,
            description="The :math:`z`-coordinate of the torus center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="center",
            start_idx=0,
            is_tuple=True,
            tuple_length=3,
            description="Center coordinates :math:`(x_0, y_0, z_0)` of the torus",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="major_radius",
            start_idx=3,
            description="Major radius :math:`A`: distance from the torus center to the tube center",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
        _SurfaceParamSpec(
            name="minor_radii",
            start_idx=4,
            is_tuple=True,
            tuple_length=2,
            description=r"Minor radii :math:`(B, C)` of the tube cross-section",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
        _SurfaceParamSpec(
            name="minor_radius_1",
            start_idx=4,
            description="Minor radius :math:`B` perpendicular to the torus axis",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
        _SurfaceParamSpec(
            name="minor_radius_2",
            start_idx=5,
            description="Minor radius :math:`C` parallel to the torus axis",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
)


class Torus(Surface, metaclass=_SurfaceClassFactory, spec=_torus_spec):
    """Represents surfaces TX, TY, TZ: an elliptical torus whose axis of
    symmetry is parallel to a coordinate axis.

    The surface equation (e.g. for TZ) is:

    .. math::

        \\left(\\sqrt{(x-x_0)^2+(y-y_0)^2} - A\\right)^2 / B^2
        + (z-z_0)^2 / C^2 - 1 = 0

    .. tip::

        Since version 1.4.0 this has not been the preferred class for working with ``TX``, ``TY``, and ``TZ`` surfaces.
        Instead :class:`~montepy.XTorus`, :class:`~montepy.YTorus`, and :class:`~montepy.ZTorus` are preferred.
        There is no plan at this time to deprecate this class, but its use is not going to be promoted.

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    surface_type : Union[SurfaceType, str]
        The surface_type to set for this object
    """

    @property
    def minor_radius(self):
        """The minor radius of the torus when the tube cross-section is
        circular, i.e. when :attr:`minor_radius_1` :math:`B` and
        :attr:`minor_radius_2` :math:`C` are equal.

        Getting this property raises :class:`ValueError` if the two minor
        radii are not approximately equal.

        Setting this property assigns the same value to both
        :attr:`minor_radius_1` and :attr:`minor_radius_2`.

        Returns
        -------
        float

        Raises
        ------
        ValueError
            If :attr:`minor_radius_1` and :attr:`minor_radius_2` differ.
        """
        r1, r2 = self.minor_radius_1, self.minor_radius_2
        if r1 is None or r2 is None:
            return None
        if not math.isclose(r1, r2):
            raise ValueError(
                f"minor_radius is only defined when minor_radius_1 and "
                f"minor_radius_2 are equal. Got {r1} and {r2}."
            )
        return r1

    @minor_radius.setter
    def minor_radius(self, value):
        if not isinstance(value, (float, int)):
            raise TypeError(f"minor_radius must be a number. {value} given.")
        value = float(value)
        _enforce_positive_radius(self, value)
        self.minor_radius_1 = value
        self.minor_radius_2 = value

    def validate(self):
        super().validate()
        if any(c is None for c in self.center):
            raise IllegalState(f"Surface: {self.number} does not have a center set.")
        if self.major_radius is None:
            raise IllegalState(
                f"Surface: {self.number} does not have a major_radius set."
            )
        if any(r is None for r in self.minor_radii):
            raise IllegalState(f"Surface: {self.number} does not have minor_radii set.")


# ---------------------------------------------------------------------------
# XTorus, YTorus, ZTorus  (TX, TY, TZ — axis-specific)
# ---------------------------------------------------------------------------


class XTorus(Torus):
    """Represents surface TX: a torus whose axis of symmetry is the X-axis.

    The surface equation is:

    .. math::

        \\left(\\sqrt{(y - y_0)^2 + (z - z_0)^2} - A\\right)^2
        \\frac{1}{B^2}
        + \\frac{(x - x_0)^2}{C^2} - 1 = 0

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    _ALLOWED_SURFACE_TYPES = {SurfaceType.TX}


class YTorus(Torus):
    """Represents surface TY: a torus whose axis of symmetry is the Y-axis.

    The surface equation is:

    .. math::

        \\left(\\sqrt{(x - x_0)^2 + (z - z_0)^2} - A\\right)^2
        \\frac{1}{B^2}
        + \\frac{(y - y_0)^2}{C^2} - 1 = 0

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    _ALLOWED_SURFACE_TYPES = {SurfaceType.TY}


class ZTorus(Torus):
    """Represents surface TZ: a torus whose axis of symmetry is the Z-axis.

    The surface equation is:

    .. math::

        \\left(\\sqrt{(x - x_0)^2 + (y - y_0)^2} - A\\right)^2
        \\frac{1}{B^2}
        + \\frac{(z - z_0)^2}{C^2} - 1 = 0

    .. versionadded:: 1.4.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    _ALLOWED_SURFACE_TYPES = {SurfaceType.TZ}


# ---------------------------------------------------------------------------
# Box  (BOX)
# ---------------------------------------------------------------------------

_box_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.BOX},
    num_param_values=12,
    params=[
        _SurfaceParamSpec(
            name="corner",
            start_idx=0,
            is_tuple=True,
            tuple_length=3,
            description="Corner point :math:`(v_x, v_y, v_z)` of the box",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="edge_1",
            start_idx=3,
            is_tuple=True,
            tuple_length=3,
            description="First edge vector :math:`\\mathbf{a}_1` of the box",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="edge_2",
            start_idx=6,
            is_tuple=True,
            tuple_length=3,
            description="Second edge vector :math:`\\mathbf{a}_2` of the box",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="edge_3",
            start_idx=9,
            is_tuple=True,
            tuple_length=3,
            description="Third edge vector :math:`\\mathbf{a}_3` of the box",
            types=(float, int),
            base_type=float,
        ),
    ],
)


class Box(Surface, metaclass=_SurfaceClassFactory, spec=_box_spec):
    """Represents macrobody BOX: a general orthogonal box defined by a corner
    point and three edge vectors.

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def validate(self):
        super().validate()
        if any(c is None for c in self.corner):
            raise IllegalState(f"Surface: {self.number} does not have a corner set.")


# ---------------------------------------------------------------------------
# RectangularParallelepiped  (RPP)
# ---------------------------------------------------------------------------

_rpp_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.RPP},
    num_param_values=6,
    params=[
        _SurfaceParamSpec(
            name="x_min",
            start_idx=0,
            description="Minimum :math:`x` extent",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="x_max",
            start_idx=1,
            description="Maximum :math:`x` extent",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y_min",
            start_idx=2,
            description="Minimum :math:`y` extent",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y_max",
            start_idx=3,
            description="Maximum :math:`y` extent",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z_min",
            start_idx=4,
            description="Minimum :math:`z` extent",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z_max",
            start_idx=5,
            description="Maximum :math:`z` extent",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="x_bounds",
            start_idx=0,
            is_tuple=True,
            tuple_length=2,
            description=":math:`x` bounds :math:`(x_{min}, x_{max})`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y_bounds",
            start_idx=2,
            is_tuple=True,
            tuple_length=2,
            description=":math:`y` bounds :math:`(y_{min}, y_{max})`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z_bounds",
            start_idx=4,
            is_tuple=True,
            tuple_length=2,
            description=":math:`z` bounds :math:`(z_{min}, z_{max})`",
            types=(float, int),
            base_type=float,
        ),
    ],
)


class RectangularParallelepiped(
    Surface, metaclass=_SurfaceClassFactory, spec=_rpp_spec
):
    """Represents macrobody RPP: an axis-aligned rectangular parallelepiped
    defined by min/max extents on each axis.

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def validate(self):
        super().validate()
        for attr in ("x_min", "x_max", "y_min", "y_max", "z_min", "z_max"):
            if getattr(self, attr) is None:
                raise IllegalState(f"Surface: {self.number} does not have {attr} set.")


# ---------------------------------------------------------------------------
# SphereMacrobody  (SPH)
# ---------------------------------------------------------------------------

_sphere_macrobody_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.SPH},
    num_param_values=4,
    params=[
        _SurfaceParamSpec(
            name="x",
            start_idx=0,
            description="The :math:`x`-coordinate of the sphere center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=1,
            description="The :math:`y`-coordinate of the sphere center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=2,
            description="The :math:`z`-coordinate of the sphere center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="center",
            start_idx=0,
            is_tuple=True,
            tuple_length=3,
            description="Center coordinates :math:`(x_0, y_0, z_0)` of the sphere",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="radius",
            start_idx=3,
            description="The radius :math:`R` of the sphere",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
)


class SphereMacrobody(
    Surface, metaclass=_SurfaceClassFactory, spec=_sphere_macrobody_spec
):
    """Represents macrobody SPH: a sphere defined by center and radius.

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def validate(self):
        super().validate()
        if any(c is None for c in self.center):
            raise IllegalState(f"Surface: {self.number} does not have a center set.")
        if self.radius is None:
            raise IllegalState(f"Surface: {self.number} does not have a radius set.")


# ---------------------------------------------------------------------------
# RightCircularCylinder  (RCC)
# ---------------------------------------------------------------------------

_rcc_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.RCC},
    num_param_values=7,
    params=[
        _SurfaceParamSpec(
            name="x",
            start_idx=0,
            description="The :math:`x`-coordinate of the base center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=1,
            description="The :math:`y`-coordinate of the base center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=2,
            description="The :math:`z`-coordinate of the base center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="center",
            start_idx=0,
            is_tuple=True,
            tuple_length=3,
            description="Base center coordinates :math:`(v_x, v_y, v_z)`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="height_vector",
            start_idx=3,
            is_tuple=True,
            tuple_length=3,
            description="Height vector :math:`\\mathbf{h}` from base to top center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="radius",
            start_idx=6,
            description="The radius :math:`R` of the cylinder",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
)


class RightCircularCylinder(Surface, metaclass=_SurfaceClassFactory, spec=_rcc_spec):
    """Represents macrobody RCC: a right circular cylinder defined by a base
    center, height vector, and radius.

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def validate(self):
        super().validate()
        if any(c is None for c in self.center):
            raise IllegalState(f"Surface: {self.number} does not have a center set.")
        if any(h is None for h in self.height_vector):
            raise IllegalState(
                f"Surface: {self.number} does not have a height_vector set."
            )
        if self.radius is None:
            raise IllegalState(f"Surface: {self.number} does not have a radius set.")


# ---------------------------------------------------------------------------
# RightHexagonalPrism  (RHP / HEX)
# ---------------------------------------------------------------------------

_rhp_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.RHP, SurfaceType.HEX},
    num_param_values=15,
    params=[
        _SurfaceParamSpec(
            name="x",
            start_idx=0,
            description="The :math:`x`-coordinate of the base center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=1,
            description="The :math:`y`-coordinate of the base center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=2,
            description="The :math:`z`-coordinate of the base center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="center",
            start_idx=0,
            is_tuple=True,
            tuple_length=3,
            description="Base center coordinates :math:`(v_x, v_y, v_z)`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="height_vector",
            start_idx=3,
            is_tuple=True,
            tuple_length=3,
            description="Height vector :math:`\\mathbf{h}` from base to top center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="facet_vector_1",
            start_idx=6,
            is_tuple=True,
            tuple_length=3,
            description="First facet vector from base center to a flat-face midpoint",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="facet_vector_2",
            start_idx=9,
            is_tuple=True,
            tuple_length=3,
            description="Second facet vector from base center to a flat-face midpoint",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="facet_vector_3",
            start_idx=12,
            is_tuple=True,
            tuple_length=3,
            description="Third facet vector from base center to a flat-face midpoint",
            types=(float, int),
            base_type=float,
        ),
    ],
)


class RightHexagonalPrism(Surface, metaclass=_SurfaceClassFactory, spec=_rhp_spec):
    """Represents macrobodies RHP and HEX: a right hexagonal prism defined by
    a base center, height vector, and three facet vectors.

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def validate(self):
        super().validate()
        if any(c is None for c in self.center):
            raise IllegalState(f"Surface: {self.number} does not have a center set.")
        if any(h is None for h in self.height_vector):
            raise IllegalState(
                f"Surface: {self.number} does not have a height_vector set."
            )


# ---------------------------------------------------------------------------
# RightEllipticalCylinder  (REC)
# ---------------------------------------------------------------------------

_rec_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.REC},
    num_param_values=12,
    params=[
        _SurfaceParamSpec(
            name="x",
            start_idx=0,
            description="The :math:`x`-coordinate of the base center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=1,
            description="The :math:`y`-coordinate of the base center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=2,
            description="The :math:`z`-coordinate of the base center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="center",
            start_idx=0,
            is_tuple=True,
            tuple_length=3,
            description="Base center coordinates :math:`(v_x, v_y, v_z)`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="height_vector",
            start_idx=3,
            is_tuple=True,
            tuple_length=3,
            description="Height vector :math:`\\mathbf{h}` from base to top center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="semi_major_axis",
            start_idx=6,
            is_tuple=True,
            tuple_length=3,
            description="Semi-major axis vector :math:`\\mathbf{r}_1` of the elliptical cross-section",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="semi_minor_axis",
            start_idx=9,
            is_tuple=True,
            tuple_length=3,
            description="Semi-minor axis vector :math:`\\mathbf{r}_2` of the elliptical cross-section",
            types=(float, int),
            base_type=float,
        ),
    ],
)


class RightEllipticalCylinder(Surface, metaclass=_SurfaceClassFactory, spec=_rec_spec):
    """Represents macrobody REC: a right elliptical cylinder defined by a base
    center, height vector, and semi-axis vectors.

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def validate(self):
        super().validate()
        if any(c is None for c in self.center):
            raise IllegalState(f"Surface: {self.number} does not have a center set.")
        if any(h is None for h in self.height_vector):
            raise IllegalState(
                f"Surface: {self.number} does not have a height_vector set."
            )


# ---------------------------------------------------------------------------
# TruncatedRightCone  (TRC)
# ---------------------------------------------------------------------------

_trc_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.TRC},
    num_param_values=8,
    params=[
        _SurfaceParamSpec(
            name="x",
            start_idx=0,
            description="The :math:`x`-coordinate of the base center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=1,
            description="The :math:`y`-coordinate of the base center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=2,
            description="The :math:`z`-coordinate of the base center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="center",
            start_idx=0,
            is_tuple=True,
            tuple_length=3,
            description="Base center coordinates :math:`(v_x, v_y, v_z)`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="height_vector",
            start_idx=3,
            is_tuple=True,
            tuple_length=3,
            description="Height vector :math:`\\mathbf{h}` from base center to top center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="base_radius",
            start_idx=6,
            description="The radius :math:`r_1` of the base",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
        _SurfaceParamSpec(
            name="top_radius",
            start_idx=7,
            description="The radius :math:`r_2` of the top",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
)


class TruncatedRightCone(Surface, metaclass=_SurfaceClassFactory, spec=_trc_spec):
    """Represents macrobody TRC: a truncated right-angle cone defined by a base
    center, height vector, and two radii.

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def validate(self):
        super().validate()
        if any(c is None for c in self.center):
            raise IllegalState(f"Surface: {self.number} does not have a center set.")
        if any(h is None for h in self.height_vector):
            raise IllegalState(
                f"Surface: {self.number} does not have a height_vector set."
            )
        if self.base_radius is None:
            raise IllegalState(
                f"Surface: {self.number} does not have a base_radius set."
            )
        if self.top_radius is None:
            raise IllegalState(
                f"Surface: {self.number} does not have a top_radius set."
            )


# ---------------------------------------------------------------------------
# Ellipsoid  (ELL)
# ---------------------------------------------------------------------------

_ellipsoid_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.ELL},
    num_param_values=7,
    params=[
        _SurfaceParamSpec(
            name="focus_1",
            start_idx=0,
            is_tuple=True,
            tuple_length=3,
            description="First focus coordinates :math:`(v_{1x}, v_{1y}, v_{1z})`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="focus_2",
            start_idx=3,
            is_tuple=True,
            tuple_length=3,
            description="Second focus coordinates :math:`(v_{2x}, v_{2y}, v_{2z})`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="semi_major_axis",
            start_idx=6,
            description="Semi-major axis length :math:`r_m` (positive) or half the distance between foci (negative)",
            types=(float, int),
            base_type=float,
        ),
    ],
)


class Ellipsoid(Surface, metaclass=_SurfaceClassFactory, spec=_ellipsoid_spec):
    """Represents macrobody ELL: an ellipsoid defined by two foci and a
    semi-major axis length.

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def validate(self):
        super().validate()
        if any(f is None for f in self.focus_1):
            raise IllegalState(f"Surface: {self.number} does not have focus_1 set.")
        if any(f is None for f in self.focus_2):
            raise IllegalState(f"Surface: {self.number} does not have focus_2 set.")
        if self.semi_major_axis is None:
            raise IllegalState(
                f"Surface: {self.number} does not have semi_major_axis set."
            )


# ---------------------------------------------------------------------------
# Wedge  (WED)
# ---------------------------------------------------------------------------

_wedge_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.WED},
    num_param_values=12,
    params=[
        _SurfaceParamSpec(
            name="corner",
            start_idx=0,
            is_tuple=True,
            tuple_length=3,
            description="Corner vertex :math:`(v_x, v_y, v_z)` of the wedge base",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="edge_1",
            start_idx=3,
            is_tuple=True,
            tuple_length=3,
            description="First base edge vector :math:`\\mathbf{r}_1`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="edge_2",
            start_idx=6,
            is_tuple=True,
            tuple_length=3,
            description="Second base edge vector :math:`\\mathbf{r}_2`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="height_vector",
            start_idx=9,
            is_tuple=True,
            tuple_length=3,
            description="Height vector :math:`\\mathbf{h}` extruding the triangular base",
            types=(float, int),
            base_type=float,
        ),
    ],
)


class Wedge(Surface, metaclass=_SurfaceClassFactory, spec=_wedge_spec):
    """Represents macrobody WED: a wedge defined by a corner vertex, two base
    edge vectors, and a height vector.

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def validate(self):
        super().validate()
        if any(c is None for c in self.corner):
            raise IllegalState(f"Surface: {self.number} does not have a corner set.")
        if any(h is None for h in self.height_vector):
            raise IllegalState(
                f"Surface: {self.number} does not have a height_vector set."
            )


# ---------------------------------------------------------------------------
# ArbitraryPolyhedron  (ARB)
# ---------------------------------------------------------------------------

_arb_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.ARB},
    num_param_values=30,
    params=[
        _SurfaceParamSpec(
            name="vertex_1",
            start_idx=0,
            is_tuple=True,
            tuple_length=3,
            description="Vertex 1 coordinates :math:`(x_1, y_1, z_1)`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="vertex_2",
            start_idx=3,
            is_tuple=True,
            tuple_length=3,
            description="Vertex 2 coordinates :math:`(x_2, y_2, z_2)`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="vertex_3",
            start_idx=6,
            is_tuple=True,
            tuple_length=3,
            description="Vertex 3 coordinates :math:`(x_3, y_3, z_3)`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="vertex_4",
            start_idx=9,
            is_tuple=True,
            tuple_length=3,
            description="Vertex 4 coordinates :math:`(x_4, y_4, z_4)`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="vertex_5",
            start_idx=12,
            is_tuple=True,
            tuple_length=3,
            description="Vertex 5 coordinates :math:`(x_5, y_5, z_5)`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="vertex_6",
            start_idx=15,
            is_tuple=True,
            tuple_length=3,
            description="Vertex 6 coordinates :math:`(x_6, y_6, z_6)`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="vertex_7",
            start_idx=18,
            is_tuple=True,
            tuple_length=3,
            description="Vertex 7 coordinates :math:`(x_7, y_7, z_7)`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="vertex_8",
            start_idx=21,
            is_tuple=True,
            tuple_length=3,
            description="Vertex 8 coordinates :math:`(x_8, y_8, z_8)`",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="facet_1",
            start_idx=24,
            description="Face 1 descriptor: digit string of up to 4 vertex indices",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="facet_2",
            start_idx=25,
            description="Face 2 descriptor: digit string of up to 4 vertex indices",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="facet_3",
            start_idx=26,
            description="Face 3 descriptor: digit string of up to 4 vertex indices",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="facet_4",
            start_idx=27,
            description="Face 4 descriptor: digit string of up to 4 vertex indices",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="facet_5",
            start_idx=28,
            description="Face 5 descriptor: digit string of up to 4 vertex indices",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="facet_6",
            start_idx=29,
            description="Face 6 descriptor: digit string of up to 4 vertex indices",
            types=(float, int),
            base_type=float,
        ),
    ],
)


class ArbitraryPolyhedron(Surface, metaclass=_SurfaceClassFactory, spec=_arb_spec):
    """Represents macrobody ARB: an arbitrary convex polyhedron defined by up
    to 8 vertices and 6 face descriptors.

    Vertices are given as :math:`(x, y, z)` triples (24 values total).
    Each face descriptor is a 4-digit integer whose digits are the 1-based
    vertex indices forming that face (0 if the face has fewer than 4 vertices).

    .. versionadded:: 1.3.0

    Parameters
    ----------
    input : Union[Input, str]
        The Input object representing the input
    number : int
        The number to set for this object.
    """

    def validate(self):
        super().validate()
        if any(v is None for v in self.vertex_1):
            raise IllegalState(f"Surface: {self.number} does not have vertex_1 set.")
