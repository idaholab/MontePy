.. meta::
   :description lang=en:
        Working with MCNP tallies in MontePy: the Tally object model, building tallies, cloning, tally multipliers, and building reaction expressions with Python operators.

Tallies
=======

.. testsetup:: *

   import montepy
   problem = montepy.read_input("tests/inputs/test.imcnp")

This guide covers how to inspect and build tallies: what a tally
scores, which cells or surfaces it covers, and how its tally
multiplier modifies it. Every tally (``F``) input and tally multiplier
(``FM``) input in a problem is available as a real object through
``problem.tallies``, addressable by number like any other MontePy
collection.

The Tally Object Hierarchy
---------------------------

Every tally in a problem is stored in ``problem.tallies``, a
:class:`~montepy.Tallies` collection, and can be accessed by its number like
any other collection in MontePy.

.. testcode::

   tally = problem.tallies[4]
   print(tally)

.. testoutput::

   CellFluxTally: 4

MontePy picks the class for you based on the tally's type digit (e.g., the ``4`` in
``F4``).
:class:`~montepy.Tally` is the base class, and it has one subclass for every tally
type:

.. list-table::
   :header-rows: 1

   * - Quantity Tallied
     - Type Digit
     - MontePy Class
     - Shorthand Alias
   * - Surface current
     - F1
     - :class:`~montepy.SurfaceCurrentTally`
     - ``montepy.F1Tally``
   * - Average surface flux
     - F2
     - :class:`~montepy.SurfaceFluxTally`
     - ``montepy.F2Tally``
   * - Cell flux
     - F4
     - :class:`~montepy.CellFluxTally`
     - ``montepy.F4Tally``
   * - Point/ring detector flux
     - F5
     - :class:`~montepy.DetectorTally`
     - ``montepy.F5Tally``
   * - Energy deposition
     - F6
     - :class:`~montepy.EnergyDepositionTally`
     - ``montepy.F6Tally``
   * - Fission energy deposition
     - F7
     - :class:`~montepy.FissionEnergyDepositionTally`
     - ``montepy.F7Tally``
   * - Pulse height (energy deposition in a detector)
     - F8
     - :class:`~montepy.EnergyDetectorPulseTally`
     - ``montepy.F8Tally``

The Shorthand Alias is just another name for the same class, e.g.
``montepy.F4Tally`` is :class:`~montepy.CellFluxTally`.

Underneath these, there are two intermediate classes worth knowing about:
:class:`~montepy.SurfaceTally` for tallies that score on surfaces
(F1, F2), and :class:`~montepy.CellTally` for tallies that score in
cells (F4, F6, F7, F8).
You can check :attr:`~montepy.Tally.tally_type` to get the
:class:`~montepy.TallyType` for any tally.

.. doctest::

   >>> tally.tally_type
   <TallyType.CELL_FLUX: 4>

What a Tally Scores
--------------------

The list of cells or surfaces a tally scores over is exposed as
:attr:`~montepy.Tally.groups`.
Each entry is a :class:`~montepy.data_inputs.tally.FlatGroup`, which knows the numbers
it covers, and whether they're a single averaged bin or separate bins.

.. testcode::

   for group in tally.groups:
       print(group.old_numbers, group.is_grouped)

.. testoutput::

   [1] False
   [2] False
   [3] False

``is_grouped`` is ``False`` here because ``F4:n 1 2 3`` creates three separate bins.
If the numbers had been written in parentheses, like ``(1 2)``, they would be one
averaged bin instead, and ``is_grouped`` would be ``True``.

For cell tallies, :attr:`~montepy.CellTally.cells` gives you the
flattened, deduplicated set of every cell the tally touches, across all of its groups.
Surface tallies have the equivalent
:attr:`~montepy.SurfaceTally.surfaces`.

.. doctest::

   >>> print(tally.cells)
   Cells: [1, 2, 3]

Use ``cells``/``surfaces`` when you just want to know what's involved.
Use ``groups`` when the bin structure itself matters.

Checking whether a specific cell is scored by a tally works the way you'd expect:

.. doctest::

   >>> problem.cells[1] in tally
   True
   >>> problem.cells[99] in tally
   False

Building Tallies from Scratch
-------------------------------

You don't need MCNP syntax to build a tally.
Create the subclass you want, give it a number, and add cells or surfaces to it.

