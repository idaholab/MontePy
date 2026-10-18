.. meta::
   :description lang=en:
        How MontePy's tally (F) and tally multiplier (FM) inputs are dispatched, parsed into a syntax tree, modeled, edited, and written back.

Tallies: :class:`~montepy.Tally`
================================

A tally (``F``) input is a :class:`~montepy.Tally`, defined in ``montepy/data_inputs/tally.py``.
Its scoring bins are :class:`~montepy.data_inputs.tally.TallyGroup` objects, defined in
``montepy/data_inputs/tally_group.py``, and its ``FM`` input is a
:class:`~montepy.TallyMultiplier`, defined in ``montepy/data_inputs/tally_multiplier.py``.
The grammars for both are in ``montepy/input_parser/tally_parser.py``.

Tally Types and Dispatch
------------------------

Each kind of tally is a :class:`~montepy.TallyType`, keyed by its mnemonic, the last digit of its
number (modulo 10), and its modifier (``+``, ``*``, or none).
``TallyType`` has a member for every valid combination, even when two use the same class.

Each concrete :class:`~montepy.Tally` subclass has:

* ``_TALLY_TYPE``: its default ``TallyType``;
* ``_OTHER_TALLY_TYPES``: any other ``TallyType`` it is used for. ``F6`` and ``*F6`` only differ in
  units (MeV/g or jerks/g), so both are an :class:`~montepy.EnergyDepositionTally`, and
  :attr:`~montepy.Tally.tally_units` switches between them.
  A different quantity, such as ``*F4``'s energy flux, is a different class instead;
* ``_DEFAULT_SCORES``: the :class:`~montepy.Score` it reports without a multiplier.

``_TALLY_TYPE_MAP`` maps every ``TallyType`` to its class, and
:meth:`~montepy.Tally.from_input` uses it (through ``Tally._dispatch_class``) to pick the
class from the classifier, after a light parse of it.
A tally's ``tally_type`` is set per instance from its classifier's modifier
(``Tally._parse_tally_type``).

Detector (``F5``) tallies aren't supported yet.
:func:`~montepy.data_inputs.data_parser.parse_data` reads them, and ``FM`` inputs for them, as plain
data inputs (see ``tally._is_detector_input``), and ``Tally.from_input`` raises
:class:`~montepy.exceptions.UnsupportedFeature` for them.

The Syntax Tree
---------------

The grammar gives a tally's bins their structure: Python code doesn't need to split or pair up
nodes after parsing.
The bins are a ``"tally bins"`` :class:`~montepy.input_parser.syntax_node.SyntaxNode`, whose
children are keyed by their kind and a counter, e.g. ``("run", 0)`` or ``("group", 1)``
(see ``tally_parser._next_key``):

* a ``"tally number run"`` :class:`~montepy.input_parser.syntax_node.ListNode` holds consecutive
  numbers and shortcuts (e.g. ``1 3i 5``), and nothing else, so it can be re-zipped with
  :meth:`~montepy.input_parser.syntax_node.ListNode.update_with_new_values` after a number
  changes or is removed;
* a ``"tally group"`` node is a parenthesized group. A union's entries are its children
  directly, while a ``<`` path's children are ``("level", n)`` ``"tally level"`` nodes,
  separated by ``("sep", n)`` ``<`` nodes;
* a ``"lattice cell"`` node holds the ``("run", 0)`` of a cell (or shortcut) and the ``"lattice"``
  phrase that follows it, e.g. ``2[0 0 0]``;
* a ``u=`` universe designator is a ``"universe phrase"``.

``tally_parser._append_tally_item`` adds an item to a node, collecting numbers into runs.
For example:

.. doctest::

    >>> from montepy.input_parser.tally_parser import TallyParser
    >>> from montepy.input_parser.tokens import TallyLexer
    >>> tree = TallyParser().parse(TallyLexer().tokenize("f4:n 1 3i 5 (6 < 7[0 0 0])"))
    >>> bins = tree["data"]["tally"]
    >>> list(bins.nodes)
    [('run', 0), ('group', 0)]
    >>> list(bins[("group", 0)].nodes)
    ['start_pad', ('level', 0), ('sep', 0), ('level', 1), 'end_pad']
    >>> list(bins[("group", 0)][("level", 1)].nodes)
    [('cell', 0)]

The ``FM`` grammar, :class:`~montepy.input_parser.tally_parser.TallyMultiplierParser`,
overrides all of these rules: its bins have no paths or lattices, and their numbers are ``float``.

The Object Model
----------------

``tally_group._parse_tally_numbers`` maps the bins to groups:

* :class:`~montepy.data_inputs.tally.FlatGroup` is a union (``is_grouped``) or a set of separate
  bins, e.g. a single top-level number, or one level of a path. Its members are numbers,
  :class:`~montepy.Cell`/:class:`~montepy.Surface` objects once linked, or nested union
  ``FlatGroup`` objects, e.g. the ``(2 3)`` in ``(1 (2 3) < 5)``.
  ``_items``, ``_old_numbers`` (``None`` for a nested union), ``_lattice_indices``, and
  ``_number_nodes`` (the :class:`~montepy.input_parser.syntax_node.ValueNode` of each number)
  are parallel lists, and ``_leaves`` walks every scored entry, including nested ones.
  A ``FlatGroup`` keeps the node it was parsed from, and edits it in place.
* :class:`~montepy.data_inputs.tally.PathGroup` is a ``<`` path, whose
  :attr:`~montepy.data_inputs.tally.PathGroup.levels` are ``FlatGroup`` objects, innermost first.
  Only the innermost level is scored, so only it is ``in`` the tally, linked to the problem, or
  in :attr:`~montepy.CellTally.cells`; the outer levels only say which instance of it is meant.
* :class:`~montepy.data_inputs.tally.LatticeIndex` holds a lattice phrase's elements.

:attr:`~montepy.CellTally.cells` and :attr:`~montepy.SurfaceTally.surfaces` are kept in step with
the groups: adding a group adds its scored objects, and removing one only checks its own entries
against what the other groups still score (``Tally._prune_unreferenced``).

Writing Back
------------

``Tally._update_values`` brings the tree up to date:

#. Each group's ``node`` is updated with its current numbers, e.g. after a cell is renumbered.
   A group built from scratch builds its node the first time.
#. If groups were added or removed, the bins are rebuilt (``Tally._rebuild_bins``), putting each
   remaining top-level number back into the run it was parsed in.
#. Each run with a changed value is re-zipped, so a shortcut stays a shortcut.
#. The ``T`` total flag is written only if it changed, keeping its original case, by
   ``tally_parser._set_end_flag``, which :class:`~montepy.TallyMultiplier` also uses for its
   ``T``/``C`` flag.

Editing a parsed group edits its tree directly. ``FlatGroup._remove_item`` removes a number's
node, re-zipping its shortcut and dropping a lattice index that followed it, and the entry before
a removed last entry takes over its trailing padding.
``PathGroup.inside`` adds a new outermost level to a parsed path's tree.

Linking and Multipliers
-----------------------

A tally's groups are linked to the problem's cells or surfaces by number in ``link_to_problem``
(``TallyGroup.update_pointers``).
:class:`~montepy.Cell` and :class:`~montepy.Surface` list ``("tallies", "groups", True)`` in their
``_parent_collections``, so renumbering one fully parses any tally that may refer to it first.

An ``FM`` input is linked to its tally by number in :class:`~montepy.tallies.Tallies`, in
whichever order the two are added: one added before its tally waits in ``Tallies._fm_queue``.
Renumbering a tally renumbers its multiplier, and deleting it deletes its multiplier.
