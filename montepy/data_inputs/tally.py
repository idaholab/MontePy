# Copyright 2024-2026, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
import copy
from typing import Generator
import warnings

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
    _entry_is,
    _parse_tally_numbers,
)
from montepy.data_inputs.tally_type import Score, TallyType, TallyUnits, _TallyKey
from montepy.exceptions import (
    IllegalState,
    MalformedInputError,
    NumberConflictError,
    OnlyInPathError,
    PathContainmentWarning,
    UnsupportedFeature,
)
from montepy.input_parser import syntax_node, tally_parser
from montepy.numbered_mcnp_object import Numbered_MCNP_Object
from montepy.surface_collection import Surfaces
import montepy.types as ty
from montepy.utilities import *

_TALLY_TYPE_MODULUS = 10
# Detector tallies (F5) have their own syntax and aren't supported yet; see
# https://github.com/idaholab/MontePy/issues/1024.
_DETECTOR_MODULO = 5
_VALID_MODULI = {t.modulo for t in TallyType if t.modulo is not None}


def _get_type_digit(num: ty.Integral) -> ty.Integral:
    """Get the tally type digit (last digit) of a tally number."""
    return num % _TALLY_TYPE_MODULUS


def _is_detector_input(classifier: syntax_node.ClassifierNode | None) -> bool:
    """Whether a classifier is of a detector (``F5``) tally, or an ``FM`` card for one.

    Neither is supported yet.

    Parameters
    ----------
    classifier : ClassifierNode | None
        The light-parsed classifier of the input, or ``None`` if it couldn't
        be read.

    Returns
    -------
    bool
        Whether it is a detector input. ``False`` if the classifier couldn't
        be read, so the tally or multiplier class reports the error.
    """
    if classifier is None or classifier.number is None:
        return False
    return (
        classifier.prefix.value.upper() in {"F", "FM"}
        and classifier.number.value % _TALLY_TYPE_MODULUS == _DETECTOR_MODULO
    )


def _link_multiplier_to_tally(self, fm):
    fm._link_to_parent(self)
    if self._problem is not None:
        self._problem.tallies.append(fm)


