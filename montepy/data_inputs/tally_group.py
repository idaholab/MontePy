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
from montepy.exceptions import BrokenObjectLinkError, UnsupportedFeature
from montepy.input_parser import syntax_node
from montepy.input_parser.tally_parser import _append_tally_item, _is_run, _next_key
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
    """The lattice elements in brackets after a lattice cell in a tally path.

    In ``F4:n (1 < 2[0 0 0] < 3)``, cell 2 is a lattice, and ``[0 0 0]`` limits
    the tally to cell 1 only when it is inside lattice element ``[0, 0, 0]`` of
    cell 2. Without the brackets, cell 1 would be scored in every element of
    cell 2. MCNP accepts three forms inside the brackets:

    * ``[n]``: the n-th lattice element of the cell, counted in the order of
      its ``FILL`` array.
    * ``[i j k]``: the single element at lattice indices ``i, j, k``. Any of the
      three can be a range ``i1:i2`` instead, as on a ``FILL`` card, to select
      every element in that range, e.g. ``[-1:1 0:1 0]``.
    * ``[i1 j1 k1, i2 j2 k2]``: a comma-separated list of individual elements.

    :attr:`elements` holds one tuple per comma-separated element. Each entry
    in it is an ``int`` for a single index, or an ``(i1, i2)`` tuple for a
    range.

    .. versionadded:: 1.6.0b2

    Parameters
    ----------
    elements : list[list[Integral | tuple[Integral, Integral]]]
        One list per comma-separated element. Each entry is either a single
        lattice index, or a ``(start, stop)`` range (``i1:i2``).

    Examples
    --------

    A lattice index is reached through the
    :attr:`~montepy.data_inputs.tally.FlatGroup.lattice_indices` of a path's
    level. Levels go from innermost to outermost, so cell 2 is ``levels[1]``:

    .. doctest::

        >>> import montepy
        >>> tally = montepy.Tally.from_input("F4:n (1 < 2[0 0 0] < 3)")
        >>> tally.groups[0].levels[1].lattice_indices[0].elements
        ((0, 0, 0),)

    A range becomes a ``(start, stop)`` tuple:

    .. doctest::

        >>> tally = montepy.Tally.from_input("F4:n (1 < 2[-1:1 0:1 0] < 3)")
        >>> tally.groups[0].levels[1].lattice_indices[0].elements
        (((-1, 1), (0, 1), 0),)

    A single number is the element's position in the ``FILL`` array:

    .. doctest::

        >>> tally = montepy.Tally.from_input("F4:n (1 < 2[5] < 3)")
        >>> tally.groups[0].levels[1].lattice_indices[0].elements
        ((5,),)

    A comma-separated list gives one tuple per element:

    .. doctest::

        >>> tally = montepy.Tally.from_input("F4:n (1 < 2[0 0 0, 0 1 0] < 3)")
        >>> tally.groups[0].levels[1].lattice_indices[0].elements
        ((0, 0, 0), (0, 1, 0))

    To build a path with a lattice index, pass the indices as ``lattice`` to
    :meth:`~montepy.data_inputs.tally.PathGroup.inside`.
    """

    __slots__ = ("_elements",)

    @args_checked
    def __init__(
        self, elements: list[list[ty.Integral | tuple[ty.Integral, ty.Integral]]]
    ):
        self._elements = tuple(tuple(element) for element in elements)

    @property
    def elements(self) -> tuple[tuple[int | tuple[int, int], ...], ...]:
        """The lattice elements, each a tuple of indices or (start, end) ranges.

        .. versionadded:: 1.6.0b4
        """
        return self._elements

    @property
    def node(self) -> syntax_node.ListNode:
        """Build a fresh ``ListNode("lattice phrase")`` from these elements.

        Inverse of :meth:`parse_input_node`. Indices within an element are
        space-separated, and elements are separated by ``", "``.

        .. versionadded:: 1.6.0b4
        """
        node = syntax_node.ListNode("lattice phrase")
        node.append(syntax_node.PaddingNode("["))
        for i, element in enumerate(self._elements):
            if i != 0:
                node.append(syntax_node.PaddingNode(", "))
            for j, dim in enumerate(element):
                if j != 0:
                    node.append(syntax_node.PaddingNode(" "))
                if isinstance(dim, tuple):
                    item = syntax_node.ListNode("lattice range")
                    item.append(_make_value_node(int, dim[0], padding=None))
                    item.append(syntax_node.PaddingNode(":"))
                    item.append(_make_value_node(int, dim[1], padding=None))
                    node.append(item)
                else:
                    node.append(_make_value_node(int, dim, padding=None))
        node.append(syntax_node.PaddingNode("]"))
        return node

    @staticmethod
    def parse_input_node(lattice_node) -> LatticeIndex:
        """Parse a ``ListNode("lattice phrase")`` into a :class:`LatticeIndex`.

        .. versionadded:: 1.6.0b4
        """
        elements = [[]]
        for n in lattice_node.nodes:
            if isinstance(n, syntax_node.PaddingNode):
                if n.format().strip() == ",":
                    elements.append([])
                continue
            if isinstance(n, syntax_node.ListNode) and n.name == "lattice range":
                vals = [
                    m.value for m in n.nodes if isinstance(m, syntax_node.ValueNode)
                ]
                if len(vals) >= 2:
                    elements[-1].append((int(vals[0]), int(vals[1])))
            elif isinstance(n, syntax_node.ValueNode) and isinstance(
                n.value, (int, float)
            ):
                elements[-1].append(int(n.value))
        return LatticeIndex(elements)

    def __repr__(self):
        return f"LatticeIndex({self._elements})"


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
    """A list of cells/surfaces to score over: a union, or a set of separate bins.

    Used as both a top-level bin and as an individual level in a
    :class:`PathGroup` chain. A member can itself be a parenthesized union,
    e.g. the ``(2 3)`` in ``(1 (2 3) < 5)``, as a nested ``FlatGroup``.

    .. versionadded:: 1.6.0b2

    .. versionchanged:: 1.6.0b4
        A member can be a nested union ``FlatGroup``.

    Parameters
    ----------
    items : list[Integral | montepy.Cell | montepy.Surface | FlatGroup]
        Cell/surface numbers, the live objects themselves (e.g. from
        :meth:`~montepy.CellTally.add_cell`), or nested unions. Mirrors
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
        items: list[ty.Integral | montepy.Cell | montepy.Surface | FlatGroup],
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
        # after a resolved object is later renumbered, so old_numbers keeps
        # meaning "as originally read/added", not "as of right now". None for
        # a nested union.
        self._old_numbers = [self._number_of(item) for item in self._items]
        self._lattice_indices = lattice_indices or [None] * len(self._items)
        self._is_grouped = is_grouped
        self._universe_spec = universe_spec
        self._node = node
        # Parallel to _items: the ValueNode holding each number, or None for
        # a nested union. Empty until the tree is built.
        self._number_nodes = list(number_nodes) if number_nodes else []

    @staticmethod
    def _number_of(
        item: ty.Integral | montepy.Cell | montepy.Surface | FlatGroup,
    ) -> ty.Integral | None:
        if isinstance(item, FlatGroup):
            return None
        return item if isinstance(item, ty.Integral) else item.number

    def _leaves(self):
        """Every scored entry, including those in nested unions, in order.

        Yields ``(entry, old_number, lattice_index)``.
        """
        for item, number, index in zip(
            self._items, self._old_numbers, self._lattice_indices
        ):
            if isinstance(item, FlatGroup):
                yield from item._leaves()
            else:
                yield item, number, index

    @property
    def members(self) -> list[ty.Integral | montepy.Cell | montepy.Surface | FlatGroup]:
        """The entries of this group, in order.

        Each is a :class:`~montepy.Cell`/:class:`~montepy.Surface` (or its
        number, if not linked to a problem yet), or a nested union
        :class:`FlatGroup`, e.g. the ``(2 3)`` in ``(1 (2 3))``.

        .. versionadded:: 1.6.0b4
        """
        return list(self._items)

    @property
    def old_numbers(self):
        """The cell/surface numbers as originally read or added, including
        those in nested unions."""
        return [number for _, number, _ in self._leaves()]

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
        return [index for _, _, index in self._leaves()]

    @property
    def cells_or_surfaces(self):
        """The resolved :class:`~montepy.Cell`/:class:`~montepy.Surface` objects
        this group covers, including those in nested unions, once linked to a
        problem. Empty if not yet linked.

        .. versionadded:: 1.6.0b3
        """
        return [
            entry
            for entry, _, _ in self._leaves()
            if not isinstance(entry, ty.Integral)
        ]

    def _all_of(self, kind) -> list | None:
        objs = self.cells_or_surfaces
        if not objs or len(objs) != len(self.old_numbers):
            return None
        if not all(isinstance(o, kind) for o in objs):
            return None
        return objs

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
        return self._all_of(montepy.Cell)

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
        return self._all_of(montepy.Surface)

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
            if isinstance(item, FlatGroup):
                item.update_pointers(container, is_cell=is_cell, tally=tally)
            elif isinstance(item, ty.Integral):
                try:
                    self._items[i] = container[item]
                except KeyError:
                    raise BrokenObjectLinkError("Tally", tally.number, kind, item)

    def _remove_matching(self, matches) -> bool:
        """Remove every entry, including in nested unions, for which ``matches(entry)``.

        A nested union left empty is removed too.

        Returns
        -------
        bool
            Whether anything was removed.
        """
        found = False
        for i in reversed(range(len(self._items))):
            item = self._items[i]
            if isinstance(item, FlatGroup):
                if item._remove_matching(matches):
                    found = True
                    if not item._items:
                        self._remove_item(i)
            elif matches(item):
                found = True
                self._remove_item(i)
        return found

    def _remove_item(self, index: int) -> None:
        """Remove the member at ``index``, with its lattice index, from this group and its tree.

        A shortcut it was part of is re-zipped around the remaining values.

        .. versionadded:: 1.6.0b4
        """
        item = self._items.pop(index)
        del self._old_numbers[index]
        del self._lattice_indices[index]
        if not self._number_nodes:
            return
        num_node = self._number_nodes.pop(index)
        if isinstance(item, FlatGroup):
            self._remove_child(item._node)
        else:
            self._remove_number_node(num_node)

    def _remove_child(self, child) -> None:
        """Remove ``child``, or the lattice cell holding it, from this group's tree."""
        if isinstance(self._node, syntax_node.ListNode):
            nodes = self._node.nodes
            for i, node in enumerate(nodes):
                if node is child or (
                    _is_lattice_cell(node)
                    and any(v is child for v in node.nodes[("run", 0)])
                ):
                    del nodes[i]
                    return
            return
        for key, node in list(self._node.nodes.items()):
            if node is child:
                text = child.format()
                space = text[len(text.rstrip()) :]
                self._drop_key(key, syntax_node.PaddingNode(space) if space else None)
                return

    def _drop_key(self, key, trailing) -> None:
        """Delete the child at ``key`` from this group's tree.

        If it was the last entry, the entry before it takes over its trailing
        padding, so ``(1 2[0 0 0])`` becomes ``(1)``, not ``(1 )``.
        """
        keys = list(self._node.nodes)
        i = keys.index(key)
        del self._node.nodes[key]
        following = keys[i + 1] if i + 1 < len(keys) else None
        if following not in (None, "end_pad") or i == 0:
            return
        previous = self._node.nodes.get(keys[i - 1])
        if previous is not None:
            _set_trailing_padding(previous, trailing)

    def _remove_number_node(self, num_node) -> None:
        if isinstance(self._node, syntax_node.ListNode):
            self._remove_child(num_node)
            return
        for key, child in list(self._node.nodes.items()):
            cell = child if _is_lattice_cell(child) else None
            run = cell.nodes[("run", 0)] if cell is not None else child
            if not _is_run(run):
                continue
            values = list(run)
            if not any(v is num_node for v in values):
                continue
            # The padding after the removed number: its own, or, if a lattice
            # index follows it, the lattice's. A lattice index always follows
            # its cell's last value.
            trailing = num_node.padding
            if cell is not None and values[-1] is num_node:
                lattice = cell.nodes.pop("lattice")
                tail = lattice.nodes[-2:]
                trailing = tail[-1] if tail[0].format() == "]" else None
            remaining = [v for v in values if v is not num_node]
            if remaining:
                if values[-1] is num_node and any(
                    n is remaining[-1] for n in run.nodes
                ):
                    # The new last value takes over the trailing padding, so
                    # "(1 2 3)" becomes "(1 2)", not "(1 2 )".
                    remaining[-1].padding = trailing
                run.update_with_new_values(remaining)
            else:
                self._drop_key(key, trailing)
            return

    def _current_numbers(self):
        """The numbers to write out, parallel to the members: live cell/surface
        numbers if linked, else the numbers as originally read. ``None`` for a
        nested union."""
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
            for item in self._items:
                if isinstance(item, FlatGroup):
                    item._ensure_has_node()
            return
        entries = []
        if self._universe_spec is not None:
            universe = syntax_node.ListNode("universe phrase")
            universe.append(_make_value_node(str, "u", padding=None))
            universe.append(syntax_node.PaddingNode("="))
            universe.append(_make_value_node(int, self._universe_spec, padding=None))
            entries.append(universe)
        self._number_nodes = []
        for i, (item, num, idx) in enumerate(
            zip(self._items, self._current_numbers(), self._lattice_indices)
        ):
            if isinstance(item, FlatGroup):
                item._ensure_has_node()
                self._number_nodes.append(None)
                if i != len(self._items) - 1:
                    # Otherwise it is glued to the next entry: "(2 3)(4)".
                    _set_trailing_padding(item._node, syntax_node.PaddingNode(" "))
                entries.append(item._node)
                continue
            # MCNP requires the brackets to immediately follow the cell number.
            num_node = _make_value_node(int, num, padding=" " if idx is None else None)
            self._number_nodes.append(num_node)
            if idx is None:
                entries.append(num_node)
                continue
            cell = syntax_node.SyntaxNode("lattice cell", {})
            _append_tally_item(cell, num_node)
            lattice_node = idx.node
            lattice_node.append(syntax_node.PaddingNode(" "))
            cell.nodes["lattice"] = lattice_node
            entries.append(cell)
        if self._is_grouped:
            self._node = _make_group_node(entries)
        else:
            self._node = syntax_node.ListNode("flat group body")
            for entry in entries:
                self._node.append(entry)

    def _update_node(self):
        for item, num_node, num in zip(
            self._items, self._number_nodes, self._current_numbers()
        ):
            if isinstance(item, FlatGroup):
                item._update_node()
            elif num_node is not None and num_node.value != num:
                num_node.value = num

    def __contains__(self, item) -> bool:
        for entry, number, _ in self._leaves():
            if isinstance(entry, ty.Integral):
                if hasattr(item, "old_number") and item.old_number == number:
                    return True
                if hasattr(item, "number") and item.number == number:
                    return True
            elif entry is item or entry == item:
                return True
        return False

    def __repr__(self):
        return f"FlatGroup({self.old_numbers}, grouped={self._is_grouped})"


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
        node = syntax_node.SyntaxNode(
            "tally group", {"start_pad": syntax_node.PaddingNode("(")}
        )
        for i, level in enumerate(self._levels):
            if i != 0:
                node.nodes[_next_key(node, "sep")] = _make_value_node(
                    str, "<", padding=" "
                )
            node.nodes[_next_key(node, "level")] = self._level_node(level)
        node.nodes["end_pad"] = syntax_node.PaddingNode(")")
        self._node = node

    @staticmethod
    def _level_node(level: FlatGroup) -> syntax_node.SyntaxNode:
        """Build the ``"tally level"`` node for a level made from scratch."""
        level._ensure_has_node()
        level._update_node()
        level_node = syntax_node.SyntaxNode("tally level", {})
        if _is_group_node(level._node):
            _append_tally_item(level_node, level._node)
        else:
            for entry in level._node.nodes:
                _append_tally_item(level_node, entry)
            # The level now edits its entries where they are in this path.
            level._node = level_node
        return level_node

    def _append_level_node(self, level: FlatGroup) -> None:
        """Add a new outermost level to this path's existing tree."""
        nodes = self._node.nodes
        end_pad = nodes.pop("end_pad")
        last_level = nodes[[key for key in nodes if key != "start_pad"][-1]]
        last_entry = list(last_level.nodes.values())[-1]
        if not last_level.format()[-1:].isspace():
            # Keep the new "<" from being glued to the old outermost level.
            _set_trailing_padding(last_entry, syntax_node.PaddingNode(" "))
        nodes[_next_key(self._node, "sep")] = _make_value_node(str, "<", padding=" ")
        nodes[_next_key(self._node, "level")] = self._level_node(level)
        nodes["end_pad"] = end_pad

    def _update_node(self):
        for level in self._levels:
            level._update_node()

    @args_checked
    def inside(
        self,
        *cells_or_surfaces: montepy.Cell | montepy.Surface,
        lattice: list[ty.Integral | tuple[ty.Integral, ty.Integral]] | None = None,
    ) -> PathGroup:
        """Append an outer level and return self for chaining.

        Parameters
        ----------
        cells_or_surfaces : Cell | Surface
            Objects at this level.
        lattice : list[Integral | tuple[Integral, Integral]], optional
            The indices of one lattice element (e.g. ``[0, 0, 0]``) for the
            first object at this level.

        Returns
        -------
        PathGroup
            ``self``, for method chaining.
        """
        indices = [None] * len(cells_or_surfaces)
        if lattice is not None and cells_or_surfaces:
            indices[0] = LatticeIndex([lattice])
        is_grouped = len(cells_or_surfaces) > 1
        level = FlatGroup(list(cells_or_surfaces), indices, is_grouped=is_grouped)
        self._levels.append(level)
        if self._node is not None:
            self._append_level_node(level)
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


