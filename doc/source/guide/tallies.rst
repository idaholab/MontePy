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
     - ``F1``
     - :class:`~montepy.SurfaceCurrentTally`
     - ``montepy.F1Tally``
   * - Surface energy current
     - ``*F1``
     - :class:`~montepy.SurfaceEnergyCurrentTally`
     -
   * - Average surface flux
     - ``F2``
     - :class:`~montepy.SurfaceFluxTally`
     - ``montepy.F2Tally``
   * - Average surface energy flux
     - ``*F2``
     - :class:`~montepy.SurfaceEnergyFluxTally`
     -
   * - Cell flux
     - ``F4``
     - :class:`~montepy.CellFluxTally`
     - ``montepy.F4Tally``
   * - Cell energy flux
     - ``*F4``
     - :class:`~montepy.CellEnergyFluxTally`
     -
   * - Energy deposition
     - ``F6``, ``*F6``
     - :class:`~montepy.EnergyDepositionTally`
     - ``montepy.F6Tally``
   * - Collision heating
     - ``+F6``
     - :class:`~montepy.CollisionHeatingTally`
     - ``montepy.PlusF6Tally``
   * - Fission energy deposition
     - ``F7``, ``*F7``
     - :class:`~montepy.FissionEnergyDepositionTally`
     - ``montepy.F7Tally``
   * - Pulse height in a detector
     - ``F8``
     - :class:`~montepy.EnergyDetectorPulseTally`
     - ``montepy.F8Tally``
   * - Energy deposition in a detector
     - ``*F8``
     - :class:`~montepy.DetectorEnergyDepositionTally`
     -
   * - Charge deposition
     - ``+F8``
     - :class:`~montepy.ChargeDepositionTally`
     - ``montepy.PlusF8Tally``

The Shorthand Alias is just another name for the same class, e.g.
``montepy.F4Tally`` is :class:`~montepy.CellFluxTally`.

Detector (``F5``) tallies are not supported yet.
They are read as plain data inputs, so they are kept and written back out unchanged,
but they are not in :attr:`~montepy.MCNP_Problem.tallies`.

The leading ``+`` on ``+F6``/``+F8`` is a separate MCNP tally variant:
``+F6`` (collision heating) and ``+F8`` (charge
deposition) score a different physical quantity than plain ``F6``/``F8``, so
MontePy treats them as distinct classes even though they share the same type
digit.
The same goes for a leading ``*`` on ``*F1``, ``*F2``, ``*F4``, and ``*F8``, which
tally energy instead of particles (or, for ``*F8``, energy deposition instead of
pulses).

On ``F6`` and ``F7``, though, ``*`` only changes the units, from MeV/g to jerks/g,
so ``*F6`` and ``*F7`` are the same classes as ``F6`` and ``F7``.
Every tally has :attr:`~montepy.Tally.tally_units`, and on these two you can set
it to switch between them:

.. doctest::

   >>> deposition = montepy.Tally.from_input("F16:n 1")
   >>> deposition.tally_units
   <TallyUnits.MEV_PER_G: 'MeV/g'>
   >>> deposition.tally_units = montepy.TallyUnits.JERKS_PER_G
   >>> deposition.mcnp_str()
   '*F16:n 1'

Underneath these, there are two intermediate classes worth knowing about:
:class:`~montepy.SurfaceTally` for tallies that score on surfaces
(i.e., ``F1`` and ``F2``), and :class:`~montepy.CellTally` for tallies that score in
cells (i.e., ``F4``, ``F6``, ``F7``, and ``F8``).
You can check :attr:`~montepy.Tally.tally_type` to get the
:class:`~montepy.TallyType` for any tally.

.. doctest::

   >>> tally.tally_type
   <TallyType.CELL_FLUX: 4>

Geometry Filters
------------------

The cells or surfaces a tally scores over are its geometry filter, exposed as
:attr:`~montepy.Tally.groups`, a list of
:class:`~montepy.data_inputs.tally.TallyGroup` objects.

