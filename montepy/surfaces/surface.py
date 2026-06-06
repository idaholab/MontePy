# Copyright 2024-2026, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
import copy
from collections.abc import Callable
from dataclasses import asdict, dataclass
import math
import numpy as np
from typing import Union
from numbers import Real
import warnings

import montepy
from montepy.data_inputs import transform
from montepy.exceptions import *
from montepy.input_parser.surface_parser import JitSurfParser, SurfaceParser
from montepy.input_parser import syntax_node
from montepy._exception_context import _ExceptionContextAdder
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


@dataclass
class _SurfaceParamSpec:
    """Specification for a surface type's parameters"""

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
    """Specification for how to load surface_constants into attributes"""

    attr_name: str
    is_tuple: bool
    start_idx: int
    tuple_length: int = 1


@dataclass
class _SurfaceTypeSpec:
    """
    Specification for a class for a surface type.
    """

    surface_types: set[SurfaceType]
    num_param_values: int
    params: list[_SurfaceParamSpec]
    equation: Callable = None


class _SurfaceClassFactory(_ExceptionContextAdder):
    """A metaclass for building :class:`Surface` instances.

    This will take a specification and add the necessary properties
    to the class. It will load the required class attributes so that
    the init function is able to load the right data into the new attributes.
    """

    def __new__(cls, name, bases, namespace, spec: _SurfaceTypeSpec = None, **kwargs):
        if spec is None:
            return super().__new__(cls, name, bases, namespace, **kwargs)
        param_loaders = []
        _SurfaceClassFactory.build_params_props(namespace, spec, param_loaders)
        namespace["_PARAM_LOADERS"] = param_loaders
        namespace["_NUM_PARAMS"] = spec.num_param_values
        namespace["_ALLOWED_SURFACE_TYPES"] = spec.surface_types
        namespace["__equation"] = spec.equation
        # default surface_type scenario
        if len(spec.surface_types) == 1:
            surf_type = next(iter(spec.surface_types))
            namespace["_surface_type"] = surf_type

            @args_checked
            def __init__(
                self,
                input: InitInput = None,
                number: ty.PositiveInt = None,
                *,
                jit_parse: bool = True,
            ):
                Surface.__init__(
                    self,
                    input,
                    number,
                    surface_type=surf_type,
                    jit_parse=jit_parse,
                    **kwargs,
                )

            namespace["__init__"] = __init__
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
        base_func.__doc__ = base_func.__doc__.format(
            **{"tuple_str": ", ".join(["float"] * param.tuple_length)} | asdict(param)
        )
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
        base_func = metacls.gen_scalar_getter()
        base_func.__name__ = param.name
        base_func.__doc__ = base_func.__doc__.format(**asdict(param))
        return make_prop_val_node(
            f"_{param.name}", param.types, param.base_type, param.validator
        )(base_func)

    @classmethod
    def gen_scalar_getter(meta_class):
        def dummy_function(self) -> float:
            """
            {description}

            Returns
            -------
            float
            """
            pass

        return dummy_function

    @classmethod
    def gen_tuple_getter(meta_class, hidden_param):
        @needs_full_ast
        def dummy_tuple_function(self) -> float:
            """
            {description}

            Returns
            -------
            tuple[{tuple_str}]
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


class Surface(Numbered_MCNP_Object, metaclass=_SurfaceClassFactory):
    """Object to hold a single MCNP surface

    .. versionchanged:: 1.0.0

        Added number parameter

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    surface_type: SurfaceType | str
        The surface_type to set for this object
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    _JitParser = JitSurfParser
    _PARAM_LOADERS: list = []
    _NUM_PARAMS: int = 0
    _ALLOWED_SURFACE_TYPES: set = None
    _VARIABLE_NUM_PARAMS: bool = False

    _POINTER_ATTRS = {"transform", "periodic_surface"}

    @staticmethod
    def _parent_collections():
        return (("cells", "surfaces", True), ("surfaces", "periodic_surface", False))

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
            number=number,
            surface_type=surface_type,
            jit_parse=jit_parse,
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
        self._surface_type = self._tree["surface_type"]
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
        num = self._number.value if hasattr(self, "_number") else None
        try:
            if num is not None:
                assert num > 0
        except AssertionError:
            raise MalformedInputError(
                self._input,
                f"{num} could not be parsed as a valid surface number.",
            )
        if hasattr(self, "_tree"):
            if "pointer" in self._tree and self._tree["pointer"].value is not None:
                val = self._tree["pointer"]
                val.is_negatable_identifier = True
                if val.is_negative:
                    self._old_periodic_surface = val
                else:
                    self._old_transform_number = val
            if "surface_type" in self._tree:
                self._surface_type = self._tree["surface_type"]
        if not hasattr(self, "_surface_type"):
            return
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
                self._input,
                f"{self._surface_type.value} could not be parsed as a surface type mnemonic.",
            )
        surf_type_val = self._surface_type.value
        if (
            surf_type_val is not None
            and surf_type_val not in self._allowed_surface_types()
        ):
            raise ValueError(
                f"{type(self).__name__} must be a surface of type: {[e.value for e in self._allowed_surface_types()]}"
            )

    def _load_constants(self):
        if self._PARAM_LOADERS:
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
        self._enforce_constants()
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

    def _enforce_constants(self, _validation_call=False):
        pass

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
        """
        The allowed surface types for this surface type.

        Returns
        -------
        set[SurfaceType]
        """
        if cls._ALLOWED_SURFACE_TYPES is None:
            return set(SurfaceType)
        return cls._ALLOWED_SURFACE_TYPES

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

        E.g. :attr:`~montepy.SurfaceType.CZ`, :attr:`~montepy.SurfaceType.CZ` etc.

        Returns
        -------
        SurfaceType
        """
        pass

    @make_prop_pointer("_is_reflecting", bool)
    @needs_full_ast
    def is_reflecting(self):
        """If true this surface is a reflecting boundary.

        Returns
        -------
        bool
        """
        pass

    @make_prop_pointer("_is_white_boundary", bool)
    @needs_full_ast
    def is_white_boundary(self):
        """If true this surface is a white boundary.

        Returns
        -------
        bool
        """
        pass

    @property
    @needs_full_ast
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
    @needs_full_ast
    def surface_constants(self, constants: ty.Iterable[ty.Real]):
        if len(constants) != len(self._surface_constants):
            raise ValueError(f"Cannot change the length of the surface constants.")
        for i, value in enumerate(constants):
            self._surface_constants[i].value = value

    @make_prop_val_node("_old_transform_number")
    @needs_full_ast
    def old_transform_number(self):
        """The transformation number for this surface in the original file.

        Returns
        -------
        int
        """
        pass

    @make_prop_val_node("_old_periodic_surface")
    @needs_full_ast
    def old_periodic_surface(self):
        """The surface number this is periodic with reference to in the original file.

        Returns
        -------
        int
        """
        pass

    # TODO handle case of deleting value, but the access looks for old value again.
    @prop_pointer_from_problem(
        "_periodic_surface",
        "old_periodic_surface",
        "surfaces",
        types=(),
        deletable=True,
    )
    @needs_full_ast
    def periodic_surface(self):
        """The surface that this surface is periodic with respect to

        Returns
        -------
        Surface
        """
        pass

    @periodic_surface.deleter
    @needs_full_ast
    def periodic_surface(self):
        self._periodic_surface = None
        self._old_periodic_surface.value = None

    @prop_pointer_from_problem(
        "_transform",
        "old_transform_number",
        "transforms",
        transform.Transform,
        deletable=True,
    )
    @needs_full_ast
    def transform(self):
        """The Transform object that translates this surface

        Returns
        -------
        Transform
        """
        pass

    @transform.deleter
    @needs_full_ast
    def transform(self):
        self._transform = None
        self._old_transform_number.value = None

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
        collections.abc.Generator
        """
        if self._problem:
            for cell in self._problem.cells:
                if self in cell.surfaces:
                    yield cell

    def validate(self):
        if self.number is None or self.number < 1:
            raise IllegalState(
                f"Surface: {self.number} does not have a valid number set."
            )
        if self.surface_type is None:
            raise IllegalState(
                f"Surface: {self.number} does not have a surface type set."
            )
        self._enforce_constants(_validation_call=True)
        if any(c is None for c in self.surface_constants):
            raise IllegalState(
                f"Surface: {self.number} does not have all required constants set."
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

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : Input | str
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    surface_type : SurfaceType | str
        The surface_type to set for this object
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """


# ---------------------------------------------------------------------------
# XCylinder, YCylinder, ZCylinder  (CX, CY, CZ — axis-specific)
# ---------------------------------------------------------------------------

_x_cylinder_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.CX},
    num_param_values=1,
    params=[
        _SurfaceParamSpec(
            name="radius",
            start_idx=0,
            description="The radius :math:`R` of the cylinder",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
    equation=lambda x, y, z, c: y**2 + z**2 - c[0] ** 2,
)

_y_cylinder_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.CY},
    num_param_values=1,
    params=[
        _SurfaceParamSpec(
            name="radius",
            start_idx=0,
            description="The radius :math:`R` of the cylinder",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
    equation=lambda x, y, z, c: x**2 + z**2 - c[0] ** 2,
)

_z_cylinder_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.CZ},
    num_param_values=1,
    params=[
        _SurfaceParamSpec(
            name="radius",
            start_idx=0,
            description="The radius :math:`R` of the cylinder",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
    equation=lambda x, y, z, c: x**2 + y**2 - c[0] ** 2,
)


class XCylinder(CylinderOnAxis, metaclass=_SurfaceClassFactory, spec=_x_cylinder_spec):
    """Represents surface CX: an infinite cylinder whose axis is the X-axis.

    The surface equation is:

    .. math::

        y^2 + z^2 - R^2 = 0

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : Input | str
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


class YCylinder(CylinderOnAxis, metaclass=_SurfaceClassFactory, spec=_y_cylinder_spec):
    """Represents surface CY: an infinite cylinder whose axis is the Y-axis.

    The surface equation is:

    .. math::

        x^2 + z^2 - R^2 = 0

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : Input | str
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


class ZCylinder(CylinderOnAxis, metaclass=_SurfaceClassFactory, spec=_z_cylinder_spec):
    """Represents surface CZ: an infinite cylinder whose axis is the Z-axis.

    The surface equation is:

    .. math::

        x^2 + y^2 - R^2 = 0

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : Input | str
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter


    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    surface_type : SurfaceType | str
        The surface type to set for this object
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    COORDINATE_PAIRS = {
        SurfaceType.C_X: {0: "y", 1: "z"},
        SurfaceType.C_Y: {0: "x", 1: "z"},
        SurfaceType.C_Z: {0: "x", 1: "y"},
    }
    """Which coordinate corresponds to which axis for each cylinder type."""


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
    equation=lambda x, y, z, c: (y - c[0]) ** 2 + (z - c[1]) ** 2 - c[2] ** 2,
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
    equation=lambda x, y, z, c: (x - c[0]) ** 2 + (z - c[1]) ** 2 - c[2] ** 2,
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
    equation=lambda x, y, z, c: (x - c[0]) ** 2 + (y - c[1]) ** 2 - c[2] ** 2,
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

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : Input | str
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


class YCylinderParAxis(
    CylinderParAxis, metaclass=_SurfaceClassFactory, spec=_y_cylinder_par_axis_spec
):
    """Represents surface C/Y: an infinite cylinder whose axis is parallel to
    the Y-axis, offset to :math:`(x_0, z_0)`.

    The surface equation is:

    .. math::

        (x - x_0)^2 + (z - z_0)^2 - R^2 = 0

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : Input | str
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


class ZCylinderParAxis(
    CylinderParAxis, metaclass=_SurfaceClassFactory, spec=_z_cylinder_par_axis_spec
):
    """Represents surface C/Z: an infinite cylinder whose axis is parallel to
    the Z-axis, offset to :math:`(x_0, y_0)`.

    The surface equation is:

    .. math::

        (x - x_0)^2 + (y - y_0)^2 - R^2 = 0

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : Input | str
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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
            description="The location :math:`D` of the plane along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="D",
            start_idx=0,
            description="Alias for :attr:`location` following MCNP manual notation (:math:`D`).",
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

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter


    Parameters
    ----------
    input : Input | str
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    surface_type : SurfaceType | str
        The surface_type to set for this object
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    COORDINATE = {SurfaceType.PX: "x", SurfaceType.PY: "y", SurfaceType.PZ: "z"}
    """Maps surface type to the axis name for the plane's location."""


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
            description="The location :math:`D` of the plane along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="x",
            start_idx=0,
            description="The :math:`x`-intercept :math:`D` of the plane",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="D",
            start_idx=0,
            description="Alias for :attr:`location` following MCNP manual notation (:math:`D`).",
            types=(float, int),
            base_type=float,
        ),
    ],
    equation=lambda x, y, z, c: x - c[0],
)