def _is_group_node(node) -> bool:
    return isinstance(node, syntax_node.SyntaxNode) and node.name == "tally group"


def _set_trailing_padding(node, padding) -> None:
    """Replace the padding at the end of a tree entry with ``padding`` (or none)."""
    if _is_run(node) and node.nodes:
        last = node.nodes[-1]
        if isinstance(last, syntax_node.ShortcutNode):
            last.end_padding = padding or syntax_node.PaddingNode("")
        elif isinstance(last, syntax_node.ValueNode):
            last.padding = padding
    elif _is_lattice_cell(node) and "lattice" in node.nodes:
        lattice = node.nodes["lattice"]
        while lattice.nodes and lattice.nodes[-1].format() != "]":
            del lattice.nodes[-1]
        if padding is not None:
            lattice.append(padding)
    elif isinstance(node, syntax_node.ListNode) and node.name == "universe phrase":
        node.nodes[-1].padding = padding
    elif _is_group_node(node):
        end = syntax_node.PaddingNode(")")
        if padding is not None:
            end += padding
        node.nodes["end_pad"] = end


def _is_lattice_cell(node) -> bool:
    return isinstance(node, syntax_node.SyntaxNode) and node.name == "lattice cell"


def _levels_of(group_node) -> list:
    """The ``("level", n)`` children of a ``<`` path group node, empty for a union."""
    return [
        node
        for key, node in group_node.nodes.items()
        if isinstance(key, tuple) and key[0] == "level"
    ]