class Tally(Numbered_MCNP_Object, DataInputAbstract):
    """Base class for all MCNP tallies.

    Each :class:`~montepy.TallyType` is a subclass of this; see
    :class:`CellTally` and :class:`SurfaceTally`. The tallies currently
    supported are the cell and surface ``F`` tallies: ``F1``, ``F2``, ``F4``,
    ``F6``, ``F7``, and ``F8``, with their ``*`` and ``+`` variants. Other
    tallies, such as detector (``F5``) tallies, are read as plain data inputs.

    Use :meth:`from_input` as a factory to create the appropriate subclass
    when reading from a file.

    Examples
    --------

    Building a tally
    ^^^^^^^^^^^^^^^^

    Make a tally of the class for its type, set its particles, and add the
    cells it scores. :meth:`~montepy.CellTally.add_cell` gives each cell its
    own bin, and :meth:`~montepy.CellTally.add_group` averages cells in one
    bin, with a list as a nested union:

    .. doctest::

        >>> import montepy
        >>> problem = montepy.read_input("tests/inputs/test_tally.imcnp")
        >>> cells = problem.cells
        >>> flux = montepy.CellFluxTally(number=304)
        >>> flux.particles = {montepy.Particle.NEUTRON}
        >>> flux.add_cell(cells[1], cells[2])
        >>> flux.add_group(cells[3], [cells[4], cells[7]])
        >>> problem.tallies.append(flux)
        >>> print(flux.mcnp_str())  # doctest: +NORMALIZE_WHITESPACE
        F304:n 1 2 (3 (4 7))

    For repeated structures, :meth:`~montepy.CellTally.add_path_group` scores
    cells only where they are inside other cells, which
    :meth:`~montepy.data_inputs.tally.PathGroup.inside` adds from the inside
    out:

    .. doctest::

        >>> path = flux.add_path_group(cells[1])
        >>> path.inside(cells[2], lattice=[0, 0, 0]).inside(cells[5])
        PathGroup(levels=3)
        >>> print(flux.mcnp_str())  # doctest: +NORMALIZE_WHITESPACE
        F304:n 1 2 (3 (4 7)) (1 < 2[0 0 0] < 5)

    Changing the tally type
    ^^^^^^^^^^^^^^^^^^^^^^^

    :meth:`clone_as` makes a tally of another type that scores the same cells,
    with the next free number of that type:

    .. doctest::

        >>> heating = flux.clone_as(montepy.TallyType.ENERGY_DEPOSITION)
        >>> print(heating.mcnp_str())  # doctest: +NORMALIZE_WHITESPACE
        F26:n 1 2 (3 (4 7)) (1 < 2[0 0 0] < 5)

    Checking what a tally scores
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    ``in`` checks whether a cell or surface is scored by a tally:

    .. doctest::

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
    _DEFAULT_SCORES: tuple[Score, ...] = ()
    """What :attr:`scores` reports when no multiplier is linked."""
    _TALLY_TYPE: TallyType | None = None
    """The tally type of this class, which a new tally of this class gets.

    ``None`` for an abstract class.
    """
    _OTHER_TALLY_TYPES: tuple[TallyType, ...] = ()
    """Every other tally type that is this class, which :attr:`tally_units` can switch to.

    E.g. ``F6`` and ``*F6`` only differ in units, so both are an
    :class:`EnergyDepositionTally`.
    """
    _KEYS_TO_PRESERVE = {"_multiplier"}
    _HAS_PARTICLES: bool = True
    """Whether this tally has a particle designator, e.g. the ``:n`` in ``F4:n``.

    ``+F6`` applies to all particles, so it has none.
    """
    _SCORED_COLLECTION_ATTR: str | None = None
    """The attribute holding the collection of scored objects, e.g. ``"_cells"``.

    ``None`` for an abstract class.
    """

    @staticmethod
    def _parser():
        return tally_parser.TallyParser()

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
        self._tally_type = type(self)._TALLY_TYPE

    def _jit_light_init(self, input):
        super()._jit_light_init(input)
        self._old_number = self._input_number
        self._parse_tally_type()

    def _parse_tree(self):
        super()._parse_tree()
        num = self._input_number
        self._old_number = copy.deepcopy(num)
        self._number = num
        self._parse_tally_body()

    def _generate_default_tree(self, **kwargs):
        super()._generate_default_tree()
        classifier = self._tree["classifier"]
        tally_type = getattr(type(self), "_TALLY_TYPE", None)
        if tally_type is not None:
            # Until a number is set, use the smallest one of this type, so the
            # tally is still written as its own type.
            classifier.number.value = tally_type.modulo
            if tally_type.modifier:
                classifier.modifier.value = tally_type.modifier
        self._tree.nodes["data"] = syntax_node.SyntaxNode(
            "tally list",
            {
                "tally": syntax_node.SyntaxNode("tally bins", {}),
                "end": syntax_node.ValueNode(None, str),
            },
        )

    @staticmethod
    def _class_prefix() -> str:
        return "f"

    @staticmethod
    def _has_number() -> bool:
        return True

    @staticmethod
    def _has_classifier() -> ty.PositiveInt:
        return 1

    def _parse_tally_body(self):
        if self._input is None:
            return
        num = self._input_number.value
        # Is this digit valid for *any* tally type -- the concrete subclass
        # is already fixed by dispatch, so this only catches a hand-built
        # Tally() bypassing from_input with a bogus digit.
        digit = _get_type_digit(num)
        if digit not in _VALID_MODULI:
            raise MalformedInputError(self._input, f"Invalid tally type digit: {digit}")
        self._parse_tally_type()
        tally_list = self._tree["data"]
        end_node = tally_list["end"]
        self._include_total = (
            end_node.value is not None and str(end_node.value).upper() == "T"
        )
        self._parsed_include_total = self._include_total
        self._groups = _parse_tally_numbers(tally_list["tally"])
        self._groups_in_tree = list(self._groups)

    def _parse_tally_type(self):
        """Pick which of this class's tally types the classifier's modifier is."""
        if self._TALLY_TYPE is None:
            return
        modifier = self._classifier.modifier.value
        for tally_type in (self._TALLY_TYPE, *self._OTHER_TALLY_TYPES):
            if (tally_type.modifier or "") == modifier:
                self._tally_type = tally_type
                return
        raise MalformedInputError(
            self._input,
            f"Modifier {modifier!r} is not valid for a {type(self).__name__}.",
        )

    def _number_validator(self, number):
        # Unlike _parse_tally_body's check, this is specific to *this*
        # subclass's own digit, not just any valid one.
        tally_type = getattr(type(self), "_TALLY_TYPE", None)
        if tally_type is not None and _get_type_digit(number) != tally_type.modulo:
            raise ValueError(
                f"Cannot change tally type via number setter; "
                f"expected last digit {tally_type.modulo}, "
                f"got {_get_type_digit(number)}."
            )
        super()._number_validator(number)
        if self._multiplier is not None:
            self._multiplier.number = number

    @make_prop_val_node("_old_number")
    def old_number(self):
        """The tally number as read from the input file."""
        pass

    @property
    def tally_type(self) -> TallyType | None:
        """The MCNP tally type (e.g. ``TallyType.CELL_FLUX`` for ``F4``)."""
        return self._tally_type

    @property
    def tally_units(self) -> TallyUnits | None:
        """The units of this tally's result, e.g. ``TallyUnits.MEV_PER_G`` for ``F6``.

        Only settable for a tally type that MCNP allows in more than one
        unit: ``F6`` and ``F7`` can be in MeV/g or, as ``*F6``/``*F7``, in
        jerks/g. A different quantity, such as the energy flux of ``*F4``,
        is a different class instead (:class:`~montepy.CellEnergyFluxTally`).

        .. versionadded:: 1.6.0b2

        Raises
        ------
        ValueError
            If this tally type can't be in the given units.
        """
        if self._tally_type is None:
            return None
        return self._tally_type.units

    @tally_units.setter
    @args_checked
    @needs_full_cst
    def tally_units(self, units: TallyUnits):
        for tally_type in (self._TALLY_TYPE, *self._OTHER_TALLY_TYPES):
            if tally_type is not None and tally_type.units is units:
                self._tally_type = tally_type
                return
        raise ValueError(f"A {type(self).__name__} can't be in {units.value}.")

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

        This is just the quantity implied by the tally type, unless an
        ``FM`` tally-multiplier card is linked (see :attr:`multiplier`), in
        which case this returns one :class:`~montepy.data_inputs.tally_multiplier.MultiplierScore`
        per output bin the multiplier defines instead.
        """
        if self.multiplier is not None:
            return [score for bin_ in self.multiplier.bins for score in bin_.scores]
        return list(self._DEFAULT_SCORES)

    @property
    @needs_full_ast
    def particles(self) -> set[montepy.Particle]:
        """The particles this tally is for, e.g. ``{Particle.NEUTRON}`` for ``F4:n``.

        This is a copy, so to add a particle, set a new set, e.g.
        ``tally.particles = tally.particles | {montepy.Particle.PHOTON}``.

        .. versionadded:: 1.6.0b2

        Returns
        -------
        set[Particle]
            The particles, or an empty set if there is no particle
            designator, as for ``+F6``.

        Raises
        ------
        ValueError
            If set to no particles, or set for a tally without a particle
            designator, such as ``+F6``, which applies to all particles.
        """
        node = self._classifier.particles
        return set(node.particles) if node is not None else set()

    @particles.setter
    @args_checked
    @needs_full_cst
    def particles(self, particles: set[montepy.Particle] | list[montepy.Particle]):
        if not self._HAS_PARTICLES:
            raise ValueError(
                f"A {type(self).__name__} applies to all particles, so it can't "
                "have a particle designator."
            )
        if not particles:
            raise ValueError("A tally needs at least one particle.")
        node = self._classifier.particles
        if node is None:
            token = ":" + ",".join(p.value.lower() for p in particles)
            node = syntax_node.ParticleNode("data particles", token)
            self._classifier.particles = node
        else:
            node.particles = particles
        self._particles = node.particles

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

    def _referenced_objects_and_numbers(self) -> tuple[set[int], set[int]]:
        """Get the objects and numbers that the groups of this tally score.

        As with ``in``, only the innermost level of a :class:`PathGroup` counts.
        These are found in one pass over the groups, so that pruning
        :attr:`cells`/:attr:`surfaces` doesn't scan every group once per item.

        Returns
        -------
        tuple[set[int], set[int]]
            The ``id()`` of each scored object, and each scored number that isn't linked
            to an object yet.
            Objects are tracked by ``id()`` since :class:`~montepy.Surface` is unhashable:
            it overrides ``__eq__`` without ``__hash__``.
        """
        object_ids = set()
        numbers = set()
        for group in self._groups:
            scored = group.levels[0] if isinstance(group, PathGroup) else group
            for entry, number, _ in scored._leaves():
                # An unresolved entry is its own number (see
                # FlatGroup._number_of), so this avoids a slow isinstance
                # check against the Integral ABC.
                if entry is number:
                    numbers.add(number)
                else:
                    object_ids.add(id(entry))
        return object_ids, numbers

    def _remove_scored(
        self,
        item: montepy.Cell | montepy.Surface,
        kind: type[montepy.Cell] | type[montepy.Surface],
    ) -> None:
        """Remove every scored occurrence of ``item``, for ``remove_cell``/``remove_surface``.

        ``item`` is removed from each bin, union, and innermost path level it
        is in, so it is no longer ``in`` this tally. A bin, union, or path
        left with nothing to score is removed.

        Parameters
        ----------
        item : Cell | Surface
            The cell or surface to remove.
        kind : type[Cell] | type[Surface]
            The class of objects this tally scores, for the error messages.

        Raises
        ------
        OnlyInPathError
            If ``item`` is only an outer level of a path, so it isn't scored.
        ValueError
            If ``item`` isn't in this tally.

        Warns
        -----
        PathContainmentWarning
            If ``item`` is still an outer level of a path after it's removed.
        """
        name = kind.__name__
        found = False
        for group in list(self._groups):
            scored = group.levels[0] if isinstance(group, PathGroup) else group
            if not scored._remove_matching(lambda entry: _entry_is(entry, item)):
                continue
            found = True
            if not scored._items:
                self._groups.remove(group)
        in_path = any(
            _entry_is(entry, item)
            for group in self._groups
            if isinstance(group, PathGroup)
            for level in group.levels[1:]
            for entry, _, _ in level._leaves()
        )
        if not found:
            if in_path:
                raise OnlyInPathError(
                    f"{name} {item.number} is only a containment level "
                    f"of a path in {self}, not a scored {name.lower()}, so it can't be "
                    "removed."
                )
            raise ValueError(f"{name} {item.number} is not in {self}.")
        if in_path:
            warnings.warn(
                f"{name} {item.number} was removed from {self}, but is "
                "still a containment level of one of its paths.",
                PathContainmentWarning,
            )
        self._prune_unreferenced([item])

    def _prune_unreferenced(self, entries) -> None:
        """Drop the objects for ``entries`` from :attr:`cells`/:attr:`surfaces`
        if no remaining group still scores them.

        ``entries`` are the items (objects or numbers) of what was just
        removed, so only those are checked, not the whole collection.
        """
        collection = self._scored_collection
        referenced_objects, referenced_numbers = self._referenced_objects_and_numbers()
        for entry in entries:
            if isinstance(entry, ty.Integral):
                obj = collection.get(entry)
                if obj is None:
                    continue
            else:
                obj = entry
            if (
                obj in collection
                and id(obj) not in referenced_objects
                and obj.old_number not in referenced_numbers
                and obj.number not in referenced_numbers
            ):
                collection.remove(obj)

    def _add_union(
        self,
        members: list | tuple,
        kind: type[montepy.Cell] | type[montepy.Surface],
    ) -> None:
        """Add ``members`` as one union bin, for ``add_group``.

        A nested list or tuple is a nested union, so ``[c1, [c2, c3]]`` is
        ``(1 (2 3))``. Each object is also added to :attr:`cells`/:attr:`surfaces`
        if it isn't there yet.

        Parameters
        ----------
        members : list | tuple
            The objects to group, in order, or nested lists or tuples of them.
        kind : type[Cell] | type[Surface]
            The class of objects this tally scores. Every object must be one.

        Raises
        ------
        TypeError
            If a member isn't a ``kind`` object, list, or tuple.
        ValueError
            If the union, or a nested union, is empty.
        """

        def build(members):
            items = []
            for member in members:
                if isinstance(member, (list, tuple)):
                    items.append(build(member))
                elif isinstance(member, kind):
                    items.append(member)
                else:
                    raise TypeError(
                        f"A union can only hold {kind.__name__} objects or nested "
                        f"lists of them, not {member!r}."
                    )
            if not items:
                raise ValueError("A union can't be empty.")
            return FlatGroup(items, is_grouped=True)

        group = build(members)
        self._groups.append(group)
        collection = self._scored_collection
        for entry, _, _ in group._leaves():
            if entry not in collection:
                collection.append(entry)

    @staticmethod
    def _scored_entries(group: TallyGroup) -> list:
        """The items (objects or numbers) ``group`` scores: a path's innermost level."""
        scored = group.levels[0] if isinstance(group, PathGroup) else group
        return [entry for entry, _, _ in scored._leaves()]

    def link_to_problem(self, problem, *, deepcopy=False):
        """Links the tally to the parent problem, and its groups to the problem's objects.

        Every number in the groups, including in a path's outer levels and a
        ``U=N`` universe, is resolved to the live object, so it follows
        renumbering.

        Parameters
        ----------
        problem : MCNP_Problem
            The problem to link this tally to.
        deepcopy : bool
            If this is occurring during a problem level deepcopy.
        """
        super().link_to_problem(problem, deepcopy=deepcopy)
        attr = self._SCORED_COLLECTION_ATTR
        if problem is None or attr is None or hasattr(self, "_not_parsed"):
            return
        # Rebuild from scratch: a deepcopy (e.g. from clone()) carries stale
        # copied objects that must be discarded, not merged with the live
        # ones from `problem`.
        collection = type(getattr(self, attr))()
        setattr(self, attr, collection)
        is_cell = isinstance(collection, Cells)
        for group in self._groups:
            group.update_pointers(problem, is_cell=is_cell, tally=self)
            for obj in self._scored_entries(group):
                if obj not in collection:
                    collection.append(obj)

    @staticmethod
    def _dispatch_class(
        input, num: ty.Integral, modifier: str | None = None, mnemonic: str = "F"
    ) -> type[Tally]:
        """The :class:`Tally` subclass for a tally mnemonic/number/modifier."""
        if mnemonic == "F" and num % _TALLY_TYPE_MODULUS == _DETECTOR_MODULO:
            raise UnsupportedFeature("Detector (F5) tallies are not supported.", input)
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
            An instance of the correct subclass for the tally type.
        """
        try:
            classifier = Tally._peek_light_parse(input).nodes["classifier"]
        except (AttributeError, KeyError, ValueError, AssertionError):
            classifier = None
        return Tally._from_classifier(input, classifier, jit_parse=jit_parse)

    @staticmethod
    def _from_classifier(
        input, classifier: syntax_node.ClassifierNode | None, *, jit_parse: bool = True
    ) -> Tally:
        """Create the :class:`Tally` subclass for an input from its classifier.

        This lets :func:`~montepy.data_inputs.data_parser.parse_data` reuse the
        classifier it already light-parsed, rather than light-parsing again.

        Parameters
        ----------
        input : Input | str
            The raw MCNP input object.
        classifier : ClassifierNode | None
            The light-parsed classifier of ``input``, or ``None`` if the
            light parser couldn't read it.
        jit_parse : bool
            Whether to defer full parsing.

        Returns
        -------
        Tally
            An instance of the correct subclass for the tally type.

        Raises
        ------
        ParsingError
            If the classifier is invalid.
        MalformedInputError
            If the classifier has no number, or isn't a valid tally type.
        """
        if classifier is None or classifier.number is None:
            # The light parser reports a malformed classifier with a bare
            # exception and no context, or reads no number. The full parser
            # raises a ParsingError pointing at the offending token instead,
            # or reads a classifier the light parser couldn't.
            classifier = Tally(input, jit_parse=False)._classifier
        if classifier.number is None:
            raise MalformedInputError(input, f"The tally has no number: {input}")
        # An empty modifier node means there is no modifier.
        modifier = classifier.modifier.value or None
        subclass = Tally._dispatch_class(
            input, classifier.number.value, modifier, classifier.prefix.value.upper()
        )

        return subclass(input, jit_parse=jit_parse)

    def _update_values(self):
        tally_type = self._tally_type
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
        for run in tally_parser._iter_runs(bins):
            if run._has_changed_values():
                run.update_with_new_values(list(run))
        if self._include_total != self._parsed_include_total:
            # Only rewrite when this actually changed -- preserves the
            # original node (and its casing, e.g. a parsed lowercase "t")
            # untouched for a tally whose include_total was never set.
            tally_parser._set_end_flag(
                self._tree["data"], "T" if self._include_total else None
            )
            self._parsed_include_total = self._include_total

    def _rebuild_bins(self, bins, group_nodes):
        """Rewrite ``bins`` after groups were added or removed.

        A top-level bin's value goes back into the run it was parsed in, so
        that run keeps its shortcuts and re-zips around the remaining values.
        """
        old_run_of = {
            id(v): run
            for run in bins.nodes.values()
            if tally_parser._is_run(run)
            for v in run
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
                bins.nodes[tally_parser._next_key(bins, "run")] = run
            else:
                tally_parser._append_tally_item(bins, entry)
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
        """Which of {SurfaceTally, CellTally} ``cls`` belongs to."""
        for category in (SurfaceTally, CellTally):
            if issubclass(cls, category):
                return category
        return None

    @args_checked
    @needs_full_cst
    def clone(
        self,
        starting_number: ty.PositiveInt = None,
        step: ty.PositiveInt = None,
        *,
        clone_multiplier: bool = True,
    ) -> Tally:
        """Clone this tally with a new number of the same tally type.

        See :meth:`~montepy.numbered_mcnp_object.Numbered_MCNP_Object.clone`.

        Parameters
        ----------
        starting_number : Integral, optional
            The starting number to request for the new object's number.
        step : Integral, optional
            The step size to use to find a new valid number.
        clone_multiplier : bool
            Whether to also clone this tally's linked ``FM`` multiplier (see
            :attr:`multiplier`) and link it to the new tally. Since ``clone``
            keeps the tally type, the multiplier still applies, so this
            defaults to ``True``.

        Returns
        -------
        Tally
            A new tally of the same type, with the same scoring groups.
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
        if clone_multiplier and multiplier is not None:
            multiplier.clone(ret)
        return ret

    @args_checked
    @needs_full_cst
    def clone_as(
        self,
        new_type: TallyType | type[Tally],
        starting_number: ty.PositiveInt = None,
        step: ty.PositiveInt = None,
        *,
        clone_multiplier: bool = False,
    ) -> Tally:
        """Clone this tally as a different tally type, keeping the same scoring geometry.

        For example, this can turn a cell flux tally into an energy deposition
        tally scoring the same cells:

        .. code-block:: python

            heating = flux_tally.clone_as(montepy.EnergyDepositionTally)
            # or, equivalently:
            heating = flux_tally.clone_as(montepy.TallyType.ENERGY_DEPOSITION)

        A :class:`CellTally` can only be cloned as another cell tally, and a
        :class:`SurfaceTally` as another surface tally, since the scoring
        geometry is made of cells or surfaces respectively.

        Parameters
        ----------
        new_type : TallyType | type[Tally]
            The target tally type, either as a :class:`TallyType` member or
            as a :class:`Tally` subclass (e.g. ``montepy.EnergyDepositionTally``).
            A subclass gives its default type, so ``EnergyDepositionTally`` is
            ``F6`` (MeV/g); use ``TallyType.ENERGY_DEPOSITION_JERKS`` for ``*F6``
            (jerks/g).
        starting_number : Integral, optional
            The starting number to request for the new object's number.
        step : Integral, optional
            The step size to use to find a new valid number.
        clone_multiplier : bool
            Whether to also clone this tally's linked ``FM`` multiplier (see
            :attr:`multiplier`) and link it to the new tally. This defaults
            to ``False``, since a multiplier written for one tally type
            often doesn't make sense for another; e.g. MCNP doesn't allow a
            multiplier on an energy-detector pulse tally.

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
            target_type = new_type
        elif isinstance(new_type, type) and issubclass(new_type, Tally):
            target_cls = new_type
            target_type = new_type._TALLY_TYPE
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
            ret = self.clone(starting_number, step, clone_multiplier=clone_multiplier)
            ret._tally_type = target_type
            return ret

        multiplier = self.multiplier
        ret = copy.deepcopy(self)
        ret.__class__ = target_cls
        ret._tally_type = target_type
        ret._multiplier = None
        new_number = self._next_number_for_type(target_type, starting_number, step)
        if self._problem:
            ret.link_to_problem(self._problem)
            ret.number = new_number
            self._problem.tallies.append(ret)
        else:
            ret.number = new_number
        if clone_multiplier and multiplier is not None:
            multiplier.clone(ret)
        return ret

    def __repr__(self):
        try:
            ttype = getattr(self, "_tally_type", None)
            ngroups = len(getattr(self, "_groups", []))
            return f"TALLY: {self.number}, type: {ttype}, groups: {ngroups}"
        except Exception:
            return "TALLY: (unparsed)"


class SurfaceTally(Tally):
    """Intermediate class for tallies that score on surfaces (``F1``, ``F2``).

    .. versionadded:: 1.6.0b2
    """

    _SCORED_COLLECTION_ATTR = "_surfaces"

    def _init_blank(self):
        super()._init_blank()
        self._surfaces = Surfaces()

    @property
    @needs_full_ast
    def surfaces(self) -> Surfaces:
        """The surfaces this tally scores over."""
        return self._surfaces

    @property
    def _scored_collection(self) -> Surfaces:
        """The collection the scored objects are kept in: :attr:`surfaces`."""
        return self.surfaces

    @args_checked
    @needs_full_cst
    def add_surface(self, *surfaces: montepy.Surface) -> None:
        """Add surfaces, each as its own scoring bin.

        Parameters
        ----------
        *surfaces : Surface
            The surfaces to add, in order.

        Raises
        ------
        ValueError
            If no surfaces are given.
        """
        if not surfaces:
            raise ValueError("At least one surface must be given.")
        for surface in surfaces:
            self._groups.append(FlatGroup([surface], is_grouped=False))
            if surface not in self._surfaces:
                self._surfaces.append(surface)

    @args_checked
    @needs_full_cst
    def add_group(self, *surfaces: montepy.Surface | list | tuple) -> None:
        """Add surfaces as a single union (averaged) bin.

        A list or tuple is a nested union, so ``add_group(s1, [s2, s3])`` is
        ``(1 (2 3))``.

        Parameters
        ----------
        *surfaces : Surface | list | tuple
            The surfaces to group, in order, or lists or tuples of them.

        Raises
        ------
        TypeError
            If an entry isn't a :class:`~montepy.Surface`, list, or tuple.
        ValueError
            If the union, or one nested in it, is empty.
        """
        self._add_union(surfaces, montepy.Surface)

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
        for s in surfaces:
            if s not in self._surfaces:
                self._surfaces.append(s)
        return pg

    @args_checked
    @needs_full_cst
    def remove_surface(self, surface: montepy.Surface) -> None:
        """Remove a surface from everywhere this tally scores it.

        After this, ``surface in tally`` is ``False``. The surface is removed
        from its own bins, from unions (``(1 2)`` becomes ``(2)``), and from
        the innermost level of ``<`` paths. A union or path left with nothing
        to score is removed.

        Parameters
        ----------
        surface : Surface
            The surface to remove.

        Raises
        ------
        OnlyInPathError
            If the surface is only a containment (outer) level of a path,
            which isn't scored, and so can't be removed.
        ValueError
            If the surface isn't in this tally at all.

        Warns
        -----
        PathContainmentWarning
            If the surface is still a containment level of a path after it
            was removed from where it was scored.
        """
        self._remove_scored(surface, montepy.Surface)

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
        self._prune_unreferenced(self._scored_entries(group))


class CellTally(Tally):
    """Intermediate class for tallies that score in cells (``F4``, ``F6``, ``F7``, ``F8``).

    .. versionadded:: 1.6.0b2
    """

    _SCORED_COLLECTION_ATTR = "_cells"

    def _init_blank(self):
        super()._init_blank()
        self._cells = Cells()

    @property
    @needs_full_ast
    def cells(self) -> Cells:
        """The cells this tally scores in."""
        return self._cells

    @property
    def _scored_collection(self) -> Cells:
        """The collection the scored objects are kept in: :attr:`cells`."""
        return self.cells

    @args_checked
    @needs_full_cst
    def add_cell(self, *cells: montepy.Cell) -> None:
        """Add cells, each as its own scoring bin.

        Parameters
        ----------
        *cells : Cell
            The cells to add, in order.

        Raises
        ------
        ValueError
            If no cells are given.
        """
        if not cells:
            raise ValueError("At least one cell must be given.")
        for cell in cells:
            self._groups.append(FlatGroup([cell], is_grouped=False))
            if cell not in self._cells:
                self._cells.append(cell)

    @args_checked
    @needs_full_cst
    def add_group(self, *cells: montepy.Cell | list | tuple) -> None:
        """Add cells as a single union (averaged) bin.

        A list or tuple is a nested union, so ``add_group(c1, [c2, c3])`` is
        ``(1 (2 3))``.

        Parameters
        ----------
        *cells : Cell | list | tuple
            The cells to group, in order, or lists or tuples of them.

        Raises
        ------
        TypeError
            If an entry isn't a :class:`~montepy.Cell`, list, or tuple.
        ValueError
            If the union, or one nested in it, is empty.
        """
        self._add_union(cells, montepy.Cell)

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
        for c in cells:
            if c not in self._cells:
                self._cells.append(c)
        return pg

    @args_checked
    @needs_full_cst
    def remove_cell(self, cell: montepy.Cell) -> None:
        """Remove a cell from everywhere this tally scores it.

        After this, ``cell in tally`` is ``False``. The cell is removed from
        its own bins, from unions (``(1 2)`` becomes ``(2)``), and from the
        innermost level of ``<`` paths. A union or path left with nothing to
        score is removed.

        Parameters
        ----------
        cell : Cell
            The cell to remove.

        Raises
        ------
        OnlyInPathError
            If the cell is only a containment (outer) level of a path, which
            isn't scored, and so can't be removed.
        ValueError
            If the cell isn't in this tally at all.

        Warns
        -----
        PathContainmentWarning
            If the cell is still a containment level of a path after it was
            removed from where it was scored.
        """
        self._remove_scored(cell, montepy.Cell)

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
        self._prune_unreferenced(self._scored_entries(group))


# ── Concrete subclasses ────────────────────────────────────────────────────────


class SurfaceCurrentTally(SurfaceTally):
    """``F1``: surface current tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.CURRENT
    _DEFAULT_SCORES = (Score.CURRENT,)