This section covers flat cell/surface lists, where every entry is a
:class:`~montepy.data_inputs.tally.FlatGroup`.
A ``FlatGroup`` knows the cells or surfaces it covers, and whether they form a single
averaged bin or separate bins.
Repeated structures and lattices use the ``<``/``[...]``/``U=`` syntax instead, which
produces :class:`~montepy.data_inputs.tally.PathGroup` entries; see
`Universe and Lattice Paths`_ below.

A group gives you the objects it covers through three attributes:

* :attr:`~montepy.data_inputs.tally.FlatGroup.cells` is the list of
  :class:`~montepy.Cell` objects, or ``None`` if the group isn't made of cells.
* :attr:`~montepy.data_inputs.tally.FlatGroup.surfaces` is the list of
  :class:`~montepy.Surface` objects, or ``None`` if the group isn't made of surfaces.
* :attr:`~montepy.data_inputs.tally.FlatGroup.cells_or_surfaces` is whichever of the
  two applies.

Prefer ``cells`` and ``surfaces``: they say what you are getting, and a ``None`` tells
you that you asked a surface tally for cells.
``cells_or_surfaces`` is for code that handles both kinds of tally.
All three need the tally to be part of a problem, so that its numbers can be
resolved to objects; a tally that was only just parsed from a string, or
built by hand, has to be appended to ``problem.tallies`` first.

In the simple, "flat" case, a tally just lists cells or surfaces one after another,
and MCNP creates a separate bin for each one:

.. testcode::

   # f4:n 1 2 3
   tally = problem.tallies[4]
   for group in tally.groups:
       print(*group.cells, group.is_grouped)

.. testoutput::

   Cell: 1 False
   Cell: 2 False
   Cell: 3 False

``is_grouped`` is ``False`` for every group here, since ``F4:n 1 2 3`` has no
parentheses: each of cells 1, 2, and 3 gets its own separate bin.
This is a cell tally, so ``surfaces`` is ``None`` for these groups.
For a surface tally it is the other way around:

.. testcode::

   # f2:p 1005
   surface_tally = problem.tallies[2]
   group = surface_tally.groups[0]
   print(*group.surfaces)
   print(group.cells)

.. testoutput::

   RightCircularCylinder: 1005
   None


Wrapping cells or surfaces in parentheses instead unions them into a single bin,
averaged, or summed, depending on the tally score, rather than reported separately.
A tally can mix flat entries and multiple parenthesized groups on the same input, and
each group becomes its own entry in ``groups``:

.. testcode::

   grouped = montepy.CellFluxTally("f44:n (1 2) (3)")
   problem.tallies.append(grouped)
   for group in grouped.groups:
       print(*group.cells, group.is_grouped)

.. testoutput::

   Cell: 1 Cell: 2 True
   Cell: 3 True

Notice that the second group here still has ``is_grouped`` set to ``True``, even
though it only covers a single cell: what matters is whether the parentheses were
there, not how many cells are inside them. Without the parentheses, ``f44:n 1 2 3``
would instead produce three separate, ungrouped bins, exactly like the cell flux
tally example above.
To build flat and grouped bins like these from scratch instead of reading them from
an existing tally, see `Building Tallies from Scratch`_ below.

Parentheses can also nest, e.g. ``(1 (2 3))``.
``cells`` covers every cell in a group, including the nested ones, while
:attr:`~montepy.data_inputs.tally.FlatGroup.members` keeps the structure, with each
nested union as its own :class:`~montepy.data_inputs.tally.FlatGroup`:

.. doctest::

   >>> nested = montepy.CellFluxTally("f54:n (1 (2 3))")
   >>> problem.tallies.append(nested)
   >>> print(*nested.groups[0].cells)
   Cell: 1 Cell: 2 Cell: 3
   >>> nested.groups[0].members[1]
   FlatGroup([2, 3], grouped=True)

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

A tally can also end with a trailing ``T``, for "total": an extra bin that's the
union of every other bin on the input, rather than a scoring region of its own.
Because it isn't really its own region, MontePy doesn't represent it as another
entry in ``groups``.
Instead it's a separate flag, :attr:`~montepy.Tally.include_total`:

.. testcode::

   totaled = montepy.CellFluxTally("f64:n (1 2) (3) T")
   problem.tallies.append(totaled)
   for group in totaled.groups:
       print(*group.cells, group.is_grouped)
   print(totaled.include_total)

