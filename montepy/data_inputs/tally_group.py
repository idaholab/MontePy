# Copyright 2024-2026, Battelle Energy Alliance, LLC All Rights Reserved.
"""Tally scoring-group object model: :class:`LatticeIndex`, :class:`TallyGroup`
and its concrete forms (:class:`FlatGroup`, :class:`PathGroup`), and the
:class:`Filter` hierarchy.

Split out of ``tally.py`` (mirrors ``half_space.py`` being its own file):
these are small, self-contained value objects that ``tally.py``'s ``Tally``
subclasses build and consume, not the tally-parsing machinery itself.
"""

from __future__ import annotations
from abc import ABC, abstractmethod

import montepy
from montepy.exceptions import BrokenObjectLinkError
from montepy.input_parser import syntax_node
import montepy.types as ty
from montepy.utilities import *


def _make_value_node(value_type, default, padding=" ", never_pad=False):
    """Build a fresh :class:`~montepy.input_parser.syntax_node.ValueNode`.

    Mirrors :func:`montepy.mcnp_object.MCNP_Object._generate_default_node`,
    duplicated here since ``FlatGroup``/``PathGroup`` aren't ``MCNP_Object``
    subclasses and so don't inherit that helper.
    """
    padding_node = syntax_node.PaddingNode(padding) if padding else None
    if default is None:
        return syntax_node.ValueNode(default, value_type, padding_node, never_pad)
    return syntax_node.ValueNode(str(default), value_type, padding_node, never_pad)


class LatticeIndex:
    """A lattice element index ``[i j k]`` in a tally path specification.

    .. versionadded:: 1.6.0b2

    Parameters
    ----------
    dimensions : list[Integral | tuple[Integral, Integral]]
        Each entry is either a single element index, or a ``(start, stop)``
        range (``i1:i2``).
    """

    __slots__ = ("_dimensions",)

    @args_checked
    def __init__(self, dimensions: list[ty.Integral | tuple[ty.Integral, ty.Integral]]):
        self._dimensions = tuple(dimensions)

    @property
    def dimensions(self):
        """The indices or (start, end) ranges."""
        return self._dimensions

    @property
    def node(self) -> syntax_node.ListNode:
        """Build a fresh ``ListNode("lattice phrase")`` from these dimensions.

        Inverse of :meth:`parse_input_node`. Freshly-built dimensions are
        always space-separated (the common ``[i j k]`` single-element-index
        form); the data model doesn't distinguish that from a comma-separated
        list once parsed, so there's no lossless "original style" to
        preserve here anyway.

        .. versionadded:: 1.6.0b4
        """
        node = syntax_node.ListNode("lattice phrase")
        node.append(syntax_node.PaddingNode("["))
        dims = self._dimensions
        for i, dim in enumerate(dims):
            if isinstance(dim, tuple):
                item = syntax_node.ListNode("lattice range")
                item.append(_make_value_node(int, dim[0], padding=None))
                item.append(syntax_node.PaddingNode(":"))
                item.append(_make_value_node(int, dim[1], padding=None))
                node.append(item)
            else:
                node.append(_make_value_node(int, dim, padding=None))
            if i != len(dims) - 1:
                node.append(syntax_node.PaddingNode(" "))
        node.append(syntax_node.PaddingNode("]"))
        return node

    @staticmethod
    def parse_input_node(lattice_node) -> LatticeIndex:
        """Parse a ``ListNode("lattice phrase")`` into a :class:`LatticeIndex`.

        .. versionadded:: 1.6.0b4
        """
        dimensions = []
        for n in lattice_node.nodes:
            if isinstance(n, syntax_node.PaddingNode):
                continue
            if isinstance(n, syntax_node.ListNode) and n.name == "lattice range":
                vals = [
                    m.value for m in n.nodes if isinstance(m, syntax_node.ValueNode)
                ]
                if len(vals) >= 2:
                    dimensions.append((int(vals[0]), int(vals[1])))
            elif isinstance(n, syntax_node.ValueNode) and isinstance(
                n.value, (int, float)
            ):
                dimensions.append(int(n.value))
        return LatticeIndex(dimensions)

    def __repr__(self):
        return f"LatticeIndex({self._dimensions})"


