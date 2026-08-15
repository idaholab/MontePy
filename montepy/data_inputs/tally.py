# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
import copy
from typing import Generator

import montepy
from montepy.cells import Cells
from montepy.surface_collection import Surfaces
from montepy.data_inputs.data_input import DataInputAbstract
from montepy.data_inputs import tally_multiplier
from montepy.data_inputs.tally_type import Score, TallyType
from montepy.exceptions import MalformedInputError, NumberConflictError
from montepy.input_parser.tally_parser import TallyParser
from montepy.input_parser import syntax_node
from montepy.numbered_mcnp_object import Numbered_MCNP_Object
import montepy.types as ty
from montepy.utilities import *
from montepy.mcnp_object import InitInput

_TALLY_TYPE_MODULUS = 10


class LatticeIndex:
    """A lattice element index ``[i j k]`` in a tally path specification.

    .. versionadded:: 1.6.0b2

    Parameters
    ----------
    dimensions : list
        List of :class:`int` (single element index) or
        ``tuple[int, int]`` (range ``i1:i2``).
    """

    __slots__ = ("_dimensions",)

    @args_checked
    def __init__(self, dimensions: list[ty.Integral | tuple[ty.Integral, ty.Integral]]):
        self._dimensions = list(dimensions)

    @property
    def dimensions(self):
        """The list of indices or (start, end) ranges."""
        return list(self._dimensions)

    def __repr__(self):
        return f"LatticeIndex({self._dimensions})"


class TallyGroup:
    """Abstract base for a tally scoring group.

    .. versionadded:: 1.6.0b2
    """

    def __contains__(self, item) -> bool:
        raise NotImplementedError


class Filter:
    """Abstract analog of an OpenMC-style tally filter.

    .. versionadded:: 1.6.0b2
    """


class ParticleFilter(Filter):
    """Filters a tally to the particle types in its classifier (e.g. ``:n,p``).

    .. versionadded:: 1.6.0b2

    Parameters
    ----------
    particles : list[montepy.Particle]
        The particles this tally is restricted to.
    """

    __slots__ = ("_particles",)

    @args_checked
    def __init__(self, particles: list[montepy.Particle] | set[montepy.Particle]):
        self._particles = list(particles)

    @property
    def particles(self):
        """The particles this tally is restricted to."""
        return list(self._particles)

    def __eq__(self, other):
        return isinstance(other, ParticleFilter) and self._particles == other._particles

    def __repr__(self):
        return f"ParticleFilter({self._particles})"


class SpatialFilter(Filter):
    """Filters a tally to its scoring bins (cells, surfaces, or paths).

    A thin wrapper around a :class:`~montepy.Tally`'s :attr:`~montepy.Tally.groups`.

    .. versionadded:: 1.6.0b2

    Parameters
    ----------
    groups : list[TallyGroup]
        The scoring bins.
    """

    __slots__ = ("_groups",)

    @args_checked
    def __init__(self, groups: list[TallyGroup]):
        self._groups = list(groups)

    @property
    def groups(self):
        """The scoring bins (:class:`~montepy.data_inputs.tally.TallyGroup` objects) this filter covers."""
        return list(self._groups)

    def __eq__(self, other):
        return isinstance(other, SpatialFilter) and self._groups == other._groups

    def __repr__(self):
        return f"SpatialFilter({self._groups})"