.. testoutput::

   Cell: 1 Cell: 2 True
   Cell: 3 True
   True

Notice that ``groups`` only has the two real bins; the ``T`` never shows up as a
third entry there, no matter how many bins came before it.
Unlike ``scores`` and ``filters``, ``include_total`` is settable, so you can turn
total-bin reporting on (or off) for any tally, including one you build from scratch
with :func:`~montepy.CellTally.add_cell`/:func:`~montepy.CellTally.add_group` (see
`Building Tallies from Scratch`_ below):

.. doctest::

   >>> totaled.include_total = False
   >>> totaled.include_total
   False
   >>> "T" in totaled.mcnp_str()
   False

Building Tallies from Scratch
-------------------------------

It's also possible to build a tally from scratch.
Instantiate the concrete subclass for the quantity you want to score (e.g.
:class:`~montepy.CellFluxTally` for flux), give it a number, and add cells or
surfaces to it.

.. testcode::

   new_tally = montepy.CellFluxTally(number=104)
   new_tally.add_cell(problem.cells[1], problem.cells[2])
   problem.tallies.append(new_tally)

:func:`~montepy.CellTally.add_cell` adds each cell as its own separate
bin.
If you want a group of cells averaged into a single bin instead, use
:func:`~montepy.CellTally.add_group`:

.. testcode::

   new_tally.add_group(problem.cells[1], problem.cells[3])

.. doctest::

   >>> for group in new_tally.groups:
   ...     print(*group.cells, group.is_grouped)
   Cell: 1 False
   Cell: 2 False
   Cell: 1 Cell: 3 True

A list (or tuple) given to ``add_group`` is a nested union:

.. doctest::

   >>> nested_tally = montepy.CellFluxTally(number=114)
   >>> nested_tally.add_group(problem.cells[1], (problem.cells[2], problem.cells[3]))
   >>> print(*nested_tally.groups[0].cells)
   Cell: 1 Cell: 2 Cell: 3
   >>> nested_tally.groups[0].members[1]
   FlatGroup([2, 3], grouped=True)

:class:`~montepy.SurfaceTally` has the matching
:func:`~montepy.SurfaceTally.add_surface` and
:func:`~montepy.SurfaceTally.add_group`.

Each of these has a matching removal method.
:func:`~montepy.CellTally.remove_group` removes any group outright, whether it came
from ``add_cell``, ``add_group``, or ``add_path_group``.
:func:`~montepy.CellTally.remove_cell`/:func:`~montepy.SurfaceTally.remove_surface`
remove a cell or surface from everywhere the tally scores it, so that afterwards it is
no longer ``in`` the tally:

.. doctest::

   >>> new_tally.remove_cell(problem.cells[2])
   >>> for group in new_tally.groups:
   ...     print(*group.cells, group.is_grouped)
   Cell: 1 False
   Cell: 1 Cell: 3 True
   >>> problem.cells[2] in new_tally.cells
   False

That includes unions, which keep their remaining members (even just one), and the
innermost level of ``<`` paths. A bin, union, or path left with nothing to score is
removed:

.. doctest::

   >>> new_tally.remove_cell(problem.cells[1])
   >>> for group in new_tally.groups:
   ...     print(*group.cells, group.is_grouped)
   Cell: 3 True

A cell or surface that is only a containment (outer) level of a path isn't scored,
so it isn't ``in`` the tally, and removing it raises
:class:`~montepy.exceptions.OnlyInPathError`.
If it is scored somewhere else too, it is removed from there, with a
:class:`~montepy.exceptions.PathContainmentWarning` that the path still uses it.

Scores and Filters
--------------------

.. note::

   "Score" and "filter" aren't MCNP terms.
   MontePy borrows this vocabulary from
   `OpenMC <https://docs.openmc.org/en/stable/>`_, since it's more general than
   anything MCNP itself uses, and describes the same underlying concepts more intuitively.
   See `OpenMC's tallies user guide
   <https://docs.openmc.org/en/stable/usersguide/tallies.html>`_ for more on this
   terminology.