class TallyGroup(ABC):
    """Abstract base for a tally scoring group.

    .. versionadded:: 1.6.0b2
    """

    @abstractmethod
    def __contains__(self, item) -> bool:
        pass


class Filter(ABC):
    """Abstract analog of an OpenMC-style tally filter.

    .. versionadded:: 1.6.0b2
    """


class ParticleFilter(Filter):
    """Filters a tally to the particle types in its classifier (e.g. ``:n,p``).

    A thin wrapper around the underlying
    :class:`~montepy.input_parser.syntax_node.ParticleNode`, mirroring
    :class:`~montepy.Mode`'s design: particle *membership* is what matters, not
    order. Two filters with the same particles compare equal no matter what order
    they were written in (``:n,p`` == ``:p,n``); order is only ever meaningful when
    the underlying node formats itself back to MCNP text.

    .. versionadded:: 1.6.0b2

    Parameters
    ----------
    particles : montepy.input_parser.syntax_node.ParticleNode, list[montepy.Particle], set[montepy.Particle]
        The parsed node backing this filter's particles, or a plain collection of
        particles to build one from.
    """

    __slots__ = ("_node",)

    @args_checked
    def __init__(
        self,
        particles: (
            syntax_node.ParticleNode | list[montepy.Particle] | set[montepy.Particle]
        ),
    ):
        if isinstance(particles, syntax_node.ParticleNode):
            self._node = particles
        else:
            token = ",".join(p.value for p in particles)
            self._node = syntax_node.ParticleNode("particle_filter", token)

    @property
    def particles(self) -> set[montepy.Particle]:
        """The particles this tally is restricted to."""
        return set(self._node.particles)

    def __eq__(self, other):
        if not isinstance(other, ParticleFilter):
            return NotImplemented
        return self.particles == other.particles

    def __repr__(self):
        return f"ParticleFilter({self._node.format()!r})"


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
    items : list[Integral | montepy.Cell | montepy.Surface]
        Cell/surface numbers, or the live objects themselves (e.g. from
        :meth:`~montepy.CellTally.add_cell`). Mirrors
        :attr:`~montepy.UnitHalfSpace.divider`'s "store whatever's given"
        design.
    lattice_indices : list[LatticeIndex | None], optional
        Lattice indices parallel to ``items``.
    is_grouped : bool
        ``True`` = parenthesized union (one averaged bin);
        ``False`` = separate bins.
    universe_spec : Integral, optional
        Universe number if ``U=N`` syntax was used.
    """

    __slots__ = (
        "_items",
        "_old_numbers",
        "_lattice_indices",
        "_is_grouped",
        "_universe_spec",
        "_node",
        "_number_nodes",
    )

    @args_checked
    def __init__(
        self,
        items: list[ty.Integral | montepy.Cell | montepy.Surface],
        lattice_indices: list[LatticeIndex | None] | None = None,
        *,
        is_grouped: bool,
        universe_spec: ty.Integral | None = None,
        node: syntax_node.SyntaxNodeBase | None = None,
        number_nodes: list | None = None,
    ):
        self._items = list(items)
        # A frozen snapshot of the numbers as given here -- deliberately
        # never updated even after update_pointers() resolves an entry, or
        # after a resolved object is later renumbered. Needed so a renumber
        # can be detected (the shortcut-group staleness check in
        # _update_node) and so old_numbers keeps meaning "as originally
        # read/added", not "as of right now".
        self._old_numbers = [self._number_of(item) for item in self._items]
        self._lattice_indices = lattice_indices or [None] * len(self._items)
        self._is_grouped = is_grouped
        self._universe_spec = universe_spec
        self._node = node
        self._number_nodes = list(number_nodes) if number_nodes else []

    @staticmethod
    def _number_of(item: ty.Integral | montepy.Cell | montepy.Surface) -> ty.Integral:
        return item if isinstance(item, ty.Integral) else item.number

    @property
    def old_numbers(self):
        """The cell/surface numbers as originally read or added."""
        return list(self._old_numbers)

    @property
    def is_grouped(self):
        """``True`` if entries form a union bin (parenthesized)."""
        return self._is_grouped

    @property
    def universe_spec(self):
        """Universe number if ``U=N`` syntax was used, else ``None``."""
        return self._universe_spec

    @property
    def lattice_indices(self):
        """The :class:`LatticeIndex` for each number, parallel to :attr:`old_numbers`.

        .. versionadded:: 1.6.0b3
        """
        return list(self._lattice_indices)

    @property
    def cells_or_surfaces(self):
        """The resolved :class:`~montepy.Cell`/:class:`~montepy.Surface` objects
        this group covers, once linked to a problem. Empty if not yet linked.

        .. versionadded:: 1.6.0b3
        """
        return [item for item in self._items if not isinstance(item, ty.Integral)]

    @property
    def cells(self) -> list[montepy.Cell] | None:
        """The :class:`~montepy.Cell` objects this group covers, or ``None``
        if this group isn't (fully resolved to be) cell-based.

        .. versionadded:: 1.6.0b4

        Returns
        -------
        list[Cell] | None
            The resolved cells, or ``None``.
        """
        objs = self.cells_or_surfaces
        if not objs or len(objs) != len(self._items):
            return None
        if not all(isinstance(o, montepy.Cell) for o in objs):
            return None
        return objs

    @property
    def surfaces(self) -> list[montepy.Surface] | None:
        """The :class:`~montepy.Surface` objects this group covers, or
        ``None`` if this group isn't (fully resolved to be) surface-based.

        .. versionadded:: 1.6.0b4

        Returns
        -------
        list[Surface] | None
            The resolved surfaces, or ``None``.
        """
        objs = self.cells_or_surfaces
        if not objs or len(objs) != len(self._items):
            return None
        if not all(isinstance(o, montepy.Surface) for o in objs):
            return None
        return objs

    def update_pointers(
        self, container, *, is_cell: bool, tally: montepy.data_inputs.tally.Tally
    ) -> None:
        """Resolve any still-raw numbers into live :class:`~montepy.Cell`/
        :class:`~montepy.Surface` objects.

        Mirrors :meth:`~montepy.UnitHalfSpace.update_pointers`.

        .. versionadded:: 1.6.0b4

        Parameters
        ----------
        container : Cells | Surfaces
            The problem's live collection to resolve numbers against.
        is_cell : bool
            Whether entries should resolve to :class:`~montepy.Cell` (``True``)
            or :class:`~montepy.Surface` (``False``).
        tally : Tally
            The tally this group belongs to, used only to give a clear error
            if a number can't be resolved.
        """
        kind = "Cell" if is_cell else "Surface"
        for i, item in enumerate(self._items):
            if isinstance(item, ty.Integral):
                try:
                    self._items[i] = container[item]
                except KeyError:
                    raise BrokenObjectLinkError("Tally", tally.number, kind, item)

    def _current_numbers(self):
        """The numbers to write out: live cell/surface numbers if linked,
        else the numbers as originally read."""
        return [self._number_of(item) for item in self._items]

    @property
    def node(self):
        """The syntax node for this group.

        If this was generated by parsing, that node (patched to reflect
        current numbers) is returned. If this was created from scratch, a
        new node is generated the first time this is accessed.

        .. versionadded:: 1.6.0b3
        """
        self._ensure_has_node()
        self._update_node()
        return self._node

    def _ensure_has_node(self):
        if self._node is not None:
            return
        body = syntax_node.ListNode("flat group body")
        if self._universe_spec is not None:
            body.append(_make_value_node(str, "u", padding=None))
            body.append(syntax_node.PaddingNode("="))
            spec_node = _make_value_node(int, self._universe_spec, padding=None)
            body.append(spec_node)
        numbers = self._current_numbers()
        self._number_nodes = []
        for i, num in enumerate(numbers):
            num_node = _make_value_node(int, num, padding=" ")
            self._number_nodes.append(num_node)
            body.append(num_node)
            idx = self._lattice_indices[i] if i < len(self._lattice_indices) else None
            if idx is not None:
                body.append(idx.node)
        if self._is_grouped:
            wrapped = syntax_node.ListNode("tally group")
            wrapped.append(syntax_node.PaddingNode("("))
            for n in body.nodes:
                wrapped.append(n)
            wrapped.append(syntax_node.PaddingNode(")"))
            self._node = wrapped
        else:
            self._node = body

    def _update_node(self):
        numbers = self._current_numbers()
        if not self._number_nodes and self.cells_or_surfaces:
            # This group used an MCNP shortcut (e.g. "3i") -- only the
            # ShortcutNode itself knows how to recompress, so there's
            # nothing here to live-patch. Fail loudly rather than silently
            # writing stale text if something inside it was renumbered.
            if not set(numbers).issubset(self._old_numbers):
                raise montepy.exceptions.IllegalState(
                    f"Cannot write group {self._old_numbers}: it used an "
                    'MCNP shortcut (e.g. "3i"), and one of its cells/'
                    "surfaces was renumbered. Live-renumbering isn't "
                    "supported inside a shortcut-written group."
                )
            return
        for num_node, num in zip(self._number_nodes, numbers):
            if num_node.value != num:
                num_node.value = num

    def __contains__(self, item) -> bool:
        objs = self.cells_or_surfaces
        if objs:
            return item in objs
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

    __slots__ = ("_levels", "_node")

    @args_checked
    def __init__(
        self,
        levels: list[FlatGroup],
        node: syntax_node.SyntaxNodeBase | None = None,
    ):
        self._levels = list(levels)
        self._node = node

    @property
    def levels(self):
        """FlatGroup levels, innermost (scored) first."""
        return list(self._levels)

    @property
    def old_numbers(self):
        """The innermost (scored) level's numbers as originally read or added.

        .. versionadded:: 1.6.0b4
        """
        if not self._levels:
            return []
        return self._levels[0].old_numbers

    @property
    def cells_or_surfaces(self):
        """The innermost (scored) level's resolved objects.

        Per the MCNP manual's tally-specification chapter, only the
        leftmost/innermost entry in a ``<``-chain is actually *tallied*;
        every outer level is a containment cell (filled with a universe)
        used only to select which occurrence is meant, never itself
        scored -- so only the innermost level's objects count as "what
        this tally covers".

        .. versionadded:: 1.6.0b4
        """
        if not self._levels:
            return []
        return self._levels[0].cells_or_surfaces

    def update_pointers(
        self, container, *, is_cell: bool, tally: montepy.data_inputs.tally.Tally
    ) -> None:
        """Resolve the innermost (scored) level's numbers into live objects.

        Outer (containment) levels are deliberately left unresolved --
        they're never "in" the tally (see ``PathGroup.__contains__``),
        so there's nothing to gain by tracking live renumbers for them.

        .. versionadded:: 1.6.0b4
        """
        if self._levels:
            self._levels[0].update_pointers(container, is_cell=is_cell, tally=tally)

    @property
    def node(self):
        """The syntax node for this path group.

        .. versionadded:: 1.6.0b3
        """
        self._ensure_has_node()
        self._update_node()
        return self._node

    def _ensure_has_node(self):
        if self._node is not None:
            for level in self._levels:
                level._ensure_has_node()
            return
        body = syntax_node.ListNode("flat group body")
        for i, level in enumerate(self._levels):
            level._ensure_has_node()
            level._update_node()
            if isinstance(level.node, syntax_node.ListNode):
                for n in level.node.nodes:
                    body.append(n)
            else:
                body.append(level.node)
            if i != len(self._levels) - 1:
                body.append(_make_value_node(str, "<", padding=" "))
        wrapped = syntax_node.ListNode("tally group")
        wrapped.append(syntax_node.PaddingNode("("))
        for n in body.nodes:
            wrapped.append(n)
        wrapped.append(syntax_node.PaddingNode(")"))
        self._node = wrapped

    def _update_node(self):
        for level in self._levels:
            level._update_node()

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
        lattice : list[Integral], optional
            Lattice index dimensions for the first element.

        Returns
        -------
        PathGroup
            ``self``, for method chaining.
        """
        indices = [None] * len(cells_or_surfaces)
        if lattice is not None and cells_or_surfaces:
            indices[0] = LatticeIndex(lattice)
        is_grouped = len(cells_or_surfaces) > 1
        level = FlatGroup(list(cells_or_surfaces), indices, is_grouped=is_grouped)
        self._levels.append(level)
        return self

    def __contains__(self, item) -> bool:
        """Whether ``item`` is scored by this path.

        Only the innermost level (``self._levels[0]``, what's actually
        scored) is checked -- an outer level is a containment constraint
        ("...inside cell 5"), not itself scored, so it deliberately isn't
        considered "in" the tally. For ``f104:n (2 < 5)``, cell 2 is in the
        group; cell 5 is not.
        """
        if not self._levels:
            return False
        return item in self._levels[0]

    def __repr__(self):
        return f"PathGroup(levels={len(self._levels)})"