class SurfaceEnergyCurrentTally(SurfaceTally):
    """``*F1``: surface energy current tally, in MeV.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.ENERGY_CURRENT
    _DEFAULT_SCORES = (Score.ENERGY_CURRENT,)


class SurfaceFluxTally(SurfaceTally):
    """``F2``: average surface flux tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.SURFACE_FLUX
    _DEFAULT_SCORES = (Score.FLUX,)


class SurfaceEnergyFluxTally(SurfaceTally):
    """``*F2``: average surface energy flux tally, in MeV/cm2.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.SURFACE_ENERGY_FLUX
    _DEFAULT_SCORES = (Score.ENERGY_FLUX,)


class CellFluxTally(CellTally):
    """``F4``: cell flux tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.CELL_FLUX
    _DEFAULT_SCORES = (Score.FLUX,)


class CellEnergyFluxTally(CellTally):
    """``*F4``: cell energy flux tally, in MeV/cm2.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.CELL_ENERGY_FLUX
    _DEFAULT_SCORES = (Score.ENERGY_FLUX,)


class EnergyDepositionTally(CellTally):
    """``F6``: energy deposition tally.

    Also ``*F6``, the same tally in jerks/g instead of MeV/g; see
    :attr:`~montepy.Tally.tally_units`.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.ENERGY_DEPOSITION
    _OTHER_TALLY_TYPES = (TallyType.ENERGY_DEPOSITION_JERKS,)
    _DEFAULT_SCORES = (Score.ENERGY_DEPOSITION,)