class FlatGroup(TallyGroup):
    """A flat list of cells/surfaces to score over.

    Used as both a top-level bin and as an individual level in a
    :class:`PathGroup` chain.

    .. versionadded:: 1.6.0b2

    Parameters
    ----------
    numbers : list[int]
        Cell or surface numbers.
    lattice_indices : list[LatticeIndex | None], optional
        Lattice indices parallel to ``numbers``.
    is_grouped : bool
        ``True`` = parenthesized union (one averaged bin);
        ``False`` = separate bins.
    universe_spec : int, optional
        Universe number if ``U=N`` syntax was used.
    """

    __slots__ = (
        "_old_numbers",
        "_lattice_indices",
        "_is_grouped",
        "_universe_spec",
        "_cells_or_surfaces",
    )

    @args_checked
    def __init__(
        self,
        numbers: list[ty.Integral],
        lattice_indices: list[LatticeIndex | None] | None = None,
        *,
        is_grouped: bool,
        universe_spec: ty.Integral | None = None,
    ):
        self._old_numbers = list(numbers)
        self._lattice_indices = lattice_indices or [None] * len(self._old_numbers)
        self._is_grouped = is_grouped
        self._universe_spec = universe_spec
        self._cells_or_surfaces = []

    @property
    def old_numbers(self):
        """The original cell/surface numbers as read."""
        return list(self._old_numbers)

    @property
    def is_grouped(self):
        """``True`` if entries form a union bin (parenthesized)."""
        return self._is_grouped

    @property
    def universe_spec(self):
        """Universe number if ``U=N`` syntax was used, else ``None``."""
        return self._universe_spec

    def __contains__(self, item) -> bool:
        if self._cells_or_surfaces:
            return item in self._cells_or_surfaces
        for num in self._old_numbers:
            if hasattr(item, "old_number") and item.old_number == num:
                return True
            if hasattr(item, "number") and item.number == num:
                return True
        return False

    def __repr__(self):
        return f"FlatGroup({self._old_numbers}, grouped={self._is_grouped})"


class PathGroup(TallyGroup):
    """A universe-path group for repeated-structures tallies.

    .. versionadded:: 1.6.0b2

    Parameters
    ----------
    levels : list[FlatGroup]
        Levels in the ``<`` chain, innermost (scored) first.
    """

    __slots__ = ("_levels",)

    @args_checked
    def __init__(self, levels: list[FlatGroup]):
        self._levels = list(levels)

    @property
    def levels(self):
        """FlatGroup levels, innermost (scored) first."""
        return list(self._levels)

    @args_checked
    def inside(
        self,
        *cells_or_surfaces: montepy.Cell | montepy.Surface,
        lattice: list[ty.Integral] | None = None,
    ) -> PathGroup:
        """Append an outer level and return self for chaining.

        Parameters
        ----------
        cells_or_surfaces : Cell | Surface
            Objects at this level.
        lattice : list[int], optional
            Lattice index dimensions for the first element.

        Returns
        -------
        PathGroup
            ``self``, for method chaining.
        """
        numbers = [obj.number for obj in cells_or_surfaces]
        indices = [None] * len(numbers)
        if lattice is not None and numbers:
            indices[0] = LatticeIndex(lattice)
        is_grouped = len(cells_or_surfaces) > 1
        self._levels.append(FlatGroup(numbers, indices, is_grouped=is_grouped))
        return self

    def __contains__(self, item) -> bool:
        if not self._levels:
            return False
        return item in self._levels[0]

    def __repr__(self):
        return f"PathGroup(levels={len(self._levels)})"


def _parse_lattice_phrase(lattice_node) -> LatticeIndex:
    """Parse a ``ListNode("lattice phrase")`` into a :class:`LatticeIndex`."""
    dimensions = []
    for n in lattice_node.nodes:
        if isinstance(n, syntax_node.PaddingNode):
            continue
        if isinstance(n, syntax_node.ListNode) and n.name == "lattice range":
            vals = [m.value for m in n.nodes if isinstance(m, syntax_node.ValueNode)]
            if len(vals) >= 2:
                dimensions.append((int(vals[0]), int(vals[1])))
        elif isinstance(n, syntax_node.ValueNode) and isinstance(n.value, (int, float)):
            dimensions.append(int(n.value))
    return LatticeIndex(dimensions)


def _extract_numbers_with_lattice(nodes):
    """Pair each numeric ValueNode with its immediately following lattice phrase.

    Returns ``(numbers, lattice_indices)`` where ``lattice_indices[i]`` is a
    :class:`LatticeIndex` or ``None``.
    """
    numbers = []
    lattice_indices = []
    i = 0
    while i < len(nodes):
        n = nodes[i]
        if (
            isinstance(n, syntax_node.ValueNode)
            and isinstance(n.value, (int, float))
            and not isinstance(n.value, bool)
        ):
            numbers.append(int(n.value))
            if (
                i + 1 < len(nodes)
                and isinstance(nodes[i + 1], syntax_node.ListNode)
                and nodes[i + 1].name == "lattice phrase"
            ):
                lattice_indices.append(_parse_lattice_phrase(nodes[i + 1]))
                i += 2
                continue
            else:
                lattice_indices.append(None)
        i += 1
    return numbers, lattice_indices


