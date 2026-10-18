# Copyright 2024-2026, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
import copy
from typing import Generator

import montepy
from montepy.cells import Cells
from montepy.data_inputs import tally_multiplier
from montepy.data_inputs.data_input import DataInputAbstract
from montepy.data_inputs.tally_group import (
    Filter,
    FlatGroup,
    LatticeIndex,
    ParticleFilter,
    PathGroup,
    SpatialFilter,
    TallyGroup,
    _parse_tally_numbers,
)
from montepy.data_inputs.tally_type import Score, TallyType, _TallyKey
from montepy.exceptions import IllegalState, MalformedInputError, NumberConflictError
from montepy.input_parser import syntax_node
from montepy.input_parser.tally_parser import (
    TallyParser,
    _append_tally_item,
    _is_run,
    _iter_runs,
    _next_key,
)
from montepy.mcnp_object import InitInput
from montepy.numbered_mcnp_object import Numbered_MCNP_Object
from montepy.surface_collection import Surfaces
import montepy.types as ty
from montepy.utilities import *

_TALLY_TYPE_MODULUS = 10
_VALID_MODULI = {t.modulo for t in TallyType if t.modulo is not None}


def _digit_of(num: ty.Integral) -> ty.Integral:
    """The tally type digit (last digit) of a tally number."""
    return num % _TALLY_TYPE_MODULUS


def _link_multiplier_to_tally(self, fm):
    fm._link_to_parent(self)
    if self._problem is not None:
        self._problem.tallies.append(fm)