.. testcode::

   new_tally = montepy.F4Tally(number=104)
   new_tally.add_cell(problem.cells[1])
   new_tally.add_cell(problem.cells[2])
   problem.tallies.append(new_tally)

:func:`~montepy.CellTally.add_cell` adds a cell as its own separate
bin.
If you want a group of cells averaged into a single bin instead, use
:func:`~montepy.CellTally.add_group`:

.. testcode::

   new_tally.add_group([problem.cells[1], problem.cells[3]])

.. doctest::

   >>> for group in new_tally.groups:
   ...     print(group.old_numbers, group.is_grouped)
   [1] False
   [2] False
   [1, 3] True

:class:`~montepy.SurfaceTally` has the matching
:func:`~montepy.SurfaceTally.add_surface` and
:func:`~montepy.SurfaceTally.add_group`.

Scores and Filters
--------------------

Sometimes you don't need the raw group structure, you just want to know what physical
quantity a tally is measuring, and for which particles.
:attr:`~montepy.Tally.scores` and
:attr:`~montepy.Tally.filters` give you a shallow, read-only summary
of this, loosely inspired by how OpenMC describes tallies.

.. doctest::

   >>> tally.scores
   [<Score.FLUX: 2>]

Every tally type has a default score:
:class:`~montepy.Score` is an enum with entries like ``FLUX``,
``CURRENT``, and ``ENERGY_DEPOSITION``.
``filters`` returns a list of :class:`~montepy.data_inputs.tally.ParticleFilter` and
:class:`~montepy.data_inputs.tally.SpatialFilter` objects, whichever apply:

.. testcode::

   f1 = problem.tallies[1]
   for filt in f1.filters:
       print(type(filt).__name__)

.. testoutput::

   ParticleFilter
   SpatialFilter

.. note::

   These aren't a new way to write tallies to the input file, they're just a
   convenient way to read what's already there.
   ``scores`` and ``filters`` aren't settable.

Cloning Tallies
-----------------

Like most MontePy objects, tallies support
:func:`~montepy.Tally.clone`, which copies a tally and gives it a
new, unused number of the same tally type.

.. testcode::

   clone = tally.clone()

.. doctest::

   >>> clone.number
   14

Tallies also have something the other objects don't: :func:`~montepy.Tally.clone_as`.
This copies a tally's scoring geometry into a *different* tally type.
It's handy when you already have flux tallied over a set of cells and you also want
the heating in those same cells, without retyping the cell list:

.. testcode::

   heating = tally.clone_as(montepy.F6Tally)

.. doctest::

   >>> type(heating).__name__
   'EnergyDepositionTally'
   >>> print(heating.cells)
   Cells: [1, 2, 3]
   >>> heating.scores
   [<Score.ENERGY_DEPOSITION: 6>]

``clone_as`` only allows conversions within the same family: surface tallies (F1, F2)
convert to other surface tallies, and cell tallies (F4, F6, F7, F8) convert to other
cell tallies.
F5 point/ring detectors are their own family, since they don't have cells or surfaces
to carry over.
Trying to cross families raises a ``ValueError``.

Tally Multipliers
-------------------

A tally multiplier input multiplies a tally's flux or current by a cross section, turning a plain
flux tally into a reaction rate, a heating rate, or similar.
MontePy represents this as a :class:`~montepy.TallyMultiplier`,
linked to its tally through :attr:`~montepy.Tally.multiplier`.

.. testcode::

   fm = montepy.TallyMultiplier("fm4 (1.0 26 16 103)")
   problem.tallies.append(fm)

.. doctest::

   >>> tally.multiplier is fm
   True

An ``FMn`` input is linked to its tally purely by number, the same way an ``MTn``
thermal scattering input gets linked to material ``n``.
You can append the ``TallyMultiplier`` and its ``Tally`` to the problem in either
order, and MontePy will connect them once both are present.

The bulk of a tally multiplier input is its :attr:`~montepy.TallyMultiplier.bins`,
a list of :class:`~montepy.data_inputs.tally_multiplier.MultiplierBin`.
Each bin holds one or more
:class:`~montepy.MultiplierSet` or
:class:`~montepy.SpecialMultiplierSet` terms, and
optionally an :class:`~montepy.AttenuatorSet`.

.. testcode::

   term = fm.bins[0].terms[0]

.. doctest::

   >>> term.constant
   1.0
   >>> term.material
   26