_y_plane_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.PY},
    num_param_values=1,
    params=[
        _SurfaceParamSpec(
            name="location",
            start_idx=0,
            description="The location :math:`D` of the plane along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=0,
            description="The :math:`y`-intercept :math:`D` of the plane",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="D",
            start_idx=0,
            description="Alias for :attr:`location` following MCNP manual notation (:math:`D`).",
            types=(float, int),
            base_type=float,
        ),
    ],
    equation=lambda x, y, z, c: y - c[0],
)

_z_plane_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.PZ},
    num_param_values=1,
    params=[
        _SurfaceParamSpec(
            name="location",
            start_idx=0,
            description="The location :math:`D` of the plane along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=0,
            description="The :math:`z`-intercept :math:`D` of the plane",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="D",
            start_idx=0,
            description="Alias for :attr:`location` following MCNP manual notation (:math:`D`).",
            types=(float, int),
            base_type=float,
        ),
    ],
    equation=lambda x, y, z, c: z - c[0],
)


class XPlane(AxisPlane, metaclass=_SurfaceClassFactory, spec=_x_plane_spec):
    """Represents surface PX: a plane normal to the X-axis.

    The surface equation is:

    .. math::

        x - D = 0

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


class YPlane(AxisPlane, metaclass=_SurfaceClassFactory, spec=_y_plane_spec):
    """Represents surface PY: a plane normal to the Y-axis.

    The surface equation is:

    .. math::

        y - D = 0

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