class FissionEnergyDepositionTally(CellTally):
    """``F7``: fission energy deposition tally.

    Also ``*F7``, the same tally in jerks/g instead of MeV/g; see
    :attr:`~montepy.Tally.tally_units`.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.FISSION_ENERGY_DEPOSITION
    _OTHER_TALLY_TYPES = (TallyType.FISSION_ENERGY_DEPOSITION_JERKS,)
    _DEFAULT_SCORES = (Score.FISSION_ENERGY_DEPOSITION,)


class EnergyDetectorPulseTally(CellTally):
    """``F8``: energy-detector pulse height tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.ENERGY_DETECTOR_PULSE
    _DEFAULT_SCORES = (Score.PULSE_HEIGHT,)


class DetectorEnergyDepositionTally(CellTally):
    """``*F8``: energy deposition in a detector, in MeV, rather than the pulse
    height of the plain F8 tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.DETECTOR_ENERGY_DEPOSITION
    _DEFAULT_SCORES = (Score.ENERGY_DEPOSITION,)


class CollisionHeatingTally(CellTally):
    """``+F6``: collision heating tally, distinct from the plain F6 energy
    deposition tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.COLLISION_HEATING
    _DEFAULT_SCORES = (Score.COLLISION_HEATING,)
    _HAS_PARTICLES = False