def _make_group_node(items) -> syntax_node.SyntaxNode:
    """Build a parenthesized ``"tally group"`` node, as the parser does."""
    node = syntax_node.SyntaxNode(
        "tally group", {"start_pad": syntax_node.PaddingNode("(")}
    )
    for item in items:
        _append_tally_item(node, item)
    node.nodes["end_pad"] = syntax_node.PaddingNode(")")
    return node


def _parse_universe_spec(universe_node) -> int | None:
    for m in universe_node.nodes:
        if isinstance(m, syntax_node.ValueNode) and isinstance(m.value, (int, float)):
            return int(m.value)
    return None


def _parse_entries(node, *, is_grouped) -> FlatGroup:
    """Parse the entries of a union or a path level (``node``) into a :class:`FlatGroup`."""
    items = []
    lattice_indices = []
    number_nodes = []
    universe_spec = None

    def add_run(run):
        for value in run:
            if value.value is None:
                continue
            items.append(value.value)
            lattice_indices.append(None)
            number_nodes.append(value)

    for child in node.nodes.values():
        if _is_run(child):
            add_run(child)
        elif _is_lattice_cell(child):
            add_run(child.nodes[("run", 0)])
            # The index applies to the cell's last value, even a shortcut's.
            lattice_indices[-1] = LatticeIndex.parse_input_node(child.nodes["lattice"])
        elif (
            isinstance(child, syntax_node.ListNode) and child.name == "universe phrase"
        ):
            universe_spec = _parse_universe_spec(child)
        elif _is_group_node(child):
            if _levels_of(child):
                raise UnsupportedFeature(
                    f"A '<' path inside another group isn't supported: {child.format()}"
                )
            items.append(_parse_entries(child, is_grouped=True))
            lattice_indices.append(None)
            number_nodes.append(None)
    return FlatGroup(
        items,
        lattice_indices,
        is_grouped=is_grouped,
        universe_spec=universe_spec,
        node=node,
        number_nodes=number_nodes,
    )