Sometimes you don't need the raw group structure, you just want to know what physical
quantity a tally is measuring, and for which particles.
:attr:`~montepy.Tally.scores` and
:attr:`~montepy.Tally.filters` give you a shallow, read-only summary
of this.

.. doctest::

   >>> tally.scores
   [<Score.FLUX: 2>]

Every tally type has a default score:
:class:`~montepy.Score` is an enum with entries like ``FLUX``,
``CURRENT``, and ``ENERGY_DEPOSITION``.
This default is overridden if the tally has a tally multiplier attached; see
`Tally Multipliers`_ below.
``filters`` returns a list of :class:`~montepy.data_inputs.tally.ParticleFilter` and
:class:`~montepy.data_inputs.tally.SpatialFilter` objects, whichever apply:

.. testcode::

   f2 = problem.tallies[2]
   for filt in f2.filters:
       print(filt)

.. testoutput::

   ParticleFilter(':p')
   SpatialFilter([FlatGroup([1005], grouped=False)])

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

   heating = tally.clone_as(montepy.EnergyDepositionTally)

.. doctest::

   >>> print(heating)
   EnergyDepositionTally: 16
   >>> print(heating.cells)
   Cells: [1, 2, 3]
   >>> heating.scores
   [<Score.ENERGY_DEPOSITION: 6>]

``clone_as`` only allows conversions within the same family: surface tallies
(i.e., ``F1`` and ``F2``) convert to other surface tallies, and cell tallies
(i.e., ``F4``, ``F6``, ``F7``, and ``F8``) convert to other cell tallies.
Trying to cross families raises a ``ValueError``.

The ``+F6``/``+F8`` modifier variants (see the table above) are part of the same
family as their plain counterparts, so ``clone_as`` converts freely between them
too:

.. testcode::

   collision_heating = heating.clone_as(montepy.CollisionHeatingTally)

.. doctest::

   >>> print(collision_heating)
   CollisionHeatingTally: 26
   >>> collision_heating.scores
   [<Score.COLLISION_HEATING: 9>]
   >>> "+" in collision_heating.mcnp_str()
   True

Tally Multipliers
-------------------

A tally multiplier input multiplies a tally's flux or current by a cross section, turning a plain
flux tally into a reaction rate, a heating rate, or similar.
MontePy represents this as a :class:`~montepy.TallyMultiplier`,
linked to its tally through :attr:`~montepy.Tally.multiplier`.

The examples in this section follow one story.
Tally 4 is a neutron flux tally.
Suppose we want to know how much hydrogen and helium gas the iron (material 2) in those
cells produces.
That's the rate of the :math:`(n,p)` reaction (MT 103) plus the :math:`(n,\alpha)` reaction
(MT 107), which is what ``FM4 (1.0 2 103:107)`` asks MCNP for.

.. testcode::

   fm = montepy.TallyMultiplier("fm4 (1.0 2 103:107)")
   problem.tallies.append(fm)

.. doctest::

   >>> tally.multiplier is fm
   True

An ``FMn`` input is linked to its tally purely by number, the same way an ``MTn``
thermal scattering input gets linked to material ``n``.
You can append the ``TallyMultiplier`` and its ``Tally`` to the problem in either
order, and MontePy will connect them once both are present.
Because that link is the whole point of an ``FMn`` card, MontePy keeps it
consistent for you: deleting a tally that has a linked multiplier removes the
now-orphaned ``FM`` card from the problem too (with a warning), and renumbering a
tally renumbers its linked multiplier to match.
Cloning a tally with :func:`~montepy.Tally.clone` clones its multiplier too,
unless you pass ``clone_multiplier=False``.
:func:`~montepy.Tally.clone_as` does the opposite: since a multiplier written for one
tally type often doesn't fit another, it only clones it with ``clone_multiplier=True``.