class ChargeDepositionTally(CellTally):
    """``+F8``: charge deposition tally, distinct from the plain F8 pulse
    height tally.

    .. versionadded:: 1.6.0b2
    """

    _TALLY_TYPE = TallyType.CHARGE_DEPOSITION
    _DEFAULT_SCORES = (Score.CHARGE_DEPOSITION,)


_TALLY_TYPE_MAP: dict[TallyType, type[Tally]] = {
    TallyType.CURRENT: SurfaceCurrentTally,
    TallyType.ENERGY_CURRENT: SurfaceEnergyCurrentTally,
    TallyType.SURFACE_FLUX: SurfaceFluxTally,
    TallyType.SURFACE_ENERGY_FLUX: SurfaceEnergyFluxTally,
    TallyType.CELL_FLUX: CellFluxTally,
    TallyType.CELL_ENERGY_FLUX: CellEnergyFluxTally,
    TallyType.ENERGY_DEPOSITION: EnergyDepositionTally,
    TallyType.ENERGY_DEPOSITION_JERKS: EnergyDepositionTally,
    TallyType.COLLISION_HEATING: CollisionHeatingTally,
    TallyType.FISSION_ENERGY_DEPOSITION: FissionEnergyDepositionTally,
    TallyType.FISSION_ENERGY_DEPOSITION_JERKS: FissionEnergyDepositionTally,
    TallyType.ENERGY_DETECTOR_PULSE: EnergyDetectorPulseTally,
    TallyType.DETECTOR_ENERGY_DEPOSITION: DetectorEnergyDepositionTally,
    TallyType.CHARGE_DEPOSITION: ChargeDepositionTally,
}

# ── Convenience aliases ────────────────────────────────────────────────────────

F1Tally = SurfaceCurrentTally
F2Tally = SurfaceFluxTally
F4Tally = CellFluxTally
F6Tally = EnergyDepositionTally
F7Tally = FissionEnergyDepositionTally
F8Tally = EnergyDetectorPulseTally
PlusF6Tally = CollisionHeatingTally
PlusF8Tally = ChargeDepositionTally