def _parse_level(level_node) -> FlatGroup:
    """Parse one level of a ``<`` path.

    A level that is only a parenthesized union, e.g. the ``(1 2)`` in
    ``((1 2) < 5)``, is that union.
    """
    children = list(level_node.nodes.values())
    if (
        len(children) == 1
        and _is_group_node(children[0])
        and not _levels_of(children[0])
    ):
        return _parse_entries(children[0], is_grouped=True)
    return _parse_entries(level_node, is_grouped=False)


def _parse_tally_group_node(group_node) -> TallyGroup:
    nodes = list(group_node.nodes.values())
    for i, n in enumerate(nodes):
        # A "<" with no padding, e.g. in "(1<2)", stays unpadded when rewritten.
        if (
            isinstance(n, syntax_node.ValueNode)
            and n.padding is None
            and i + 1 < len(nodes)
            and not isinstance(nodes[i + 1], syntax_node.PaddingNode)
        ):
            n.never_pad = True
    levels = _levels_of(group_node)
    if not levels:
        return _parse_entries(group_node, is_grouped=True)
    return PathGroup([_parse_level(level) for level in levels], node=group_node)


def _parse_tally_numbers(tally_numbers_node) -> list[TallyGroup]:
    groups = []
    for node in tally_numbers_node.nodes.values():
        if _is_run(node):
            for value in node:
                if value.value is None:
                    continue
                wrapper = syntax_node.ListNode("flat group body")
                wrapper.append(value)
                groups.append(
                    FlatGroup(
                        [int(value.value)],
                        is_grouped=False,
                        node=wrapper,
                        number_nodes=[value],
                    )
                )
        elif _is_group_node(node):
            groups.append(_parse_tally_group_node(node))
    return groups
