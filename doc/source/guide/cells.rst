.. meta::
   :description lang=en:
        Working with MCNP cells in MontePy: importances, density, geometry (CSG), and cloning.

Cells
=====

.. testsetup:: *

   import montepy
   problem = montepy.read_input("tests/inputs/test.imcnp")
   cell = problem.cells[1]

.. _CellImportance:

Setting Cell Importances
------------------------

All cells have an importance that can be modified.
This is generally accessed through ``cell.importance`` (:attr:`~montepy.Cell.importance`).
You can access the importance for a specific particle type by its name in lower case.
For example: ``cell.importance.neutron`` or ``cell.importance.photon``.
For a complete list see :class:`~montepy.particle.Particle`.

You can also quickly get the information by passing an instance of :class:`~montepy.particle.Particle` as a key to importance.
For example:

.. doctest::

    >>> for particle in sorted(problem.mode):
    ...     print(particle, cell.importance[particle])
    neutron 1.0
    photon 1.0
    >>> print(cell.importance[montepy.Particle.NEUTRON])
    1.0

There's also a lot of convenient ways to do bulk modifications.
There is the :func:`~montepy.data_inputs.importance.Importance.all` property that lets you set the importance for all particles in the problem at once.
For example:

.. doctest::
   :skipif: True

    >>> problem.set_mode("n p e")
    >>> cell.importance.all = 2.0
    >>> for particle in sorted(problem.mode):
    ...     print(particle, cell.importance[particle])
    electron 2.0
    neutron 2.0
    photon 2.0

This will set the importances for the neutron and photon.

You can also delete an importance to reset it to the default value (1.0).
For example: ``del cell.importance.neutron``.

There is also the method: :func:`~montepy.Cells.set_equal_importance`.
This method sets all of the cells for all particles in the problem to the same importance.
You can optionally pass a list of cells to this function.
These cells are the "vacuum boundary" or "graveyard" cells.
That is to say, a particle that crosses into one of these cells is killed.
Their importances will all be set to 0.



Setting How Cell Data Gets Displayed in the Input File
------------------------------------------------------

Much of the cell data can show up in the cell block or the data block, like the importance input.
These are referred to MontePy as "cell modifiers".
You can change how these cell modifiers are printed with :attr:`~montepy.MCNP_Problem.print_in_data_block`.
This acts like a dictionary where the key is the MCNP input name.
So to make cell importance data show up in the cell block just run:
``problem.print_in_data_block["imp"] = False``.

.. note::

   The default for :attr:`~montepy.MCNP_Problem.print_in_data_block` is ``False``,
   that is to print the data in the cell block if this was not set in the input file or by the user.

Density
-------
This gets a bit more complicated.
MCNP supports both atom density, and mass density.
So if there were a property ``cell.density`` its result could be ambiguous,
because it could be in g/cm3 or atom/b-cm.
No; MontePy does not support negative density; it doesn't exist!
For this reason ``cell.density`` is deprecated.
Instead there is ``cell.atom_density`` and ``cell.mass_density``.

``cell.atom_density`` is in units of atomcs/b-cm,
and ``cell.mass_density`` is in units of g/cm3.
Both will never return a valid number simultaneously.
If the cell density is set to a mass density ``cell.atom_density`` will return ``None``.
Setting the value for one of these densities will change the density mode.
MontePy does not convert mass density to atom density and vice versa.

.. doctest::

    >>> problem = montepy.read_input("tests/inputs/test.imcnp")
    >>> cell = problem.cells[3]
    >>> cell.mass_density
    1.0
    >>> cell.atom_density
    Traceback (most recent call last):
        ...
    AttributeError: Cell 3 is in mass density.. Did you mean: 'mass_density'?
    >>> cell.atom_density = 0.5
    >>> cell.mass_density
    Traceback (most recent call last):
        ...
    AttributeError: Cell 3 is in atom density.. Did you mean: 'atom_density'?

Geometry
--------

MontePy now supports understanding constructive solids geometry (CSG) set logic.
This implementation was inspired by `OpenMC <https://docs.openmc.org/en/stable/>`_, and `their documentation <https://docs.openmc.org/en/stable/usersguide/geometry.html>`_ may be helpful.