def _extract_numbers_with_lattice(nodes):
    """Pair each numeric ValueNode with its immediately following lattice phrase.

    Returns ``(numbers, lattice_indices, number_nodes)`` where
    ``lattice_indices[i]`` is a :class:`LatticeIndex` or ``None``, and
    ``number_nodes[i]`` is the real, original :class:`~montepy.input_parser.syntax_node.ValueNode`
    parsed for that number (kept so it can be patched in place later instead
    of rebuilt, preserving the original formatting/whitespace).

    If an MCNP shortcut (e.g. ``3i``) is present, ``number_nodes`` is left
    empty for the whole group: a shortcut's "virtual" expanded value nodes
    aren't meant to be formatted/patched individually (only the
    :class:`~montepy.input_parser.syntax_node.ShortcutNode` itself knows how
    to compress back to e.g. ``3i``), so live-renumbering isn't supported for
    a group that used one -- it keeps its original compressed text as-is.
    """
    numbers = []
    lattice_indices = []
    number_nodes = []
    has_shortcut = False
    i = 0
    while i < len(nodes):
        n = nodes[i]
        if isinstance(n, syntax_node.ShortcutNode):
            has_shortcut = True
            for inner in n.nodes:
                if isinstance(inner.value, (int, float)) and not isinstance(
                    inner.value, bool
                ):
                    numbers.append(int(inner.value))
                    lattice_indices.append(None)
        elif (
            isinstance(n, syntax_node.ValueNode)
            and isinstance(n.value, (int, float))
            and not isinstance(n.value, bool)
        ):
            numbers.append(int(n.value))
            number_nodes.append(n)
            if (
                i + 1 < len(nodes)
                and isinstance(nodes[i + 1], syntax_node.ListNode)
                and nodes[i + 1].name == "lattice phrase"
            ):
                lattice_indices.append(LatticeIndex.parse_input_node(nodes[i + 1]))
                i += 2
                continue
            else:
                lattice_indices.append(None)
        i += 1
    if has_shortcut:
        number_nodes = []
    return numbers, lattice_indices, number_nodes


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