Since a ``TallyMultiplier``'s number always tracks its parent tally's rather than
being independently assignable, it has its own
:func:`~montepy.TallyMultiplier.clone`, separate from
:func:`~montepy.Tally.clone`: pass the tally to attach the clone to (it takes that
tally's number), or omit it for a detached, unregistered copy.
Here we reuse the gas production recipe on the cloned tally 14:

.. testcode::

   fm_clone = fm.clone(problem.tallies[14])

.. doctest::

   >>> fm_clone.number
   14
   >>> problem.tallies[14].multiplier is fm_clone
   True

The bulk of a tally multiplier input is its :attr:`~montepy.TallyMultiplier.bins`,
a list of :class:`~montepy.data_inputs.tally_multiplier.MultiplierBin`.
Each bin holds one or more
:class:`~montepy.MultiplierSet` or
:class:`~montepy.SpecialMultiplierSet` terms, and
optionally an :class:`~montepy.AttenuatorSet`.
Our gas production multiplier has one bin with one term: the iron term.

.. testcode::

   term = fm.bins[0].terms[0]

.. doctest::

   >>> term.constant
   1.0
   >>> term.material
   2

Once a tally has a multiplier, its :attr:`~montepy.Tally.scores`
switches from the generic default to a list of
:class:`~montepy.data_inputs.tally_multiplier.MultiplierScore`, one for every output
bin the multiplier defines. This gives you the full recipe (constant, material,
reaction, and any attenuator) for every column of the tally's output.

.. doctest::

   >>> tally.scores
   [MultiplierScore(constant=1.0, material=2, reaction=ReactionExpression(Reaction(103), ReactionOperator.ADD, Reaction(107)), kind=None, attenuator=None)]

Building Reaction Expressions
------------------------------

Continuing the gas production example, the reaction list ``103:107`` in
``FM4 (1.0 2 103:107)`` is really a small expression: add reaction 103 to reaction 107.
Rather than making you build this out of strings, MontePy lets you write it as an
actual Python expression, using ``*`` for multiply, ``+`` for add, and ``-`` for
subtract.

.. note::

   Raw MT numbers like ``103`` are hard to read and easy to mistype.
   :class:`~montepy.Reaction` has named constants for the common ones, e.g.
   ``Reaction.N_P`` for MT 103; use those instead of ``Reaction(103)`` whenever a name
   is available.
   Raw numbers are still there for the reactions that don't have one.

.. doctest::

   >>> from montepy import Reaction
   >>> expr = Reaction.N_P + Reaction.N_ALPHA
   >>> expr == term.reactions[0]
   True
   >>> fm.mcnp_str()
   'fm4 (1.0 2 103:107)'

That's exactly the reaction expression already attached to ``tally`` above, built by
hand, matching the actual MCNP text of ``fm``.
Longer lists work the same way. If we also want deuteron production (MT 104),
we can keep adding to the expression:

.. doctest::

   >>> bigger_expr = expr + Reaction.N_D
   >>> bigger_expr.left == expr
   True
   >>> bigger_expr.operator
   <ReactionOperator.ADD: ':'>

Python's own operator precedence also does the right thing when you mix operators,
exactly like the MCNP manual says a reaction list should work, so you don't need to
write unnecessary parentheses to get the correct grouping.

You can go one step further and build a whole
:class:`~montepy.MultiplierSet` with ``&``, joining the iron
:class:`~montepy.Material` from the problem to the reaction expression:

.. doctest::

   >>> iron = problem.materials[2]
   >>> built = iron & expr
   >>> built == term
   True
   >>> fm.mcnp_str()
   'fm4 (1.0 2 103:107)'

You can scale the constant afterward with ``*``, for example to convert the
result to a different unit:

.. doctest::

   >>> scaled = 1.5 * built
   >>> scaled.constant
   1.5

:class:`~montepy.AttenuatorSet` supports the same kind of
chaining with ``&``, for building up multiple attenuating layers.
Say we want to know the gas production behind a shield of iron (material 2) and then material 3,
rather than in the bare cells. That adds an attenuator after the term:

.. doctest::

   >>> from montepy import AttenuatorSet, AttenuatorLayer
   >>> attenuator = AttenuatorSet(1.0, [AttenuatorLayer(2, 0.5)])
   >>> attenuator = attenuator & AttenuatorLayer(3, 0.3, is_atom_density=False)
   >>> len(attenuator.layers)
   2
   >>> fm2 = montepy.TallyMultiplier("fm104:n (1.0 -1 2 0.5 3 -0.3)")
   >>> attenuator == fm2.bins[0].attenuator
   True
   >>> fm2.mcnp_str()
   'fm104:n (1.0 -1 2 0.5 3 -0.3)'

These operators build and compare :class:`~montepy.MultiplierSet`/
:class:`~montepy.data_inputs.tally_multiplier.ReactionExpression` values, but a
:class:`~montepy.TallyMultiplier` needs one more step to actually add them to a card:
wrap each term (and optional attenuator) in a
:class:`~montepy.data_inputs.tally_multiplier.MultiplierBin`, then use
:func:`~montepy.TallyMultiplier.add_bin` (and :func:`~montepy.TallyMultiplier.remove_bin`
to take one back out). ``bins`` itself stays a read-only view, the same way ``groups``
does for a :class:`~montepy.Tally`.
To finish the story, here is the gas production multiplier for tally 4 built from scratch:

.. testcode::

   from montepy.data_inputs.tally_multiplier import MultiplierBin

   fm3 = montepy.TallyMultiplier(number=4)
   fm3.add_bin(MultiplierBin([built]))

.. doctest::

   >>> fm3.bins[0].terms[0] == built
   True

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

In the simplest case, a chain is just cell numbers separated by ``<``, read
innermost-to-outermost, e.g. "cell 2, inside cell 5":

.. testcode::

   simple_path = montepy.CellFluxTally("f74:n (2 < 5)")
   problem.tallies.append(simple_path)
   for level in simple_path.groups[0].levels:
       print(*level.cells)

.. testoutput::

   Cell: 2
   Cell: 5

A ``PathGroup`` itself has
:attr:`~montepy.data_inputs.tally.PathGroup.cells_or_surfaces`, which flattens every
level together, and
:attr:`~montepy.data_inputs.tally.PathGroup.inner_cells_or_surfaces`, which has just
the innermost (scored) level.

A level can narrow further with a lattice-element index in brackets
(``[i j k]``), and a universe designator (``u=n``) can stand in for an entire level,
meaning "any cell in universe n":

.. testcode::

   path_tally = montepy.CellFluxTally("f84:n (u=350 < 2[0 0 0] < 5)")
   problem.tallies.append(path_tally)
   for level in path_tally.groups[0].levels:
       print(*(level.cells or []), level.universe_spec)

.. testoutput::

   Universe: 350
   Cell: 2 None
   Cell: 5 None

The first level has no cells at all (``cells`` is ``None``), just a universe designator
(``u=350``), meaning "any cell in universe 350".
The second level narrows that down to lattice element ``[0 0 0]`` of cell 2, and the
third level says that whole path has to live inside cell 5.
That lattice element is available directly through
:attr:`~montepy.data_inputs.tally.FlatGroup.lattice_indices`, parallel to
``cells``, as a list of :class:`~montepy.data_inputs.tally.LatticeIndex`:

.. doctest::

   >>> path_tally.groups[0].levels[1].lattice_indices[0].elements
   ((0, 0, 0),)

You can also build a path group from scratch with
:func:`~montepy.CellTally.add_path_group` and
:func:`~montepy.data_inputs.tally.PathGroup.inside`:

.. testcode::

   scratch_tally = montepy.CellFluxTally(number=304)
   pg = scratch_tally.add_path_group(problem.cells[1])
   pg.inside(problem.cells[2])

.. doctest::

   >>> for level in pg.levels:
   ...     print(*level.cells)
   Cell: 1
   Cell: 2

``inside`` works on a path read from an input too, adding a new outermost level:

.. doctest::

   >>> path_tally.groups[0].inside(problem.cells[3])
   PathGroup(...)
   >>> path_tally.mcnp_str()
   'f84:n (u=350 < 2[0 0 0] < 5 < 3)'

References
----------

Tallies (``F``):

.. mcnp-manuals::

   :632: 5.9.1
   :631: 5.9.1
   :63: 5.9.1
   :62: 235
   :4c: 329
   :4b: 291
   :3a: 228
   :2: 152
   :1: 29

Tally multipliers (``FM``):

.. mcnp-manuals::

   :632: 5.9.7
   :631: 5.9.7
   :63: 5.9.7
   :62: 264
   :4c: 342
   :4b: 303
   :3a: 236
   :2: 156