Terminology
^^^^^^^^^^^

In MCNP the geometry of a cell can by defined by either a surface, or another cell (through complements).
Therefore, it's not very useful to talk about geometry in terms of "surfaces" because it's not accurate and could lead to confusion.
MontePy focuses mostly on the mathematical concept of `half-spaces <https://en.wikipedia.org/wiki/Half-space_(geometry)>`_.
These are represented as :class:`~montepy.HalfSpace` instances.
The use of this term is a bit loose and is not meant to be mathematical rigorous.
The general concept though is that the space (R\ :sup:`3`) can always be split into two regions, or half-spaces.
For MontePy this division is done by a divider ( a surface, a cell, or some CSG combination of thoses).
For planes this can be seen really easily; you have a top, and bottom (or a left and a right, etc.).
For cells this could be a bit less intuitive, but it is still a divider.
The two half-spaces can be viewed as in or out of the cell.

So how are these half-spaces identified?
In MCNP this generally done by marking the half-space as the positive or negative one.
In MontePy these are changed to boolean values for the :attr:`~montepy.UnitHalfSpace.side` parameter simplicity with True being the positive side.
For cell complements the side is implicitly handled by the CSG logic, and can always be thought of as the "outside"
(though ``side`` will return True).

Creating a Half-Space
^^^^^^^^^^^^^^^^^^^^^

To make a geometry you can't just start with a divider (e.g., a surface), and just expect the geometry to be unambiguous.
This is because you need to choose a half-space from the divider.
This is done very simply and pythonic.
For a :class:`~montepy.Surface` you just need to mark the surface as positive (``+``) or negative (``-``) (using the unary operators).
This actually creates a new object so don't worry about modifying the surface.

.. doctest::

    >>> bottom_plane = montepy.surfaces.surface.Surface()
    >>> bottom_plane.number = 1
    >>> top_plane = montepy.surfaces.surface.Surface()
    >>> top_plane.number = 2
    >>> type(+bottom_plane)
    <class 'montepy.surfaces.half_space.UnitHalfSpace'>
    >>> type(-bottom_plane)
    <class 'montepy.surfaces.half_space.UnitHalfSpace'>

For cells the plus/minus operator doesn't make sense.
Instead you use the binary not operator (``~``).

.. doctest::

    >>> capsule_cell = montepy.Cell()
    >>> capsule_cell.number = 1
    >>> type(~capsule_cell)
    <class 'montepy.surfaces.half_space.HalfSpace'>


Combining Half-Spaces
^^^^^^^^^^^^^^^^^^^^^

Ultimately though we need to be able to *combine* these half-spaces to work with CSG.
As with OpenMC, the set logic operations have been mapped to python's bit logic operators.

* ``&``, the and operator, represents a set intersection.
* ``|``, the or operator, represents a set union.
* ``~``, the not operator, represents a set complement.

.. note::

   When you combine two half-spaces with a logical operator you create a new half-space.
   In this case the concept of a side becomes much more about "in" and "out".

.. note::

   Half-spaces need not be contiguous.

Order of precedence and grouping is automatically handled by Python so you can easily write complicated geometry in one-line.

.. testcode::

   import montepy.surfaces as surfs
   from montepy.surfaces.surface_type import SurfaceType

   # build blank surfaces
   bottom_plane = montepy.ZPlane(number=1)
   bottom_plane.location = 0.0

   top_plane = montepy.ZPlane(number=2)
   top_plane.location = 10.0

   fuel_cylinder = montepy.ZCylinder(number=3)
   fuel_cylinder.radius = 1.26 / 2

   clad_cylinder = montepy.ZCylinder(number=4)
   clad_cylinder.radius = (1.26 / 2) + 1e-3 # fuel, gap, cladding
   clad_cylinder.surface_type = SurfaceType.CZ

   clad_od = montepy.surfaces.ZCylinder(number=5)
   clad_od.radius = clad_cylinder.radius + 0.1 # add thickness
   other_fuel = montepy.ZCylinder(number=6)
   other_fuel.radius = 3.0

   #make weird truncated fuel sample
   slug_half_space = +bottom_plane & -top_plane & -fuel_cylinder
   gas_gap = ~slug_half_space & +bottom_plane & -top_plane & -clad_cylinder
   cladding = ~gas_gap & ~slug_half_space & +bottom_plane & -top_plane & -clad_od
   # make weird multi-part cell
   slugs = (+bottom_plane & -top_plane & -fuel_cylinder) |  (+bottom_plane & -top_plane & -other_fuel)