def _extract_universe_spec_from_nodes(nodes):
    """Extract universe number from nodes that may contain a universe_phrase ListNode."""
    for n in nodes:
        if isinstance(n, syntax_node.ListNode) and n.name == "universe phrase":
            for m in n.nodes:
                if isinstance(m, syntax_node.ValueNode) and isinstance(
                    m.value, (int, float)
                ):
                    return int(m.value)
        elif isinstance(n, syntax_node.ListNode) and n.name == "tally group":
            inner = list(n.nodes)[1:-1]
            result = _extract_universe_spec_from_nodes(inner)
            if result is not None:
                return result
    return None


def _parse_body_segment(nodes, *, is_grouped) -> FlatGroup:
    numbers, lattice_indices = _extract_numbers_with_lattice(nodes)
    universe_spec = _extract_universe_spec_from_nodes(nodes)
    return FlatGroup(
        numbers, lattice_indices, is_grouped=is_grouped, universe_spec=universe_spec
    )


def _parse_segment_as_level(seg) -> FlatGroup:
    """Parse a path segment (between ``<`` separators) into a :class:`FlatGroup` level."""
    non_pad = [n for n in seg if not isinstance(n, syntax_node.PaddingNode)]
    if (
        len(non_pad) == 1
        and isinstance(non_pad[0], syntax_node.ListNode)
        and non_pad[0].name == "tally group"
    ):
        inner_body = list(non_pad[0].nodes)[1:-1]
        return _parse_body_segment(inner_body, is_grouped=True)
    return _parse_body_segment(seg, is_grouped=False)


def _parse_tally_group_node(group_node) -> TallyGroup:
    nodes = list(group_node.nodes)
    body = nodes[1:-1] if len(nodes) >= 2 else nodes

    path_sep_indices = [
        i
        for i, n in enumerate(body)
        if (
            isinstance(n, syntax_node.ValueNode)
            and isinstance(n.value, str)
            and n.value.strip() == "<"
        )
    ]

    if not path_sep_indices:
        return _parse_body_segment(body, is_grouped=True)

    segments = []
    start = 0
    for sep_i in path_sep_indices:
        segments.append(body[start:sep_i])
        start = sep_i + 1
    segments.append(body[start:])

    return PathGroup([_parse_segment_as_level(seg) for seg in segments])


def _parse_tally_numbers(tally_numbers_node) -> list[TallyGroup]:
    groups = []
    for node in tally_numbers_node:
        if isinstance(node, syntax_node.ValueNode):
            v = node.value
            if v is None:
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                groups.append(FlatGroup([int(v)], is_grouped=False))
        elif isinstance(node, syntax_node.ListNode) and node.name == "tally group":
            groups.append(_parse_tally_group_node(node))
    return groups