class ZPlane(AxisPlane, metaclass=_SurfaceClassFactory, spec=_z_plane_spec):
    """Represents surface PZ: a plane normal to the Z-axis.

    The surface equation is:

    .. math::

        z - D = 0

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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
            name="offset",
            start_idx=3,
            description="Alias for :attr:`D`",
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
    equation=lambda x, y, z, c: c[0] * x + c[1] * y + c[2] * z - c[3],
)


class GeneralPlane(Surface, metaclass=_SurfaceClassFactory, spec=_general_plane_spec):
    """Represents surface P: a general plane.

    The surface equation is:

    .. math::

        Ax + By + Cz - D = 0

    May also be defined by three points (9 surface constants).

    .. versionchanged:: 1.0.0

        Added number parameter

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    _VARIABLE_NUM_PARAMS = True

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
    equation=lambda x, y, z, c: x**2 + y**2 + z**2 - c[0] ** 2,
)


class SphereAtOrigin(
    Surface, metaclass=_SurfaceClassFactory, spec=_sphere_at_origin_spec
):
    """Represents surface SO: a sphere centered at the origin.

    The surface equation is:

    .. math::

        x^2 + y^2 + z^2 - R^2 = 0

    .. versionadded:: 1.3.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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
    equation=lambda x, y, z, c: (x - c[0]) ** 2
    + (y - c[1]) ** 2
    + (z - c[2]) ** 2
    - c[3] ** 2,
)


class GeneralSphere(Surface, metaclass=_SurfaceClassFactory, spec=_general_sphere_spec):
    """Represents surface S: a general sphere.

    The surface equation is:

    .. math::

        (x - x_0)^2 + (y - y_0)^2 + (z - z_0)^2 - R^2 = 0

    .. versionadded:: 1.3.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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
            description="The location :math:`x_0` (or :math:`y_0`, or :math:`z_0`) of the sphere center along the axis",
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

        (x - x_0)^2 + y^2 + z^2 - R^2 = 0

    .. tip::

        Since version 1.4.0 this has not been the preferred class for working with ``SX``, ``SY``, and ``SZ`` surfaces.
        Instead :class:`~montepy.XSphere`, :class:`~montepy.YSphere`, and :class:`~montepy.ZSphere` are preferred.
        There is no plan at this time to deprecate this class, but its use is not going to be promoted.

    .. versionadded:: 1.3.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    surface_type : Union[SurfaceType, str]
        The surface type to set for this object
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    COORDINATE = {SurfaceType.SX: "x", SurfaceType.SY: "y", SurfaceType.SZ: "z"}
    """Maps surface type to the axis name for the sphere's center."""


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
            description="The location :math:`x_0` of the sphere center along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="x",
            start_idx=0,
            description="The :math:`x`-coordinate :math:`x_0` of the sphere center",
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
    equation=lambda x, y, z, c: (x - c[0]) ** 2 + y**2 + z**2 - c[1] ** 2,
)