def _parse_body_segment(nodes, *, is_grouped, node=None) -> FlatGroup:
    numbers, lattice_indices, number_nodes = _extract_numbers_with_lattice(nodes)
    universe_spec = _extract_universe_spec_from_nodes(nodes)
    if node is None and nodes:
        wrapper = syntax_node.ListNode("flat group body")
        for n in nodes:
            wrapper.append(n)
        node = wrapper
    return FlatGroup(
        numbers,
        lattice_indices,
        is_grouped=is_grouped,
        universe_spec=universe_spec,
        node=node,
        number_nodes=number_nodes,
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
        return _parse_body_segment(inner_body, is_grouped=True, node=non_pad[0])
    return _parse_body_segment(seg, is_grouped=False)


def _parse_tally_group_node(group_node) -> TallyGroup:
    nodes = list(group_node.nodes)
    for i, n in enumerate(nodes):
        if (
            isinstance(n, syntax_node.ValueNode)
            and n.padding is None
            and i + 1 < len(nodes)
            and not isinstance(nodes[i + 1], syntax_node.PaddingNode)
        ):
            n.never_pad = True
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
        return _parse_body_segment(body, is_grouped=True, node=group_node)

    segments = []
    start = 0
    for sep_i in path_sep_indices:
        segments.append(body[start:sep_i])
        start = sep_i + 1
    segments.append(body[start:])

    return PathGroup(
        [_parse_segment_as_level(seg) for seg in segments], node=group_node
    )


def _parse_tally_numbers(tally_numbers_node) -> list[TallyGroup]:
    groups = []
    for node in tally_numbers_node:
        if isinstance(node, syntax_node.ValueNode):
            v = node.value
            if v is None:
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                wrapper = syntax_node.ListNode("flat group body")
                wrapper.append(node)
                groups.append(
                    FlatGroup(
                        [int(v)], is_grouped=False, node=wrapper, number_nodes=[node]
                    )
                )
        elif isinstance(node, syntax_node.ListNode) and node.name == "tally group":
            groups.append(_parse_tally_group_node(node))
    return groups