class Tally(DataInputAbstract, Numbered_MCNP_Object):
    """Base class for MCNP F-card tallies (F1, F2, F4, F5, F6, F7, F8).

    Use :meth:`from_input` as a factory to create the appropriate subclass
    when reading from a file.

    .. versionadded:: 1.6.0b2
    """

    _POINTER_ATTRS = set()
    _DEFAULT_SCORES = ()
    _KEYS_TO_PRESERVE = {"_multiplier"}

    @staticmethod
    def _parser():
        return TallyParser()

    def _init_blank(self):
        super()._init_blank()
        self._old_number = self._generate_default_node(int, -1)
        self._groups = []
        self._include_total = False
        self._multiplier = None

    def _jit_light_init(self, input):
        super()._jit_light_init(input)
        self._old_number = self._input_number

    def _parse_tree(self):
        super()._parse_tree()
        num = self._input_number
        self._old_number = copy.deepcopy(num)
        self._number = num
        self._parse_tally_body()

    def _generate_default_tree(self, **kwargs):
        ret = {}
        ret["start_pad"] = syntax_node.PaddingNode()
        ret["classifier"] = syntax_node.ClassifierNode()
        ret["classifier"].prefix = syntax_node.ValueNode(
            self._class_prefix().upper(), str, padding=None, never_pad=True
        )
        ret["classifier"].number = self._generate_default_node(int, -1)
        ret["keyword"] = syntax_node.ValueNode(None, str, padding=None)
        tally_numbers = syntax_node.ListNode("tally numbers")
        end_node = syntax_node.ValueNode(None, str)
        ret["data"] = syntax_node.SyntaxNode(
            "tally list", {"tally": tally_numbers, "end": end_node}
        )
        ret["parameters"] = syntax_node.ParametersNode()
        self._tree = syntax_node.SyntaxNode("blank data tree", ret)

    @args_checked
    def __init__(
        self,
        input: InitInput = None,
        number: ty.PositiveInt = None,
        *,
        jit_parse: bool = True,
    ):
        Numbered_MCNP_Object.__init__(self, input, number, jit_parse=jit_parse)

    @staticmethod
    def _class_prefix() -> str:
        return "f"

    @staticmethod
    def _has_number() -> bool:
        return True

    @staticmethod
    def _has_classifier() -> int:
        return 1

    @staticmethod
    def _parent_collections():
        return ()

    def _parse_tally_body(self):
        if self._input is None:
            return
        num = self._input_number.value
        try:
            TallyType(num % _TALLY_TYPE_MODULUS)
        except ValueError as e:
            raise MalformedInputError(self._input, f"Invalid tally type digit: {e}")
        tally_list = self._tree["data"]
        end_node = tally_list["end"]
        self._include_total = (
            end_node.value is not None and str(end_node.value).upper() == "T"
        )
        self._groups = _parse_tally_numbers(tally_list["tally"])

    def _number_validator(self, number):
        tally_type = getattr(type(self), "_TALLY_TYPE", None)
        if tally_type is not None and number % _TALLY_TYPE_MODULUS != tally_type.value:
            raise ValueError(
                f"Cannot change tally type via number setter; "
                f"expected last digit {tally_type.value}, "
                f"got {number % _TALLY_TYPE_MODULUS}."
            )
        super()._number_validator(number)

    @make_prop_val_node("_old_number")
    def old_number(self):
        """The tally number as read from the input file."""
        pass

    @property
    @needs_full_ast
    def tally_type(self) -> TallyType | None:
        """The MCNP tally type (e.g. ``TallyType.CELL_FLUX`` for F4)."""
        return getattr(type(self), "_TALLY_TYPE", None)

    @property
    @needs_full_ast
    def groups(self) -> list[TallyGroup]:
        """The list of :class:`~montepy.data_inputs.tally.TallyGroup` objects defining what is scored."""
        return list(self._groups)

    @property
    @needs_full_ast
    def include_total(self) -> bool:
        """``True`` if a total bin (T) is appended."""
        return self._include_total

    @make_prop_pointer("_multiplier", tally_multiplier.TallyMultiplier)
    def multiplier(self) -> tally_multiplier.TallyMultiplier:
        """The ``FM`` tally-multiplier card linked to this tally, if any.

        Returns
        -------
        TallyMultiplier
        """
        pass

    @property
    @needs_full_ast
    def scores(self) -> list[Score] | list[tally_multiplier.MultiplierScore]:
        """The physical quantities this tally scores, e.g. ``[Score.FLUX]`` for F4.

        This is just the quantity implied by the tally type digit, unless an
        ``FM`` tally-multiplier card is linked (see :attr:`multiplier`), in
        which case this returns one :class:`~montepy.data_inputs.tally_multiplier.MultiplierScore`
        per output bin the multiplier defines instead.
        """
        if self.multiplier is not None:
            return [score for bin_ in self.multiplier.bins for score in bin_.scores]
        return list(self._DEFAULT_SCORES)

    @property
    @needs_full_ast
    def filters(self) -> list[Filter]:
        """A shallow analog of OpenMC's tally filters.

        Defaults to a :class:`~montepy.data_inputs.tally.ParticleFilter` (from
        :attr:`particle_classifiers`) and a
        :class:`~montepy.data_inputs.tally.SpatialFilter` (from :attr:`groups`),
        whichever are present.
        """
        filters = []
        if self.particle_classifiers:
            filters.append(ParticleFilter(self.particle_classifiers))
        if self._groups:
            filters.append(SpatialFilter(self._groups))
        return filters

    @needs_full_ast
    def __contains__(self, item) -> bool:
        for group in self._groups:
            if item in group:
                return True
        return False

    @staticmethod
    def _dispatch_class(input, num: int) -> type[Tally]:
        """The :class:`Tally` subclass for a tally number."""
        try:
            tally_type = TallyType(num % _TALLY_TYPE_MODULUS)
        except ValueError as e:
            raise MalformedInputError(
                input, f"Tally type digit {num % _TALLY_TYPE_MODULUS} is not valid."
            ) from e
        # _TALLY_TYPE_MAP's keys are exactly TallyType's members (both
        # defined by hand in lockstep in this module), so this can never miss.
        return _TALLY_TYPE_MAP[tally_type]

    @classmethod
    def from_input(cls, input, *, jit_parse: bool = True) -> Tally:
        """Factory: create the appropriate :class:`Tally` subclass from an input.

        Parameters
        ----------
        input : Input | str
            The raw MCNP input object.
        jit_parse : bool
            Whether to defer full parsing.

        Returns
        -------
        Tally
            An instance of the correct subclass for the tally type digit.
        """
        try:
            bare_tree = Tally._peek_light_parse(input)
            number_node = bare_tree.nodes["classifier"].number
            if number_node is None:
                raise ValueError("Tally classifier has no number.")
            subclass = Tally._dispatch_class(input, number_node.value)
        except Exception:
            # The JIT light parser isn't fully robust and can fail on valid
            # syntax. Fall back to building a real Tally: its own
            # JIT-with-fallback-to-full-parse handling in _parse_input will
            # reliably determine the number instead of guessing, and gives
            # proper file/line context on error.
            base = Tally(input, jit_parse=True)
            subclass = Tally._dispatch_class(input, base._number.value)

        return subclass(input, jit_parse=jit_parse)

    def link_to_problem(self, problem, *, deepcopy=False):
        super().link_to_problem(problem)

    def _update_values(self):
        pass

    @staticmethod
    def _align_to_type(tally_type: TallyType, start: int) -> int:
        """The smallest number ``>= start`` whose last digit matches ``tally_type``."""
        aligned = start - (start % 10) + tally_type.value
        if aligned < start:
            aligned += 10
        return aligned

    def _next_number_for_type(
        self, tally_type: TallyType, starting_number, step
    ) -> int:
        """Finds the next free tally number matching ``tally_type``'s digit.

        Note
        ----
        This probes with :meth:`~montepy.numbered_object_collection.NumberedObjectCollection.check_number`
        rather than delegating to :meth:`~montepy.numbered_object_collection.NumberedObjectCollection.request_number`,
        because that method tracks a single collection-wide
        ``_last_assigned_number`` ratchet that isn't digit-aware: a prior
        request for one tally-type digit (e.g. ``clone()`` landing on 124)
        pushes that ratchet past 124, so a later request for a *different*
        digit (e.g. ``clone_as`` targeting type 6) would start its search
        from >134 instead of the correctly-aligned 6, and drift to a number
        that still doesn't end in 6.
        """
        collection = self._problem.tallies if self._problem else None
        if collection is not None:
            start = (
                starting_number
                if starting_number is not None
                else collection.starting_number
            )
            step = step if step is not None else collection.step
        else:
            start = starting_number if starting_number is not None else 1
            step = step if step is not None else 1
        candidate = self._align_to_type(tally_type, start)
        while True:
            if collection is not None:
                try:
                    collection.check_number(candidate)
                    return candidate
                except NumberConflictError:
                    pass
            elif candidate != self.number:
                return candidate
            candidate += step * 10

    @staticmethod
    def _tally_category(cls: type[Tally]) -> type[Tally] | None:
        """Which of {SurfaceTally, CellTally, DetectorTally} ``cls`` belongs to."""
        for category in (SurfaceTally, CellTally, DetectorTally):
            if issubclass(cls, category):
                return category
        return None

    @args_checked
    @needs_full_cst
    def clone(
        self,
        starting_number: ty.PositiveInt = None,
        step: ty.PositiveInt = None,
    ) -> Tally:
        """Clone this tally with a new number.

        Note that the clone does **not** carry over a linked ``FM``
        multiplier (see :attr:`multiplier`) -- a multiplier is a companion
        card tied to this exact tally number, not something that
        meaningfully transfers to a renumbered copy.

        See :meth:`~montepy.numbered_mcnp_object.Numbered_MCNP_Object.clone`.
        """
        ret = copy.deepcopy(self)
        ret._multiplier = None
        new_number = self._next_number_for_type(self.tally_type, starting_number, step)
        if self._problem:
            ret.link_to_problem(self._problem)
            ret.number = new_number
            self._problem.tallies.append(ret)
        else:
            ret.number = new_number
        return ret

    @args_checked
    @needs_full_cst
    def clone_as(
        self,
        new_type: TallyType | type[Tally],
        starting_number: ty.PositiveInt = None,
        step: ty.PositiveInt = None,
    ) -> Tally:
        """Clone this tally as a different tally type, keeping the same scoring geometry.

        For example, this can turn an F4 cell-flux tally into an F6
        energy-deposition tally scoring the same cells:

        .. code-block:: python

            from montepy.data_inputs.tally import F6Tally
            from montepy.data_inputs.tally_type import TallyType

            heating = flux_tally.clone_as(F6Tally)
            # or, equivalently:
            heating = flux_tally.clone_as(TallyType.ENERGY_DEPOSITION)

        Only conversions within the same tally category are allowed:
        F1/F2 (surface-based) convert freely among each other, as do
        F4/F6/F7/F8 (cell-based); F5 (point/ring detector) has no
        cell/surface geometry to carry over and can't be converted to or
        from.

        Parameters
        ----------
        new_type : TallyType, type[Tally]
            The target tally type, either as a :class:`TallyType` member or
            as a :class:`Tally` subclass (e.g. ``montepy.F6Tally``).
        starting_number : int
            The starting number to request for the new object's number.
        step : int
            The step size to use to find a new valid number.

        Returns
        -------
        Tally
            A new tally of the requested type, with the same scoring groups.

        Note
        ----
        The clone does **not** carry over a linked ``FM`` multiplier (see
        :attr:`multiplier`) -- a multiplier is a companion card tied to this
        exact tally number, not something that meaningfully transfers to a
        retyped/renumbered copy.
        """
        if isinstance(new_type, TallyType):
            # _TALLY_TYPE_MAP's keys are exactly TallyType's members (both
            # defined by hand in lockstep in this module), so this can never
            # miss.
            target_cls = _TALLY_TYPE_MAP[new_type]
        elif isinstance(new_type, type) and issubclass(new_type, Tally):
            target_cls = new_type
        else:
            raise TypeError(
                f"new_type must be a TallyType or a Tally subclass, got {new_type!r}."
            )

        if self._tally_category(type(self)) != self._tally_category(target_cls):
            raise ValueError(
                f"Cannot clone a {type(self).__name__} (tally type "
                f"{self.tally_type}) as a {target_cls.__name__} (tally type "
                f"{target_cls._TALLY_TYPE}); incompatible tally categories."
            )

        if target_cls is type(self):
            return self.clone(starting_number, step)

        ret = copy.deepcopy(self)
        ret.__class__ = target_cls
        ret._multiplier = None
        new_number = self._next_number_for_type(
            target_cls._TALLY_TYPE, starting_number, step
        )
        if self._problem:
            ret.link_to_problem(self._problem)
            ret.number = new_number
            self._problem.tallies.append(ret)
        else:
            ret.number = new_number
        return ret

    def __str__(self):
        try:
            return f"TALLY: {self.number}"
        except Exception:
            return "TALLY: (unparsed)"

    def __repr__(self):
        try:
            ttype = getattr(type(self), "_TALLY_TYPE", None)
            ngroups = len(getattr(self, "_groups", []))
            return f"TALLY: {self.number}, type: {ttype}, groups: {ngroups}"
        except Exception:
            return "TALLY: (unparsed)"