_y_sphere_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.SY},
    num_param_values=2,
    params=[
        _SurfaceParamSpec(
            name="location",
            start_idx=0,
            description="The location :math:`y_0` of the sphere center along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=0,
            description="The :math:`y`-coordinate :math:`y_0` of the sphere center",
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
    equation=lambda x, y, z, c: x**2 + (y - c[0]) ** 2 + z**2 - c[1] ** 2,
)

_z_sphere_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.SZ},
    num_param_values=2,
    params=[
        _SurfaceParamSpec(
            name="location",
            start_idx=0,
            description="The location :math:`z_0` of the sphere center along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=0,
            description="The :math:`z`-coordinate :math:`z_0` of the sphere center",
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
    equation=lambda x, y, z, c: x**2 + y**2 + (z - c[0]) ** 2 - c[1] ** 2,
)


class XSphere(SphereOnAxis, metaclass=_SurfaceClassFactory, spec=_x_sphere_spec):
    """Represents surface SX: a sphere centered on the X-axis.

    The surface equation is:

    .. math::

        (x - x_0)^2 + y^2 + z^2 - R^2 = 0

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


class YSphere(SphereOnAxis, metaclass=_SurfaceClassFactory, spec=_y_sphere_spec):
    """Represents surface SY: a sphere centered on the Y-axis.

    The surface equation is:

    .. math::

        x^2 + (y - y_0)^2 + z^2 - R^2 = 0

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


class ZSphere(SphereOnAxis, metaclass=_SurfaceClassFactory, spec=_z_sphere_spec):
    """Represents surface SZ: a sphere centered on the Z-axis.

    The surface equation is:

    .. math::

        x^2 + y^2 + (z - z_0)^2 - R^2 = 0

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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
            description="The position :math:`x_0` (or :math:`y_0`, or :math:`z_0`)  of the cone apex along the axis",
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

        x^2 + y^2 - t^2 (z - z_0)^2 = 0

    The optional third surface constant selects a single nappe
    (``+1`` upper, ``-1`` lower); omitting it gives both nappes.
    Access it via :attr:`sign`.

    .. tip::

        Since version 1.4.0 this has not been the preferred class for working with ``KX``, ``KY``, and ``KZ`` surfaces.
        Instead :class:`~montepy.XCone`, :class:`~montepy.YCone`, and :class:`~montepy.ZCone` are preferred.
        There is no plan at this time to deprecate this class, but its use is not going to be promoted.

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    surface_type : Union[SurfaceType, str]
        The surface type to set for this object
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    COORDINATE = {SurfaceType.KX: "x", SurfaceType.KY: "y", SurfaceType.KZ: "z"}
    """Maps surface type to the axis name for the cone's apex."""

    _VARIABLE_NUM_PARAMS = True

    @property
    def sign(self):
        """The optional sign flag selecting a single nappe of the cone.

        A value of ``+1`` selects the upper nappe and ``-1`` the lower nappe.
        Returns ``None`` if the flag was not specified in the input.

        Returns
        -------
        int or None
        """
        sc = self.surface_constants
        if len(sc) > 2:
            return sc[2]
        return None

    @sign.setter
    @needs_full_ast
    def sign(self, value):
        if value is None:
            del self.sign
            return
        if value not in {1, -1}:
            raise ValueError(f"sign must be +1 or -1. {value} given.")
        if len(self._surface_constants) > 2:
            self._surface_constants[2].value = value
        else:
            node = self._generate_default_node(int, value)
            self._surface_constants.append(node)
            self._tree["data"].append(node)

    @sign.deleter
    @needs_full_ast
    def sign(self):
        if len(self._surface_constants) > 2:
            node = self._surface_constants.pop()
            self._tree["data"].remove(node)

    def _enforce_constants(self, _validation_call=False):
        n = len(self.surface_constants)
        if n not in {2, 3}:
            message = (
                f"A {type(self).__name__} must have 2 or 3 surface constants "
                f"(2 required + optional nappe flag), but {n} were given."
            )
            if not _validation_call:
                raise ValueError(message)
            raise IllegalState(message)


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
            description="The position :math:`x_0` of the cone apex along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="x",
            start_idx=0,
            description="The :math:`x`-coordinate :math:`x_0` of the cone apex",
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
    equation=lambda x, y, z, c: y**2 + z**2 - c[1] * (x - c[0]) ** 2,
)