.. note::

  MontePy does not check if the geometry definition is "rational".
  It doesn't check a geometry defintion for being finite, existent (having any volume at all), or being infinite.
  Nor does it check for overlapping geometry.

Setting and Modifying Geometry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The half-space defining a cell's geometry is stored in ``cell.geometry`` (:attr:`~montepy.Cell.geometry`).
This property can be rather simply set.

.. testcode::

    fuel_cell = montepy.Cell()
    fuel_cell.geometry = +bottom_plane & - top_plane & - fuel_cylinder

This will completely redefine the cell's geometry. You can also modify the geometry with augmented assign operators, ``&=``, and ``|=``.

.. testcode::

    fuel_cyl = montepy.ZCylinder()
    fuel_cyl.number = 20
    fuel_cyl.radius = 1.20
    other_fuel_region = -fuel_cyl
    fuel_cell.geometry |= other_fuel_region #||

.. warning::

   Be careful when using ``&=`` and ``|=`` with complex geometries as the order of operations may not be what you expected.
   You can check the geometry logic by printing it.
   MontePy will show you its internal (`binary tree <https://en.wikipedia.org/wiki/Binary_tree>`_) representation of the logic.
   It will display the operators in a different style.

   * ``*`` is the intersection operator
   * ``:`` is the union operator
   * ``#`` is the complement operator

   For instance the intersection of three surface-based half-spaces could print as:::

        ((+1000*+1005)*-1010)

.. _Cloning a Cell:

Cloning a Cell
--------------
When a cell is cloned with :func:`~montepy.Cell.clone` a new number will be assigned.
If the cell is linked to a problem---either through being added to :class:`~montepy.Cells`, or with :func:`~montepy.Cell.link_to_problem`---
the next available number in the problem will be used.
Otherwise the ``starting_number`` will be used unless that is the original cell's number.
How the number is picked is controlled by ``starting_number`` and ``step``.
The new cell will attempt to use ``starting_number`` as its number.
If this number is taken ``step`` will be added to it until an available number is found.
For example:

.. doctest::

    >>> base_cell = problem.cells[1]
    >>> base_cell.number
    1
    >>> # clone with an available number
    >>> new_cell = base_cell.clone(starting_number=1000)
    >>> new_cell.number
    1000
    >>> # force a number collision
    >>> new_cell = base_cell.clone(starting_number=1, step=5)
    >>> new_cell.number
    6

Cells can also clone their material, and their dividers.
By default this is not done, and only a new ``HalfSpace`` instance is created that points to the same objects.
This is done so that the geometry definitions of the two cells can be edited without impacting the other cell.
For a lot of problems this is preferred in order to avoid creating geometry gaps due to not using the same surfaces in geometry definitions.
For example, if you have a problem read in already:

.. doctest::

    >>> cell = problem.cells[1]
    >>> cell.material.number
    1
    >>> new_cell = cell.clone()
    >>> #the material didn't change
    >>> new_cell.material is cell.material
    True
    >>> new_cell = cell.clone(clone_material=True)
    >>> new_cell.material.number # materials 2,3 are taken.
    4
    >>> new_cell.material is cell.material
    False

When children objects (:class:`~montepy.Material`, :class:`~montepy.Surface`, and :class:`~montepy.Cell`)
are cloned the numbering behavior is defined by the problem's instance's instance of the respective collection (e.g., :class:`~montepy.Materials`)
by the properties: :func:`~montepy.numbered_object_collection.NumberedObjectCollection.starting_number` and :func:`~montepy.numbered_object_collection.NumberedObjectCollection.step`.
For example:

.. doctest::

    >>> problem.materials.starting_number = 100
    >>> problem.cells[1].material.number
    1
    >>> new_cell = problem.cells[1].clone(clone_material=True)
    >>> new_cell.material.number
    100