class SurfaceTally(Tally):
    """Intermediate class for tallies that score on surfaces (F1, F2).

    .. versionadded:: 1.6.0b2
    """

    def _init_blank(self):
        super()._init_blank()
        self._surfaces = Surfaces()

    @property
    @needs_full_ast
    def surfaces(self) -> Surfaces:
        """The surfaces this tally scores over."""
        return self._surfaces

    @args_checked
    @needs_full_cst
    def add_surface(self, surface: montepy.Surface) -> None:
        """Add a single surface as a separate scoring bin.

        Parameters
        ----------
        surface : Surface
            The surface to add.
        """
        self._groups.append(FlatGroup([surface.number], is_grouped=False))
        if surface not in self._surfaces:
            self._surfaces.append(surface)

    @args_checked
    @needs_full_cst
    def add_group(self, surfaces: list[montepy.Surface] | set[montepy.Surface]) -> None:
        """Add surfaces as a single union (averaged) bin.

        Parameters
        ----------
        surfaces : list[Surface], set[Surface]
            The surfaces to group.
        """
        surfaces = list(surfaces)
        numbers = [s.number for s in surfaces]
        self._groups.append(FlatGroup(numbers, is_grouped=True))
        for s in surfaces:
            if s not in self._surfaces:
                self._surfaces.append(s)

    @args_checked
    @needs_full_cst
    def add_path_group(self, *surfaces: montepy.Surface) -> PathGroup:
        """Add a universe-path group rooted at the given surfaces.

        Returns the :class:`~montepy.data_inputs.tally.PathGroup` for chaining via :meth:`~montepy.data_inputs.tally.PathGroup.inside`.

        Parameters
        ----------
        surfaces : Surface
            The innermost-level surfaces.

        Returns
        -------
        PathGroup
            The new path group (already appended).
        """
        numbers = [s.number for s in surfaces]
        is_grouped = len(surfaces) > 1
        first_level = FlatGroup(numbers, is_grouped=is_grouped)
        pg = PathGroup([first_level])
        self._groups.append(pg)
        return pg

    def link_to_problem(self, problem, *, deepcopy=False):
        super().link_to_problem(problem)
        if problem is not None and not hasattr(self, "_not_parsed"):
            # Rebuild from scratch: a deepcopy (e.g. from clone()) carries
            # stale copied Surface objects that must be discarded, not
            # merged with the live ones from `problem`.
            self._surfaces = Surfaces()
            for group in self._groups:
                self._link_group_surfaces(group, problem)

    def _link_group_surfaces(self, group, problem):
        if isinstance(group, FlatGroup):
            group._cells_or_surfaces = []
            for num in group._old_numbers:
                try:
                    # Use _surfaces directly to avoid triggering __relink_objs via the property.
                    surface = problem._surfaces[num]
                except KeyError:
                    continue
                group._cells_or_surfaces.append(surface)
                try:
                    self._surfaces[surface.number]
                except KeyError:
                    self._surfaces.append(surface)
        elif isinstance(group, PathGroup):
            for level in group._levels:
                self._link_group_surfaces(level, problem)