_y_cone_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.KY},
    num_param_values=2,
    params=[
        _SurfaceParamSpec(
            name="apex",
            start_idx=0,
            description="The position :math:`y_0` of the cone apex along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=0,
            description="The :math:`y`-coordinate :math:`y_0` of the cone apex",
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
    equation=lambda x, y, z, c: x**2 + z**2 - c[1] * (y - c[0]) ** 2,
)

_z_cone_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.KZ},
    num_param_values=2,
    params=[
        _SurfaceParamSpec(
            name="apex",
            start_idx=0,
            description="The position :math:`z_0` of the cone apex along the axis",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=0,
            description="The :math:`z`-coordinate :math:`z_0` of the cone apex",
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
    equation=lambda x, y, z, c: x**2 + y**2 - c[1] * (z - c[0]) ** 2,
)


class XCone(ConeOnAxis, metaclass=_SurfaceClassFactory, spec=_x_cone_spec):
    """Represents surface KX: a cone whose apex lies on the X-axis.

    The surface equation is:

    .. math::

        y^2 + z^2 - t^2 (x - x_0)^2 = 0

    The optional third surface constant selects a single nappe
    (``+1`` upper, ``-1`` lower); omitting it gives both nappes.
    Access it via :attr:`sign`.

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


class YCone(ConeOnAxis, metaclass=_SurfaceClassFactory, spec=_y_cone_spec):
    """Represents surface KY: a cone whose apex lies on the Y-axis.

    The surface equation is:

    .. math::

        x^2 + z^2 - t^2 (y - y_0)^2 = 0

    The optional last surface constant selects a single nappe
    (``+1`` upper, ``-1`` lower); omitting it gives both nappes.
    Access it via :attr:`sign`.

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


class ZCone(ConeOnAxis, metaclass=_SurfaceClassFactory, spec=_z_cone_spec):
    """Represents surface KZ: a cone whose apex lies on the Z-axis.

    The surface equation is:

    .. math::

        x^2 + y^2 - t^2 (z - y_0)^2 = 0

    The optional last surface constant selects a single nappe
    (``+1`` upper, ``-1`` lower); omitting it gives both nappes.
    Access it via :attr:`sign`.

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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

    The optional last surface constant selects a single nappe
    (``+1`` upper, ``-1`` lower); omitting it gives both nappes.
    Access it via :attr:`sign`.

    .. tip::

        Since version 1.4.0 this has not been the preferred class for working with ``K/X``, ``K/Y``, and ``K/Z`` surfaces.
        Instead :class:`~montepy.XConeParAxis`, :class:`~montepy.YConeParAxis`, and :class:`~montepy.ZConeParAxis` are preferred.
        There is no plan at this time to deprecate this class, but its use is not going to be promoted.

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    surface_type : Union[SurfaceType, str]
        The surface type to set for this object
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    _VARIABLE_NUM_PARAMS = True

    @property
    def sign(self):
        """The optional sign flag selecting a single nappe of the cone.

        A value of ``+1`` selects the upper nappe and ``-1`` the lower nappe.
        Returns ``None`` if the flag was not specified in the input.

        Returns
        -------
        int or None
        """
        sc = self.surface_constants
        if len(sc) > 4:
            return sc[4]
        return None

    @sign.setter
    @needs_full_ast
    def sign(self, value):
        if value is None:
            del self.sign
            return
        if value not in {1, -1}:
            raise ValueError(f"sign must be +1 or -1. {value} given.")
        if len(self._surface_constants) > 4:
            self._surface_constants[4].value = value
        else:
            node = self._generate_default_node(int, value)
            self._surface_constants.append(node)
            self._tree["data"].append(node)

    @sign.deleter
    @needs_full_ast
    def sign(self):
        if len(self._surface_constants) > 4:
            node = self._surface_constants.pop()
            self._tree["data"].remove(node)

    def _enforce_constants(self, _validation_call=False):
        n = len(self.surface_constants)
        if n not in {4, 5}:
            message = (
                f"A {type(self).__name__} must have 4 or 5 surface constants "
                f"(4 required + optional nappe flag), but {n} were given."
            )
            if not _validation_call:
                raise ValueError(message)
            raise IllegalState(message)


# ---------------------------------------------------------------------------
# XConeParAxis, YConeParAxis, ZConeParAxis  (axis-specific)
# ---------------------------------------------------------------------------

_x_cone_par_axis_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.K_X},
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
    equation=lambda x, y, z, c: (y - c[1]) ** 2
    + (z - c[2]) ** 2
    - c[3] * (x - c[0]) ** 2,
)

_y_cone_par_axis_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.K_Y},
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
    equation=lambda x, y, z, c: (x - c[0]) ** 2
    + (z - c[2]) ** 2
    - c[3] * (y - c[1]) ** 2,
)

_z_cone_par_axis_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.K_Z},
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
    equation=lambda x, y, z, c: (x - c[0]) ** 2
    + (y - c[1]) ** 2
    - c[3] * (z - c[2]) ** 2,
)


class XConeParAxis(
    ConeParAxis, metaclass=_SurfaceClassFactory, spec=_x_cone_par_axis_spec
):
    """Represents surface K/X: a cone whose axis is parallel to the X-axis
    with its apex at an arbitrary point :math:`(x_0, y_0, z_0)`.

    The surface equation is:

    .. math::

        (y - y_0)^2 + (z - z_0)^2 - t^2 (x - x_0)^2 = 0

    The optional last surface constant selects a single nappe
    (``+1`` upper, ``-1`` lower); omitting it gives both nappes.
    Access it via :attr:`sign`.

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


class YConeParAxis(
    ConeParAxis, metaclass=_SurfaceClassFactory, spec=_y_cone_par_axis_spec
):
    """Represents surface K/Y: a cone whose axis is parallel to the Y-axis
    with its apex at an arbitrary point :math:`(x_0, y_0, z_0)`.

    The surface equation is:

    .. math::

        (x - x_0)^2 + (z - z_0)^2 - t^2 (y - y_0)^2 = 0

    The optional last surface constant selects a single nappe
    (``+1`` upper, ``-1`` lower); omitting it gives both nappes.
    Access it via :attr:`sign`.

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


class ZConeParAxis(
    ConeParAxis, metaclass=_SurfaceClassFactory, spec=_z_cone_par_axis_spec
):
    """Represents surface K/Z: a cone whose axis is parallel to the Z-axis
    with its apex at an arbitrary point :math:`(x_0, y_0, z_0)`.

    The surface equation is:

    .. math::

        (x - x_0)^2 + (y - y_0)^2 - t^2 (z - z_0)^2 = 0

    The optional last surface constant selects a single nappe
    (``+1`` upper, ``-1`` lower); omitting it gives both nappes.
    Access it via :attr:`sign`.

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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
    equation=lambda x, y, z, c: c[0] * (x - c[7]) ** 2
    + c[1] * (y - c[8]) ** 2
    + c[2] * (z - c[9]) ** 2
    + 2 * c[3] * (x - c[7])
    + 2 * c[4] * (y - c[8])
    + 2 * c[5] * (z - c[10])
    + c[6],
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

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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
    equation=lambda x, y, z, c: c[0] * x**2
    + c[1] * y**2
    + c[2] * z**2
    + c[3] * x * y
    + c[4] * y * z
    + c[5] * z * x
    + c[6] * x
    + c[7] * y
    + c[9] * z
    + c[10],
)