Once a tally has a multiplier, its :attr:`~montepy.Tally.scores`
switches from the generic default to a list of
:class:`~montepy.data_inputs.tally_multiplier.MultiplierScore`, one for every output
bin the multiplier defines. This gives you the full recipe (constant, material,
reaction, and any attenuator) for every column of the tally's output.

.. doctest::

   >>> tally.scores
   [MultiplierScore(constant=1.0, material=26, reaction=ReactionExpression(Reaction(16), ReactionOperator.MULTIPLY, Reaction(103)), kind=None, attenuator=None)]

Building Reaction Expressions
------------------------------

A reaction list on a tally multiplier input, like ``16 103``, is really a small expression:
multiply reaction 16 by reaction 103.
Rather than making you build this out of strings, MontePy lets you write it as an
actual Python expression, using ``*`` for multiply, ``+`` for add, and ``-`` for
subtract.

.. doctest::

   >>> from montepy import Reaction
   >>> expr = Reaction(16) * Reaction(103)
   >>> expr == term.reactions[0]
   True

That's exactly the reaction expression already attached to ``tally`` above, built by
hand.
Python's own operator precedence already does the right thing for a longer list too:
``*`` binds tighter than ``+``/``-``, exactly like the MCNP manual says a reaction
list should work, so you don't need to write any parentheses to get the correct
grouping.

.. doctest::

   >>> bigger_expr = Reaction(16) * Reaction(103) + Reaction(104)
   >>> bigger_expr.left == expr
   True
   >>> bigger_expr.operator
   <ReactionOperator.ADD: ':'>

Common reaction numbers are also available by name, right on ``Reaction`` itself, so
you don't need to remember that capture is ``102``:

.. doctest::

   >>> Reaction.CAPTURE
   Reaction(102)
   >>> (Reaction.N_2N * Reaction.N_P) == expr
   True

You can go one step further and build a whole
:class:`~montepy.MultiplierSet` with ``&``, joining a
material number to a reaction expression:

.. doctest::

   >>> built = 26 & Reaction.N_2N * Reaction.N_P
   >>> built == term
   True

Scale the constant afterwards with ``*``:

.. doctest::

   >>> scaled = 1.5 * built
   >>> scaled.constant
   1.5

:class:`~montepy.AttenuatorSet` supports the same kind of
chaining with ``&``, for building up multiple attenuating layers:

.. doctest::

   >>> from montepy import AttenuatorSet, AttenuatorLayer
   >>> attenuator = AttenuatorSet(1.0, [AttenuatorLayer(26, 0.5)])
   >>> attenuator = attenuator & AttenuatorLayer(27, 0.3, is_atom_density=False)
   >>> len(attenuator.layers)
   2

.. note::

   Right now these operators are for building and comparing expressions, not for
   writing a new tally multiplier input from scratch.
   ``TallyMultiplier.bins`` is read-only, since it's parsed from the input file.

Universe and Lattice Paths
-----------------------------

This section is for the less common case: tallying a specific cell inside a specific
universe or lattice, using the ``<`` path syntax.
Most tallies don't need this.

A tally group written with ``<`` becomes a
:class:`~montepy.data_inputs.tally.PathGroup` instead of a ``FlatGroup``.
Each step in the chain is still a ``FlatGroup``, accessible through
:attr:`~montepy.data_inputs.tally.PathGroup.levels`, ordered from innermost to
outermost.

.. testcode::

   path_tally = montepy.F4Tally("f114:n (u=1 < 2[0 0 0] < 5)")
   for level in path_tally.groups[0].levels:
       print(level.old_numbers, level.universe_spec)

.. testoutput::

   [] 1
   [2] None
   [5] None

The first level has no cell number at all, just a universe designator
(``u=1``), meaning "any cell in universe 1".
The second level narrows that down to lattice element ``[0 0 0]`` of cell 2, and the
third level says that whole path has to live inside cell 5.

You can also build a path group from scratch with
:func:`~montepy.CellTally.add_path_group` and
:func:`~montepy.data_inputs.tally.PathGroup.inside`:

.. testcode::

   pg = new_tally.add_path_group(problem.cells[1])
   pg.inside(problem.cells[2])

.. doctest::

   >>> len(pg.levels)
   2

References
----------

* :manual63:`5.9`
* :manual63:`5.9.7`