class CellTally(Tally):
    """Intermediate class for tallies that score in cells (F4, F6, F7, F8).

    .. versionadded:: 1.6.0b2
    """

    def _init_blank(self):
        super()._init_blank()
        self._cells = Cells()

    @property
    @needs_full_ast
    def cells(self) -> Cells:
        """The cells this tally scores in."""
        return self._cells

    @args_checked
    @needs_full_cst
    def add_cell(self, cell: montepy.Cell) -> None:
        """Add a single cell as a separate scoring bin.

        Parameters
        ----------
        cell : Cell
            The cell to add.
        """
        self._groups.append(FlatGroup([cell.number], is_grouped=False))
        if cell not in self._cells:
            self._cells.append(cell)

    @args_checked
    @needs_full_cst
    def add_group(self, cells: list[montepy.Cell] | set[montepy.Cell]) -> None:
        """Add cells as a single union (averaged) bin.

        Parameters
        ----------
        cells : list[Cell], set[Cell]
            The cells to group.
        """
        cells = list(cells)
        numbers = [c.number for c in cells]
        self._groups.append(FlatGroup(numbers, is_grouped=True))
        for c in cells:
            if c not in self._cells:
                self._cells.append(c)

    @args_checked
    @needs_full_cst
    def add_path_group(self, *cells: montepy.Cell) -> PathGroup:
        """Add a universe-path group rooted at the given cells.

        Returns the :class:`~montepy.data_inputs.tally.PathGroup` for chaining via :meth:`~montepy.data_inputs.tally.PathGroup.inside`.

        Parameters
        ----------
        cells : Cell
            The innermost-level cells.

        Returns
        -------
        PathGroup
            The new path group (already appended).
        """
        numbers = [c.number for c in cells]
        is_grouped = len(cells) > 1
        first_level = FlatGroup(numbers, is_grouped=is_grouped)
        pg = PathGroup([first_level])
        self._groups.append(pg)
        return pg

    def link_to_problem(self, problem, *, deepcopy=False):
        super().link_to_problem(problem)
        if problem is not None and not hasattr(self, "_not_parsed"):
            # Rebuild from scratch: a deepcopy (e.g. from clone()) carries
            # stale copied Cell objects that must be discarded, not merged
            # with the live ones from `problem`.
            self._cells = Cells()
            for group in self._groups:
                self._link_group_cells(group, problem)

    def _link_group_cells(self, group, problem):
        if isinstance(group, FlatGroup):
            group._cells_or_surfaces = []
            for num in group._old_numbers:
                try:
                    # Use _cells directly to avoid triggering __relink_objs via the property.
                    cell = problem._cells[num]
                except KeyError:
                    continue
                group._cells_or_surfaces.append(cell)
                try:
                    self._cells[cell.number]
                except KeyError:
                    self._cells.append(cell)
        elif isinstance(group, PathGroup):
            if group._levels:
                self._link_group_cells(group._levels[0], problem)