class GeneralQuadric(
    Surface, metaclass=_SurfaceClassFactory, spec=_general_quadric_spec
):
    """Represents surface GQ: a general quadric surface (cylinder, cone,
    ellipsoid, hyperboloid, or paraboloid) at arbitrary orientation.

    The surface equation is:

    .. math::

        Ax^2 + By^2 + Cz^2 + Dxy + Eyz + Fxz + Gx + Hy + Jz + K = 0

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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
            description="The :math:`x`-coordinate, :math:`x_0`, of the torus center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=1,
            description="The :math:`y`-coordinate, :math:`y_0`, of the torus center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=2,
            description="The :math:`z`-coordinate, :math:`z_0`, of the torus center",
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
            name="A",
            start_idx=3,
            description="Alias for :attr:`major_radius`",
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
            name="B",
            start_idx=4,
            description="Alias of :attr:`minor_radius_1`",
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
        _SurfaceParamSpec(
            name="C",
            start_idx=5,
            description="Alias of :attr:`minor_radius_2`",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
)


class Torus(Surface, metaclass=_SurfaceClassFactory, spec=_torus_spec):
    """Represents surfaces TX, TY, TZ: an elliptical torus whose axis of
    symmetry is parallel to a coordinate axis.

    The surface equation (e.g., for TZ) is:

    .. math::

        \\frac{(z-z_0)^2}{B^2} + \\frac{\\left(\\sqrt{(x-x_0)^2+(y-y_0)^2} - A\\right)^2}{C^2} - 1 = 0

    .. tip::

        Since version 1.4.0 this has not been the preferred class for working with ``TX``, ``TY``, and ``TZ`` surfaces.
        Instead :class:`~montepy.XTorus`, :class:`~montepy.YTorus`, and :class:`~montepy.ZTorus` are preferred.
        There is no plan at this time to deprecate this class, but its use is not going to be promoted.

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    surface_type : Union[SurfaceType, str]
        The surface type to set for this object
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    @property
    def minor_radius(self):
        """The minor radius of the torus when the tube cross-section is
        circular, i.e. when :attr:`minor_radius_1`, :math:`B`, and
        :attr:`minor_radius_2`, :math:`C`, are equal.

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


# ---------------------------------------------------------------------------
# XTorus, YTorus, ZTorus  (TX, TY, TZ — axis-specific)
# ---------------------------------------------------------------------------

_x_torus_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.TX},
    num_param_values=6,
    params=[
        _SurfaceParamSpec(
            name="x",
            start_idx=0,
            description="The :math:`x`-coordinate, :math:`x_0`, of the torus center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=1,
            description="The :math:`y`-coordinate, :math:`y_0`, of the torus center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=2,
            description="The :math:`z`-coordinate, :math:`z_0`, of the torus center",
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
            name="A",
            start_idx=3,
            description="Alias for :attr:`major_radius`",
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
            name="B",
            start_idx=4,
            description="Alias of :attr:`minor_radius_1`",
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
        _SurfaceParamSpec(
            name="C",
            start_idx=5,
            description="Alias of :attr:`minor_radius_2`",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
    equation=lambda x, y, z, c: (np.sqrt((y - c[1]) ** 2 + (z - c[2]) ** 2) - c[3]) ** 2
    / c[4] ** 2
    + (x - c[0]) ** 2 / c[5] ** 2
    - 1,
)

_y_torus_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.TY},
    num_param_values=6,
    params=[
        _SurfaceParamSpec(
            name="x",
            start_idx=0,
            description="The :math:`x`-coordinate, :math:`x_0`, of the torus center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=1,
            description="The :math:`y`-coordinate, :math:`y_0`, of the torus center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=2,
            description="The :math:`z`-coordinate, :math:`z_0`, of the torus center",
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
            name="A",
            start_idx=3,
            description="Alias for :attr:`major_radius`",
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
            name="B",
            start_idx=4,
            description="Alias of :attr:`minor_radius_1`",
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
        _SurfaceParamSpec(
            name="C",
            start_idx=5,
            description="Alias of :attr:`minor_radius_2`",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
    equation=lambda x, y, z, c: (np.sqrt((x - c[0]) ** 2 + (z - c[2]) ** 2) - c[3]) ** 2
    / c[4] ** 2
    + (y - c[1]) ** 2 / c[5] ** 2
    - 1,
)

_z_torus_spec = _SurfaceTypeSpec(
    surface_types={SurfaceType.TZ},
    num_param_values=6,
    params=[
        _SurfaceParamSpec(
            name="x",
            start_idx=0,
            description="The :math:`x`-coordinate, :math:`x_0`, of the torus center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="y",
            start_idx=1,
            description="The :math:`y`-coordinate, :math:`y_0`, of the torus center",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="z",
            start_idx=2,
            description="The :math:`z`-coordinate, :math:`z_0`, of the torus center",
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
            name="A",
            start_idx=3,
            description="Alias for :attr:`major_radius`",
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
            name="B",
            start_idx=4,
            description="Alias of :attr:`minor_radius_1`",
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
        _SurfaceParamSpec(
            name="C",
            start_idx=5,
            description="Alias of :attr:`minor_radius_2`",
            types=(float, int),
            base_type=float,
            validator=_enforce_positive_radius,
        ),
    ],
    equation=lambda x, y, z, c: (np.sqrt((x - c[0]) ** 2 + (y - c[1]) ** 2) - c[3]) ** 2
    / c[4] ** 2
    + (z - c[2]) ** 2 / c[5] ** 2
    - 1,
)


class XTorus(Torus, metaclass=_SurfaceClassFactory, spec=_x_torus_spec):
    """Represents surface TX: a torus whose axis of symmetry is the X-axis.

    The surface equation is:

    .. math::

        \\frac{(x-x_0)^2}{B^2} + \\frac{\\left(\\sqrt{(y-y_0)^2+(z-z_0)^2} - A\\right)^2}{C^2} - 1 = 0

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