class Tally(Numbered_MCNP_Object, DataInputAbstract):
    """Base class for MCNP F-card tallies (``F1``, ``F2``, ``F4``, ``F5``,
    ``F6``, ``F7``, ``F8``).

    Use :meth:`from_input` as a factory to create the appropriate subclass
    when reading from a file.

    Examples
    --------

    Checking what a tally scores
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    ``in`` checks whether a cell or surface is scored by a tally:

    .. doctest::

        >>> import montepy
        >>> tally = montepy.Tally.from_input("F4:n 2 (3 4)")
        >>> montepy.Cell(number=3) in tally
        True

    For a repeated-structures path (``<``), only the innermost (leftmost)
    entry is scored. The outer entries only select which instance of it is
    meant, so they are not ``in`` the tally:

    .. doctest::

        >>> tally = montepy.Tally.from_input("F4:n (2 < 5)")
        >>> montepy.Cell(number=2) in tally
        True
        >>> montepy.Cell(number=5) in tally
        False

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
        # The groups currently written in the tree, to tell when the bins
        # need rebuilding.
        self._groups_in_tree = []
        self._include_total = False
        self._parsed_include_total = False
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
        super()._generate_default_tree()
        classifier = self._tree["classifier"]
        # The base's -1 placeholder leaves stray padding once a 3+ digit
        # number is assigned (Material has the same bug, e.g. "M104  1001.80c").
        classifier.number = self._generate_default_node(int, 1)
        tally_type = getattr(type(self), "_TALLY_TYPE", None)
        if tally_type is not None and tally_type.modifier:
            classifier.modifier = syntax_node.ValueNode(
                tally_type.modifier, str, padding=None
            )
        self._tree.nodes["data"] = syntax_node.SyntaxNode(
            "tally list",
            {
                "tally": syntax_node.SyntaxNode("tally bins", {}),
                "end": syntax_node.ValueNode(None, str),
            },
        )

    @args_checked
    def __init__(
        self,
        input: InitInput = None,
        number: ty.PositiveInt = None,
        *,
        jit_parse: bool = True,
    ):
        super().__init__(input, number, jit_parse=jit_parse)

    @staticmethod
    def _class_prefix() -> str:
        return "f"

    @staticmethod
    def _has_number() -> bool:
        return True

    @staticmethod
    def _has_classifier() -> ty.PositiveInt:
        return 1

    @staticmethod
    def _parent_collections():
        return ()

    def _parse_tally_body(self):
        if self._input is None:
            return
        num = self._input_number.value
        # Is this digit valid for *any* tally type -- the concrete subclass
        # is already fixed by dispatch, so this only catches a hand-built
        # Tally() bypassing from_input with a bogus digit.
        digit = _digit_of(num)
        if digit not in _VALID_MODULI:
            raise MalformedInputError(self._input, f"Invalid tally type digit: {digit}")
        tally_list = self._tree["data"]
        end_node = tally_list["end"]
        self._include_total = (
            end_node.value is not None and str(end_node.value).upper() == "T"
        )
        self._parsed_include_total = self._include_total
        self._groups = _parse_tally_numbers(tally_list["tally"])
        self._groups_in_tree = list(self._groups)

    def _number_validator(self, number):
        # Unlike _parse_tally_body's check, this is specific to *this*
        # subclass's own digit, not just any valid one.
        tally_type = getattr(type(self), "_TALLY_TYPE", None)
        if tally_type is not None and _digit_of(number) != tally_type.modulo:
            raise ValueError(
                f"Cannot change tally type via number setter; "
                f"expected last digit {tally_type.modulo}, "
                f"got {_digit_of(number)}."
            )
        super()._number_validator(number)
        if self._multiplier is not None:
            self._multiplier.number = number

    @make_prop_val_node("_old_number")
    def old_number(self):
        """The tally number as read from the input file."""
        pass

    @property
    @needs_full_ast
    def tally_type(self) -> TallyType | None:
        """The MCNP tally type (e.g. ``TallyType.CELL_FLUX`` for ``F4``)."""
        return getattr(type(self), "_TALLY_TYPE", None)

    @property
    @needs_full_ast
    def groups(self) -> list[TallyGroup]:
        """The list of :class:`~montepy.data_inputs.tally.TallyGroup` objects defining what is scored."""
        return list(self._groups)

    @make_prop_pointer("_include_total", bool)
    @needs_full_ast
    def include_total(self) -> bool:
        """``True`` if a total bin (T) is appended."""
        pass

    @make_prop_pointer(
        "_multiplier",
        tally_multiplier.TallyMultiplier,
        validator=_link_multiplier_to_tally,
    )
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
        """The physical quantities this tally scores, e.g. ``[Score.FLUX]`` for ``F4``.

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
            filters.append(ParticleFilter(self._classifier.particles))
        if self._groups:
            filters.append(SpatialFilter(self._groups))
        return filters

    @needs_full_ast
    def __contains__(self, item) -> bool:
        for group in self._groups:
            if item in group:
                return True
        return False

    def _referenced_objects_and_numbers(self) -> tuple[set, set]:
        """The objects (by identity)/numbers still referenced by
        ``self._groups``, matching ``__contains__``'s per-group semantics
        (only a ``PathGroup``'s innermost level counts). Computed once in
        O(groups), for pruning a bookkeeping collection without re-scanning
        every group once per candidate item. Objects are tracked by
        ``id()`` since ``Surface`` overrides ``__eq__`` without
        ``__hash__``, making it unhashable.
        """
        object_ids = set()
        numbers = set()
        for group in self._groups:
            objs = group.cells_or_surfaces
            if objs:
                object_ids.update(id(obj) for obj in objs)
            else:
                numbers.update(group.old_numbers)
        return object_ids, numbers

    @staticmethod
    def _dispatch_class(
        input, num: ty.Integral, modifier: str | None = None, mnemonic: str = "F"
    ) -> type[Tally]:
        """The :class:`Tally` subclass for a tally mnemonic/number/modifier."""
        try:
            tally_type = TallyType(
                _TallyKey(mnemonic, num % _TALLY_TYPE_MODULUS, modifier)
            )
        except ValueError as e:
            raise MalformedInputError(
                input,
                f"Tally mnemonic {mnemonic!r} with type digit "
                f"{num % _TALLY_TYPE_MODULUS} and modifier {modifier!r} is not valid.",
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
            classifier = Tally._peek_light_parse(input).nodes["classifier"]
            if classifier.number is None:
                raise ValueError("Tally classifier has no number.")
        except (AttributeError, KeyError, ValueError, AssertionError) as e:
            # The light parser reports a malformed classifier with a bare
            # exception and no context. Fully parse only to raise a
            # ParsingError pointing at the offending token.
            Tally(input, jit_parse=False)
            # The full parser is more lenient (e.g. it accepts "f4:n:p" by
            # dropping the "n"), so don't trust a classifier it recovers.
            raise MalformedInputError(
                input, f"Could not read the tally classifier of: {input}"
            ) from e
        modifier_node = classifier.modifier
        modifier = modifier_node.value if modifier_node is not None else None
        subclass = Tally._dispatch_class(
            input, classifier.number.value, modifier, classifier.prefix.value.upper()
        )

        return subclass(input, jit_parse=jit_parse)

    def _update_values(self):
        if self._classifier.modifier is None:
            self._classifier.modifier = self._generate_default_node(
                str, "", padding=None
            )
        tally_type = getattr(type(self), "_TALLY_TYPE", None)
        self._classifier.modifier.value = (
            tally_type.modifier
            if tally_type is not None and tally_type.modifier
            else ""
        )
        bins = self._tree["data"]["tally"]
        # Patches each group's value nodes, including a shortcut's values.
        group_nodes = [group.node for group in self._groups]
        if len(self._groups) != len(self._groups_in_tree) or any(
            a is not b for a, b in zip(self._groups, self._groups_in_tree)
        ):
            self._rebuild_bins(bins, group_nodes)
        # Re-zip a run's shortcuts around its patched values. An unchanged run
        # is left alone, since re-zipping can also absorb neighboring values
        # (e.g. "1 3i 5 6" -> "1 4i 6"), changing the user's text.
        for run in _iter_runs(bins):
            if run._has_changed_values():
                run.update_with_new_values(list(run))
        end_node = self._tree["data"]["end"]
        if self._include_total != self._parsed_include_total:
            # Only rewrite when this actually changed -- preserves the
            # original node (and its casing, e.g. a parsed lowercase "t")
            # untouched for a tally whose include_total was never set.
            end_node.value = "T" if self._include_total else None
            self._parsed_include_total = self._include_total

    def _rebuild_bins(self, bins, group_nodes):
        """Rewrite ``bins`` after groups were added or removed.

        A top-level bin's value goes back into the run it was parsed in, so
        that run keeps its shortcuts and re-zips around the remaining values.
        """
        old_run_of = {
            id(v): run for run in bins.nodes.values() if _is_run(run) for v in run
        }
        entries = []  # [run, values] for a run of numbers, else a node
        used_runs = set()
        for node in group_nodes:
            if isinstance(node, syntax_node.SyntaxNode):
                entries.append(node)
                continue
            for value in node.nodes:
                if not (isinstance(value, syntax_node.ValueNode) and value.type is int):
                    entries.append(value)
                    continue
                run = old_run_of.get(id(value))
                last = entries[-1] if entries else None
                if isinstance(last, list) and (run is None or last[0] is run):
                    last[1].append(value)
                    continue
                if run is None or id(run) in used_runs:
                    run = syntax_node.ListNode("tally number run")
                used_runs.add(id(run))
                entries.append([run, [value]])
        bins.nodes.clear()
        for entry in entries:
            if isinstance(entry, list):
                run, values = entry
                current = list(run)
                if len(values) != len(current) or any(
                    a is not b for a, b in zip(values, current)
                ):
                    run.update_with_new_values(values)
                bins.nodes[_next_key(bins, "run")] = run
            else:
                _append_tally_item(bins, entry)
        self._groups_in_tree = list(self._groups)

    @staticmethod
    def _align_to_type(tally_type: TallyType, start: ty.Integral) -> ty.Integral:
        """The smallest number ``>= start`` whose last digit matches ``tally_type``."""
        aligned = start - (start % 10) + tally_type.modulo
        if aligned < start:
            aligned += 10
        return aligned

    def _next_number_for_type(
        self, tally_type: TallyType, starting_number, step
    ) -> ty.Integral:
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

        Successive candidates are exactly ``step`` apart -- ``step`` must
        therefore be a multiple of 10 to keep the trailing type digit fixed
        (:attr:`~montepy.tallies.Tallies.step` enforces this and defaults
        to 10).
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
            step = step if step is not None else 10
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
            candidate += step

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

        If this tally has a linked ``FM`` multiplier (see :attr:`multiplier`),
        it's cloned too and linked to the new tally's number -- unlike
        :meth:`clone_as`, ``clone`` is like-for-like (same tally type), so
        the multiplier's scoring relationship still applies.

        See :meth:`~montepy.numbered_mcnp_object.Numbered_MCNP_Object.clone`.
        """
        multiplier = self.multiplier
        ret = copy.deepcopy(self)
        ret._multiplier = None
        new_number = self._next_number_for_type(self.tally_type, starting_number, step)
        if self._problem:
            ret.link_to_problem(self._problem)
            ret.number = new_number
            self._problem.tallies.append(ret)
        else:
            ret.number = new_number
        if multiplier is not None:
            multiplier.clone(ret)
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

        For example, this can turn an ``F4`` cell-flux tally into an ``F6``
        energy-deposition tally scoring the same cells:

        .. code-block:: python

            heating = flux_tally.clone_as(montepy.EnergyDepositionTally)
            # or, equivalently:
            heating = flux_tally.clone_as(montepy.TallyType.ENERGY_DEPOSITION)

        Only conversions within the same tally category are allowed:
        ``F1``/``F2`` (surface-based) convert freely among each other, as do
        ``F4``/``F6``/``F7``/``F8`` (cell-based); ``F5`` (point/ring detector) has no
        cell/surface geometry to carry over and can't be converted to or
        from.

        Note
        ----
        The clone does **not** carry over a linked ``FM`` multiplier (see
        :attr:`multiplier`) -- a multiplier is a companion card tied to this
        exact tally number, not something that meaningfully transfers to a
        retyped/renumbered copy.

        Parameters
        ----------
        new_type : TallyType | type[Tally]
            The target tally type, either as a :class:`TallyType` member or
            as a :class:`Tally` subclass (e.g. ``montepy.EnergyDepositionTally``).
        starting_number : Integral, optional
            The starting number to request for the new object's number.
        step : Integral, optional
            The step size to use to find a new valid number.

        Returns
        -------
        Tally
            A new tally of the requested type, with the same scoring groups.
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
            return f"{type(self).__name__}: {self.number}"
        except Exception:
            return f"{type(self).__name__}: (unparsed)"

    def __repr__(self):
        try:
            ttype = getattr(type(self), "_TALLY_TYPE", None)
            ngroups = len(getattr(self, "_groups", []))
            return f"TALLY: {self.number}, type: {ttype}, groups: {ngroups}"
        except Exception:
            return "TALLY: (unparsed)"


class SurfaceTally(Tally):
    """Intermediate class for tallies that score on surfaces (``F1``, ``F2``).

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
        group = FlatGroup([surface], is_grouped=False)
        self._groups.append(group)
        if surface not in self._surfaces:
            self._surfaces.append(surface)

    @args_checked
    @needs_full_cst
    def add_group(
        self, surfaces: list[montepy.Surface] | tuple[montepy.Surface, ...]
    ) -> None:
        """Add surfaces as a single union (averaged) bin.

        Parameters
        ----------
        surfaces : list[Surface] | tuple[Surface, ...]
            The surfaces to group, in order.
        """
        surfaces = list(surfaces)
        group = FlatGroup(surfaces, is_grouped=True)
        self._groups.append(group)
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
        is_grouped = len(surfaces) > 1
        first_level = FlatGroup(list(surfaces), is_grouped=is_grouped)
        pg = PathGroup([first_level])
        self._groups.append(pg)
        return pg

    @args_checked
    @needs_full_cst
    def remove_surface(self, surface: montepy.Surface) -> None:
        """Remove the single-surface scoring bin added via :meth:`add_surface`.

        Parameters
        ----------
        surface : Surface
            The surface to remove.
        """
        for group in self._groups:
            if (
                isinstance(group, FlatGroup)
                and not group.is_grouped
                and group.cells_or_surfaces == [surface]
            ):
                self.remove_group(group)
                return
        raise ValueError(
            f"No single-surface scoring group found for surface {surface.number}."
        )

    @args_checked
    @needs_full_cst
    def remove_group(self, group: TallyGroup) -> None:
        """Remove a scoring group previously added via ``add_surface``/``add_group``/``add_path_group``.

        A surface is only dropped from :attr:`surfaces` if no other
        remaining group still references it.

        Parameters
        ----------
        group : TallyGroup
            The group to remove.
        """
        self._groups.remove(group)
        referenced_objects, referenced_numbers = self._referenced_objects_and_numbers()
        for surface in list(self._surfaces):
            if (
                id(surface) not in referenced_objects
                and surface.old_number not in referenced_numbers
                and surface.number not in referenced_numbers
            ):
                self._surfaces.remove(surface)

    def link_to_problem(self, problem, *, deepcopy=False):
        super().link_to_problem(problem, deepcopy=deepcopy)
        if problem is not None and not hasattr(self, "_not_parsed"):
            # Rebuild from scratch: a deepcopy (e.g. from clone()) carries
            # stale copied Surface objects that must be discarded, not
            # merged with the live ones from `problem`.
            self._surfaces = Surfaces()
            for group in self._groups:
                # Use _surfaces directly to avoid triggering __relink_objs
                # via the property.
                group.update_pointers(problem._surfaces, is_cell=False, tally=self)
                for surface in group.cells_or_surfaces:
                    try:
                        self._surfaces[surface.number]
                    except KeyError:
                        self._surfaces.append(surface)


class CellTally(Tally):
    """Intermediate class for tallies that score in cells (``F4``, ``F6``, ``F7``, ``F8``).

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
        group = FlatGroup([cell], is_grouped=False)
        self._groups.append(group)
        if cell not in self._cells:
            self._cells.append(cell)

    @args_checked
    @needs_full_cst
    def add_group(self, cells: list[montepy.Cell] | tuple[montepy.Cell, ...]) -> None:
        """Add cells as a single union (averaged) bin.

        Parameters
        ----------
        cells : list[Cell] | tuple[Cell, ...]
            The cells to group, in order.
        """
        cells = list(cells)
        group = FlatGroup(cells, is_grouped=True)
        self._groups.append(group)
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
        is_grouped = len(cells) > 1
        first_level = FlatGroup(list(cells), is_grouped=is_grouped)
        pg = PathGroup([first_level])
        self._groups.append(pg)
        return pg

    @args_checked
    @needs_full_cst
    def remove_cell(self, cell: montepy.Cell) -> None:
        """Remove the single-cell scoring bin added via :meth:`add_cell`.

        Parameters
        ----------
        cell : Cell
            The cell to remove.
        """
        for group in self._groups:
            if (
                isinstance(group, FlatGroup)
                and not group.is_grouped
                and group.cells_or_surfaces == [cell]
            ):
                self.remove_group(group)
                return
        raise ValueError(f"No single-cell scoring group found for cell {cell.number}.")

    @args_checked
    @needs_full_cst
    def remove_group(self, group: TallyGroup) -> None:
        """Remove a scoring group previously added via ``add_cell``/``add_group``/``add_path_group``.

        A cell is only dropped from :attr:`cells` if no other remaining
        group still references it.

        Parameters
        ----------
        group : TallyGroup
            The group to remove.
        """
        self._groups.remove(group)
        referenced_objects, referenced_numbers = self._referenced_objects_and_numbers()
        for cell in list(self._cells):
            if (
                id(cell) not in referenced_objects
                and cell.old_number not in referenced_numbers
                and cell.number not in referenced_numbers
            ):
                self._cells.remove(cell)

    def link_to_problem(self, problem, *, deepcopy=False):
        super().link_to_problem(problem, deepcopy=deepcopy)
        if problem is not None and not hasattr(self, "_not_parsed"):
            # Rebuild from scratch: a deepcopy (e.g. from clone()) carries
            # stale copied Cell objects that must be discarded, not merged
            # with the live ones from `problem`.
            self._cells = Cells()
            for group in self._groups:
                # Use _cells directly to avoid triggering __relink_objs via
                # the property.
                group.update_pointers(problem._cells, is_cell=True, tally=self)
                for cell in group.cells_or_surfaces:
                    try:
                        self._cells[cell.number]
                    except KeyError:
                        self._cells.append(cell)


class DetectorTally(Tally):
    """``F5``: point/ring detector tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.DETECTOR
    _DEFAULT_SCORES = (Score.FLUX,)


# ── Concrete subclasses ────────────────────────────────────────────────────────


class SurfaceCurrentTally(SurfaceTally):
    """``F1``: surface current tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.CURRENT
    _DEFAULT_SCORES = (Score.CURRENT,)


class SurfaceFluxTally(SurfaceTally):
    """``F2``: average surface flux tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.SURFACE_FLUX
    _DEFAULT_SCORES = (Score.FLUX,)


class CellFluxTally(CellTally):
    """``F4``: cell flux tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.CELL_FLUX
    _DEFAULT_SCORES = (Score.FLUX,)


class EnergyDepositionTally(CellTally):
    """``F6``: energy deposition tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.ENERGY_DEPOSITION
    _DEFAULT_SCORES = (Score.ENERGY_DEPOSITION,)


class FissionEnergyDepositionTally(CellTally):
    """``F7``: fission energy deposition tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.FISSION_ENERGY_DEPOSITION
    _DEFAULT_SCORES = (Score.FISSION_ENERGY_DEPOSITION,)


class EnergyDetectorPulseTally(CellTally):
    """``F8``: energy-detector pulse height tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.ENERGY_DETECTOR_PULSE
    _DEFAULT_SCORES = (Score.PULSE_HEIGHT,)


class CollisionHeatingTally(CellTally):
    """``+F6``: collision heating tally, distinct from the plain F6 energy
    deposition tally.

    .. versionadded:: 1.6.0b3
    """

    _TALLY_TYPE = TallyType.COLLISION_HEATING
    _DEFAULT_SCORES = (Score.COLLISION_HEATING,)


class ChargeDepositionTally(CellTally):
    """``+F8``: charge deposition tally, distinct from the plain F8 pulse
    height tally.

    .. versionadded:: 1.6.0b3
    """

    _TALLY_TYPE = TallyType.CHARGE_DEPOSITION
    _DEFAULT_SCORES = (Score.CHARGE_DEPOSITION,)


_TALLY_TYPE_MAP: dict[TallyType, type[Tally]] = {
    TallyType.CURRENT: SurfaceCurrentTally,
    TallyType.SURFACE_FLUX: SurfaceFluxTally,
    TallyType.CELL_FLUX: CellFluxTally,
    TallyType.DETECTOR: DetectorTally,
    TallyType.ENERGY_DEPOSITION: EnergyDepositionTally,
    TallyType.COLLISION_HEATING: CollisionHeatingTally,
    TallyType.FISSION_ENERGY_DEPOSITION: FissionEnergyDepositionTally,
    TallyType.ENERGY_DETECTOR_PULSE: EnergyDetectorPulseTally,
    TallyType.CHARGE_DEPOSITION: ChargeDepositionTally,
}

# ── Convenience aliases ────────────────────────────────────────────────────────

F1Tally = SurfaceCurrentTally
F2Tally = SurfaceFluxTally
F4Tally = CellFluxTally
F5Tally = DetectorTally
F6Tally = EnergyDepositionTally
F7Tally = FissionEnergyDepositionTally
F8Tally = EnergyDetectorPulseTally
PlusF6Tally = CollisionHeatingTally
PlusF8Tally = ChargeDepositionTally