class DetectorTally(Tally):
    """F5: point/ring detector tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.DETECTOR
    _DEFAULT_SCORES = (Score.FLUX,)


# ── Concrete subclasses ────────────────────────────────────────────────────────


class SurfaceCurrentTally(SurfaceTally):
    """F1: surface current tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.CURRENT
    _DEFAULT_SCORES = (Score.CURRENT,)


class SurfaceFluxTally(SurfaceTally):
    """F2: average surface flux tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.SURFACE_FLUX
    _DEFAULT_SCORES = (Score.FLUX,)


class CellFluxTally(CellTally):
    """F4: cell flux tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.CELL_FLUX
    _DEFAULT_SCORES = (Score.FLUX,)


class EnergyDepositionTally(CellTally):
    """F6: energy deposition tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.ENERGY_DEPOSITION
    _DEFAULT_SCORES = (Score.ENERGY_DEPOSITION,)


class FissionEnergyDepositionTally(CellTally):
    """F7: fission energy deposition tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.FISSION_ENERGY_DEPOSITION
    _DEFAULT_SCORES = (Score.FISSION_ENERGY_DEPOSITION,)


class EnergyDetectorPulseTally(CellTally):
    """F8: energy-detector pulse height tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.ENERGY_DETECTOR_PULSE
    _DEFAULT_SCORES = (Score.PULSE_HEIGHT,)


_TALLY_TYPE_MAP: dict[TallyType, type[Tally]] = {
    TallyType.CURRENT: SurfaceCurrentTally,
    TallyType.SURFACE_FLUX: SurfaceFluxTally,
    TallyType.CELL_FLUX: CellFluxTally,
    TallyType.DETECTOR: DetectorTally,
    TallyType.ENERGY_DEPOSITION: EnergyDepositionTally,
    TallyType.FISSION_ENERGY_DEPOSITION: FissionEnergyDepositionTally,
    TallyType.ENERGY_DETECTOR_PULSE: EnergyDetectorPulseTally,
}

# ── Convenience aliases ────────────────────────────────────────────────────────

F1Tally = SurfaceCurrentTally
F2Tally = SurfaceFluxTally
F4Tally = CellFluxTally
F5Tally = DetectorTally
F6Tally = EnergyDepositionTally
F7Tally = FissionEnergyDepositionTally
F8Tally = EnergyDetectorPulseTally
