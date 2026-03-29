# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
import copy
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Union
from numbers import Real
import warnings

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
        setter = metacls.gen_tuple_setter(attr_name, param.tuple_length, param.name)
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
    def gen_tuple_setter(meta_class, hidden_param, length, name):
        def dummy_tuple_setter(self, vals):
            if not isinstance(vals, (list, tuple)):
                raise TypeError(f"{name} must be a list")
            if len(vals) != length:
                raise ValueError(f"{name} must have exactly {length} elements")
            for val in vals:
                if not isinstance(val, Real):
                    # assume it ends in an "s"
                    raise TypeError(f"{name[:-1]} must be a number. {val} given.")
            for in_val, storage in zip(vals, getattr(self, hidden_param)):
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
            if surface == self or surface.surface_type == self.surface_type:
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
                    self._surface_constants,
                    surface.surface_constants,
                    rel_tol=tolerance,
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

    def __init__(self, input=None, number=None):
        super().__init__(input, number)
        if input:
            self._enforce_constants()

    def validate(self):
        super().validate()
        self._enforce_constants(_validation_call=True)

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