class YTorus(Torus, metaclass=_SurfaceClassFactory, spec=_y_torus_spec):
    """Represents surface TY: a torus whose axis of symmetry is the Y-axis.

    The surface equation is:

    .. math::

        \\frac{(y-y_0)^2}{B^2} + \\frac{\\left(\\sqrt{(x-x_0)^2+(z-z_0)^2} - A\\right)^2}{C^2} - 1 = 0

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


class ZTorus(Torus, metaclass=_SurfaceClassFactory, spec=_z_torus_spec):
    """Represents surface TZ: a torus whose axis of symmetry is the Z-axis.

    The surface equation is:

    .. math::

        \\frac{(z-z_0)^2}{B^2} + \\frac{\\left(\\sqrt{(x-x_0)^2+(y-y_0)^2} - A\\right)^2}{C^2} - 1 = 0

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass


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
            description="Face 1 descriptor — digit string of up to 4 vertex indices",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="facet_2",
            start_idx=25,
            description="Face 2 descriptor — digit string of up to 4 vertex indices",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="facet_3",
            start_idx=26,
            description="Face 3 descriptor — digit string of up to 4 vertex indices",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="facet_4",
            start_idx=27,
            description="Face 4 descriptor — digit string of up to 4 vertex indices",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="facet_5",
            start_idx=28,
            description="Face 5 descriptor — digit string of up to 4 vertex indices",
            types=(float, int),
            base_type=float,
        ),
        _SurfaceParamSpec(
            name="facet_6",
            start_idx=29,
            description="Face 6 descriptor — digit string of up to 4 vertex indices",
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

    .. versionadded:: 1.4.0

    .. versionchanged:: 1.5.0

        Added ``jit_parse`` parameter

    Parameters
    ----------
    input : InitInput
        The Input object representing the input
    number : PositiveInt
        The number to set for this object.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    pass
