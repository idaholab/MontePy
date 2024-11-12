Getting Started with MontePy
============================

.. testsetup:: *

   import montepy

MontePy is a Python API for reading, editing, and writing MCNP input files.
The library provides a semantic interface for working with input files ("MCNP problems").
It does not run MCNP, nor does it parse MCNP output files.
It understands that the second entry on a cell card is the material number,
and will link the cell with its material object.

.. note::
    MontePy is built primarily to support MCNP 6.2, and MCNP 6.3. Some success maybe achieved with MCNP 6.1, and 5.1.60, 
    but there may be issues due to new features in MCNP 6.2, not being backwards compatible.
    Use earlier versions of MCNP with MontePy at your own risk.

    MCNP 6.3 is not fully supported yet either. 
    An MCNP 6.3 file that is backwards compatible with 6.2 should work fine,
    but when using the new syntaxes in 6.3,
    especially for materials,
    MontePy will likely break.

    Due to the manuals for these earlier versions of MCNP being export controlled, these versions will likely never be fully supported.

Installing
----------


System Wide (for the current user)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   If you are planning to use this in a jupyter notebook on an HPC, 
   the HPC may use modules for python, which may make it so the installed MontePy package doesn't show up in the jupyter environment.
   In this case the easiest way to deal with this is to open a teminal inside of `jupyter lab` and to install the package there.


#. Install it from `PyPI <https://pypi.org/project/montepy>`_ by running ``pip install montepy``. 
   You may need to run ``pip install --user montepy`` if you are not allowed to install the package.

Install specific version for a project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The best way maybe to setup a project-specific `conda <https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html>`_, 
`Mamba <https://mamba.readthedocs.io/en/latest/user_guide/concepts.html>`_, 
or a `venv <https://docs.python.org/3/library/venv.html>`_ environment.
The steps for installing inside one of those environments are the same as the previous steps.
You can specify a specific version from `PyPI`_ be installed using:

``pip install montepy==<version>``


Best Practices
--------------

Before we begin, here are some guidelines to keep in mind while scripting your work with MCNP models.

#. *Always* version control your input files (not output files) with `git <https://git-scm.com/>`_ or another tool.
   If you are working with very large input models, like `the ITER model <https://doi.org/10.1038/s41560-020-00753-x>`_ you may want to consider `git-lfs <https://git-lfs.com/>`_.

   #. Do learn some `git best practices <https://sethrobertson.github.io/GitBestPractices/>`_. "Update" is not a useful commit message.

#. *Always* have backups. Don't be that person that loses the last months of work when your laptop falls in a pond. 
   Make sure there's a cloud backup (could be OneDrive, GitHub, etc.). 
   Just make sure you comply with any applicable corporate policies. 

#. Don't overwrite your original file. Generally your script should open file "A", modify it, and then save it to file "B".
   This way, when there is a bug in your script, you can debug it and rerun it because "A" still exists.
   Later, if you need to make changes you can modify your script and rerun it. 
   This is especially true if your script ever becomes qualified under an `ASME NQA-1 <https://en.wikipedia.org/wiki/ASME_NQA>`_ compliant Software Quality Assurance program,
   which requires that the inputs and outputs of software be preserved.

Reading a File
--------------

MontePy offers the :func:`montepy.read_input` (actually :func:`~montepy.input_parser.input_reader.read_input`) function for getting started.
It will read the specified MCNP input file, and return an MontePy :class:`~montepy.mcnp_problem.MCNP_Problem` object.

>>> import montepy
>>> problem = montepy.read_input("tests/inputs/test.imcnp")
>>> len(problem.cells)
5

Writing a File
--------------

The :class:`~montepy.mcnp_problem.MCNP_Problem` object has
the method :func:`~montepy.mcnp_problem.MCNP_Problem.write_problem`, which writes the problem's current
state as a valid MCNP input file.

>>> problem.write_problem("bar.imcnp")

The :func:`~montepy.mcnp_problem.MCNP_Problem.write_problem` method does take an optional argument: ``overwrite``.
By default if the file exists, it will not be overwritten and an error will be raised.
This can be changed by ``overwrite=True``.

.. warning::
   Overwriting the original file (with ``overwrite=True``) when writing a modified file out is discouraged.
   This is because if your script using MontePy is buggy you have no real way to debug,
   and recover from the issue if your original file has been been modified.
   Instead of constantly having to override the same file you can add a timestamp to the output file,
   or create an always unique file name with the `UUID <https://docs.python.org/3/library/uuid.html>`_ library.

The method :func:`~montepy.mcnp_problem.MCNP_Problem.write_problem`
also accepts an open file handle, stream, or other object with a ``write()`` method.

>>> with open("foo_bar.imcnp", "w") as fh:
...     problem.write_problem(fh)
>>> new_problem = montepy.read_input("foo_bar.imcnp")
>>> len(new_problem.cells)
5


If no changes are made to the problem in MontePy, the entire file should just be parroted out as it was in the original file
(see Issues :issue:`397` and :issue:`492`).
However any objects (e.g., two cells) that were changed (i.e., mutated) may have their formatting changed slightly.
MontePy will do its best to guess the formatting of the original value and to replicate it with the new value. 
However, this may not always be possible, especially if more digits are needed to keep information (e.g., ``10`` versus ``1000``).
In this case MontePy will warn you that value will take up more space which may break your pretty formatting.

For example say we have this simple MCNP input file (saved as :download:`foo.imcnp`) ::
  
        Example Problem
        1 0  -1 2 -3
        2 0  -4 5 -6

        1 CZ 0.5
        2 PZ 0
        3 PZ 1.5
        4 CZ 0.500001
        5 PZ 1.5001
        6 PZ 2.0

        kcode 1.0 100 25 100
        TR1 0 0 1.0
        TR2 0 0 1.00001

We can then open this file in MontePy, and then modify it slightly, and save it again:

.. doctest::

        import montepy
        problem = montepy.read_input("foo.imcnp")
        problem.cells[1].number = 5
        problem.surfaces[1].number = 1000
        problem.write_problem("bar.imcnp")

This new file we can see is now reformatted according to MontePy's preferences for formatting::

        Example Problem
        5 0  -1000 2 -3
        2 0  -4 5 -6

        1000 CZ 0.5
        2 PZ 0
        3 PZ 1.5
        4 CZ 0.500001
        5 PZ 1.5001
        6 PZ 2.0

        kcode 1.0 100 25 100
        TR1 0.0 0.0 1.0
        TR2 0.0 0.0 1.00001

In addition to the renumbering of cell 5,
notice that the geometry definition for cell 5 was automatically updated to reference the new surface number.
MontePy links objects together and will automatically update "pointers" in the file for you.

What Information is Kept
------------------------

So what does MontePy keep, and what does it forget? 

Information Kept
^^^^^^^^^^^^^^^^
#. The optional message block at the beginning of the problem (it's a niche feature; check out section :manual63:`4.4.1` of the user manual)
#. The problem title
#. ``C`` style comments (e.g., ``C this is a banana``)
#. (Almost) all MCNP inputs (cards). Only the read input is discarded.
#. Dollar sign comments (e.g., ``1 0 $ this is a banana``)
#. Other user formatting and spaces. If extra spaces between values are given the space will be expanded or shortened to try to keep 
   the position of the next value in the same spot as the length of the first value changes.
#. MCNP shortcuts for numbers. All shortcuts will be expanded to their meaning. 
   Jumps will be subsituted with the value: :class:`~montepy.input_parser.mcnp_input.Jump`.
   On write MontePy will attempt to recompress all shortcuts. It does this by looking at shortcuts in the original file,
   and trying to "consume" their nearest neighbors. So for instance if you had ``imp:n 1 10r 0`` and added a new cell with an importance of ``1.0``
   second to the end MontePy will print ``imp:n 1 11r 0`` and not ``imp:n 1 10r 1 0``. 
   MontePy will not automatically "spot" various sequences that could be shortcuts and will not automatically make shortcuts out of them.
   The one exception to this rule is for jumps. If a sequence of new Jump values are added they will automatically combined as ``2J`` instead of printing them as ``J J``. 

Information Lost
^^^^^^^^^^^^^^^^
#. Read cards. These are handled properly, but when written out these cards themselves will disappear. 
   When MontePy encounters a read card it notes the file in the card, and then discard the card. 
   It will then read these extra files and append their contents to the appropriate block.
   So If you were to write out a problem that used the read card in the surface block the surface
   cards in that file from the read card will appear at the end of the new surface block in the newly written file.

.. note::

   This will hopefully change soon and read "subfiles" will be kept, and will automatically be written as their own files.



What a Problem Looks Like
-------------------------

The :class:`~montepy.mcnp_problem.MCNP_Problem` is the object that represents an MCNP input file/problem.
The meat of the Problem is its collections, such as ``cells``, ``surfaces``, and ``materials``. 
Technically these are :class:`~montepy.numbered_object_collection.NumberedObjectCollection` instances, 
but it looks like a ``dict``, walks like a ``dict``, and quacks like ``dict``, so most users can just treat it like that.

.. note::

   Though these collections are based on a dict, they don't behave exactly like a dict.
   For a dict the iteration (e.g., ``for key in dict:``) iterates over the keys.
   Also when you check if an item is in a dict (e.g., ``if key in dict:``) it checks if the item is a key.
   For :class:`~montepy.numbered_object_collection.NumberedObjectCollection` this is reversed.
   When iterating it is done over the items of the collection (e.g., ``for cell in cells:``).
   Similar checking will be done for the object being in the collection (e.g., ``if cell in cells:``).

Collections are Accessible by Number
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As mentioned before :class:`~montepy.numbered_object_collection.NumberedObjectCollection` 
looks like a ``dict``, walks like a ``dict``, and quacks like ``dict``.
This mainly means you can quickly get an object (e.g., :class:`~montepy.cell.Cell`, :class:`~montepy.surfaces.surface.Surface`, :class:`~montepy.data_cards.material.Material`) 
by its number.

So say you want to access cell 2 from a problem it is accessible quickly by:


.. doctest::
   :skipif: True # skip because multi-line doc tests are kaputt

        >>> prob = montepy.read_input("tests/inputs/test.imcnp") 
        >>> prob.cells[2]
        CELL: 2
        MATERIAL: 2, ['iron']
        density: 8.0 atom/b-cm
        SURFACE: 1005, RCC
        SURFACE: 1015, CZ
        SURFACE: 1020, PZ
        SURFACE: 1025, PZ


Collections are Iterable
^^^^^^^^^^^^^^^^^^^^^^^^

Collections are also iterable, meaning you can iterate through it quickly and easily.
For instance say you want to increase all cell numbers by 1,000. 
This can be done quickly with a for loop:

.. testcode::

   for cell in problem.cells:
       cell.number += 1000

Number Collisions (should) be Impossible
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``NumberedObjectCollection`` has various mechanisms internally to avoid number collisions 
(two objects having the same number).

.. testcode::

        import montepy
        prob = montepy.read_input("tests/inputs/test.imcnp")
        cell = montepy.Cell()
        cell.number = 2
        prob.cells.append(cell)

.. testoutput::

        Traceback (most recent call last):
           ...
        montepy.errors.NumberConflictError: Number 2 is already in use for the collection: <class 'montepy.cells.Cells'> by CELL: 2, mat: 2, DENS: 8.0 atom/b-cm

There are a number of tools to avoid this though:

#. :func:`~montepy.numbered_object_collection.NumberedObjectCollection.append_renumber` politely 
   renumbers the added object if there is a number conflict, without raising any errors or warnings.
#. :func:`~montepy.numbered_object_collection.NumberedObjectCollection.request_number` will give you the
   number you requested. If that's not possible it will find a nearby number that works.
   Note you should immediately use this number, and append the object to the Collection, 
   because this number could become stale.
#. :func:`~montepy.numbered_object_collection.NumberedObjectCollection.next_number` will find the next 
   number available by taking the highest number used and increasing it.

The collections also have a property called :func:`~montepy.numbered_object_collection.NumberedObjectCollection.numbers`, which lists all numbers that are in use.
Note that using this property has some perils that will be covered in the next section.


Beware the Generators!
^^^^^^^^^^^^^^^^^^^^^^

The Collections ( ``cells``, ``surfaces``, ``materials``, ``universes``, etc.) offer many generators. 
First, what is a generator? 
Basically they are iterators that are dynamically created.
They don't hold any information until you ask for it.

The first example of this is the ``numbers`` property. 
The collection doesn't keep this information until it is needed.
When you ask for the ``numbers`` python then iterates over all of the objects in
the collection and gets their number at the exact moment.

You can iterate over a generator, as well as check if an item is in the generator.

First it is iterable:

.. testcode::

        problem = montepy.read_input("tests/inputs/test.imcnp")
        for number in problem.cells.numbers:
            print(number)

.. testoutput::

   1
   2
   3
   99
   5

You can also check if a number is in use:

>>> 1 in problem.cells.numbers
True
>>> 1000 in problem.cells.numbers
False

Using the generators in this way does not cause any issues, but there are ways to cause issues
by making "stale" information.
This can be done by making a copy of it with ``list()``. 

>>> for num in problem.cells.numbers:
...   print(num)
1
2
3
99
5
>>> numbers = list(problem.cells.numbers)
>>> numbers
[1, 2, 3, 99, 5]
>>> problem.cells[1].number = 1000
>>> 1000 in problem.cells.numbers
True
>>> 1000 in numbers
False

Oh no! When we made a list of the numbers we broke the link, and the new list won't update when the numbers of the cells change, 
and you can cause issues this way.
The simple solution is to just access the generators directly; don't try to make copies for your own use.

Cloning Objects
^^^^^^^^^^^^^^^

In the past the only way to make a copy of a MontePy object was with `copy.deepcopy <https://docs.python.org/3/library/copy.html#copy.deepcopy>`_.
In MontePy 0.5.0 a better way was introduced: :func:`~montepy.mcnp_object.MCNP_Object.clone`.
How numbered objects, for instance :class:`~montepy.cell.Cell`, is more complicated.
If a ``Cell`` or a group of ``Cells`` are cloned their numbers will be to changed to avoid collisions.
However, if a whole :class:`~montepy.mcnp_problem.MCNP_Problem` is cloned these objects will not have their numbers changed.
For an example for how to clone a numbered object see :ref:`Cloning a Cell`.

Surfaces
--------

The most important unsung heroes of an MCNP problem are the surfaces.
They may be tedious to work with but you can't get anything done without them.
MCNP supports *alot* of types of surfaces, and all of them are special in their own way.
You can see all the surface types here: :class:`~montepy.surfaces.surface_type.SurfaceType`.
By default all surfaces are an instance of :class:`~montepy.surfaces.surface.Surface`.
They will always have the properties: ``surface_type``, and ``surface_constants``.
If you need to modify the surface you can do so through the ``surface_constants`` list.
But for some of our favorite surfaces 
(``CX``, ``CY``, ``CZ``, ``C\X``, ``C\Y``, ``C\Z``, ``PX``, ``PY``, ``PZ``),
these will be a special subclass of ``Surface``, 
that will truly understand surface constants for what the mean.
See :mod:`montepy.surfaces` for specific classes, and their documentation.

Two useful examples are the :class:`~montepy.surfaces.cylinder_on_axis.CylinderOnAxis`, 
which covers ``CX``, ``CY``, and ``CZ``,
and the :class:`~montepy.surfaces.axis_plane.AxisPlane`,
which covers ``PX``, ``PY``, ``PZ``.
The first contains the parameter: ``radius``, 
and the second one contains the parameters: ``location``. 
These describe their single surface constant.


Getting Surfaces by Type the easy way
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
So there is a convenient way to update a surface, but how do you easily get the surfaces you want?
For instance what if you want to shift a cell up in Z by 10 cm? 
It would be horrible to have to get each surface by their number, and hoping you don't change the numbers along the way.

One way you might think of is: oh let's just filter the surfaces by their type?:

.. testcode::

    for surface in cell.surfaces:
        if surface.surface_type == montepy.surfaces.surface_type.SurfaceType.PZ:
            surface.location += 10

Wow that's rather verbose. 
This was the only way to do this with the API for awhile.
But MontePy 0.0.5 fixed this with: you guessed it: generators.

The :class:`~montepy.surface_collection.Surfaces` collection has a generator for every type of surface in MCNP.
These are very easy to find: they are just the lower case version of the 
MCNP surface mnemonic. 
This previous code is much simpler now:

.. testcode::

    for surface in cell.surfaces.pz:
        surface.location += 10

Cells 
-----

Setting Cell Importances
^^^^^^^^^^^^^^^^^^^^^^^^

All cells have an importance that can be modified. 
This is generally accessed through ``cell.importance`` (:func:`~montepy.cell.Cell.importance`). 
You can access the importance for a specific particle type by its name in lower case.
For example: ``cell.importance.neutron`` or ``cell.importance.photon``.
For a complete list see :class:`~montepy.particle.Particle`.

You can also quickly get the information by passing an instance of :class:`~montepy.particle.Particle` as a key to importance.
For example:

.. doctest::

    >>> for particle in sorted(problem.mode):
    ...     print(particle, cell.importance[particle])
    neutron 0.0
    photon 0.0
    >>> print(cell.importance[montepy.Particle.NEUTRON])
    0.0

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

There is also the method: :func:`~montepy.cells.Cells.set_equal_importance`.
This method sets all of the cells for all particles in the problem to the same importance.
You can optionally pass a list of cells to this function.
These cells are the "vacuum boundary" cells.
Their importances will all be set to 0.



Setting How Cell Data Gets displayed in the Input file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Much of the cell data can show up in the cell block or the data block, like the importance card.
These are referred to MontePy as "cell modifiers".
You can change how these cell modifiers are printed with :func:`~montepy.mcnp_problem.MCNP_Problem.print_in_data_block`.
This acts like a dictionary where the key is the MCNP card name.
So to make cell importance data show up in the cell block just run:
``problem.print_in_data_block["imp"] = False``.

Density
^^^^^^^
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
^^^^^^^^

MontePy now supports understanding constructive solids geometry (CSG) set logic. 
This implementation was inspired by `OpenMC <https://docs.openmc.org/en/stable/>`_, and `their documentation <https://docs.openmc.org/en/stable/usersguide/geometry.html>`_ may be helpful.

Terminology
"""""""""""

In MCNP the geometry of a cell can by defined by either a surface, or another cell (through complements).
Therefore, it's not very useful to talk about geometry in terms of "surfaces" because it's not accurate and could lead to confusion.
MontePy focuses mostly on the mathematical concept of `half-spaces <https://en.wikipedia.org/wiki/Half-space_(geometry)>`_.
These are represented as :class:`~montepy.surfaces.half_space.HalfSpace` instances.
The use of this term is a bit loose and is not meant to be mathematical rigorous. 
The general concept though is that the space (R\ :sup:`3`) can always be split into two regions, or half-spaces.
For MontePy this division is done by a divider ( a surface, a cell, or some CSG combination of thoses).
For planes this can be seen really easily; you have a top, and bottom (or a left and a right, etc.). 
For cells this could be a bit less intuitive, but it is still a divider.
The two half-spaces can be viewed as in or out of the cell. 

So how are these half-spaces identified?
In MCNP this generally done by marking the half-space as the positive or negative one.
In MontePy these are changed to boolean values for the :func:`~montepy.surfaces.half_space.UnitHalfSpace.side` parameter simplicity with True being the positive side.
For cell complements the side is implicitly handled by the CSG logic, and can always be thought of as the "outside"
(though ``side`` will return True).

Creating a Half-Space
"""""""""""""""""""""

To make a geometry you can't just start with a divider (e.g., a surface), and just expect the geometry to be unambiguous.
This is because you need to choose a half-space from the divider.
This is done very simply and pythonic. 
For a :class:`~montepy.surfaces.surface.Surface` you just need to mark the surface as positive (``+``) or negative (``-``) (using the unary operators).
This actually creates a new object so don't worry about modifying the surface.

.. doctest::

    >>> bottom_plane = montepy.surfaces.surface.Surface()
    >>> top_plane = montepy.surfaces.surface.Surface()
    >>> type(+bottom_plane)
    <class 'montepy.surfaces.half_space.UnitHalfSpace'>
    >>> type(-bottom_plane)
    <class 'montepy.surfaces.half_space.UnitHalfSpace'>

For cells the plus/minus operator doesn't make sense. 
Instead you use the binary not operator (``~``).

.. doctest::
    
    >>> capsule_cell = montepy.Cell()
    >>> type(~capsule_cell)
    <class 'montepy.surfaces.half_space.HalfSpace'>


Combining Half-Spaces
"""""""""""""""""""""

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

Order of precedence and grouping is automatically handled by python so you can easily write complicated geometry in one-line.

.. testcode::

   # build blank surfaces 
   bottom_plane = montepy.surfaces.axis_plane.AxisPlane()
   top_plane = montepy.surfaces.axis_plane.AxisPlane()
   fuel_cylinder = montepy.surfaces.cylinder_on_axis.CylinderOnAxis()
   clad_cylinder = montepy.surfaces.cylinder_on_axis.CylinderOnAxis()
   clad_od = montepy.surfaces.cylinder_on_axis.CylinderOnAxis()
   other_fuel = montepy.surfaces.cylinder_on_axis.CylinderOnAxis()
   bottom_plane.number = 1
   top_plane.number = 2
   fuel_cylinder.number = 3
   clad_cylinder.number = 4
   clad_od.number = 5
   
   #make weird truncated fuel sample
   slug_half_space = +bottom_plane & -top_plane & -fuel_cylinder
   gas_gap = ~slug_half_space & +bottom_plane & -top_plane & -clad_cylinder
   cladding = ~gas_gap & ~slug_half_space & +bottom_plane & -top_plane & -clad_od
   # make weird multi-part cell
   slugs = (+bottom_plane & -top_plane & -fuel_cylinder) |  (+bottom_plane & -top_plane & -other_fuel)

.. note::

  MontePy does not check if the geometry definition is "rational".
  It doesn't check for being finite, existant (having any volumen at all), or being infinite.
  Nor does it check for overlapping geometry.

Setting and Modifying Geometry
""""""""""""""""""""""""""""""

The half-space defining a cell's geometry is stored in ``cell.geometry`` (:func:`~montepy.cell.Cell.geometry`).
This property can be rather simply set.

.. testcode::

    fuel_cell = montepy.Cell()
    fuel_cell.geometry = +bottom_plane & - top_plane & - fuel_cylinder

This will completely redefine the cell's geometry. You can also modify the geometry with augmented assign operators, ``&=``, and ``|=``.

.. testcode::

    other_fuel_region = -montepy.surfaces.cylinder_on_axis.CylinderOnAxis()
    fuel_cell.geometry |= other_fuel_region 

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
^^^^^^^^^^^^^^
When a cell is cloned with :func:`~montepy.cell.Cell.clone` a new number will be assigned.
If the cell is linked to a problem---either through being added to :class:`~montepy.cells.Cells`, or with :func:`~montepy.cell.Cell.link_to_problem`---
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

When children objects (:class:`~montepy.data_inputs.material.Material`, :class:`~montepy.surfaces.surface.Surface`, and :class:`~montepy.cell.Cell`)
are cloned the numbering behavior is defined by the problem's instance's instance of the respective collection (e.g., :class:`~montepy.materials.Materials`)
by the properties: :func:`~montepy.numbered_object_collection.NumberedObjectCollection.starting_number` and :func:`~montepy.numbered_object_collection.NumberedObjectCollection.step`.
For example:

.. doctest::

    >>> problem.materials.starting_number = 100
    >>> problem.cells[1].material.number
    1
    >>> new_cell = problem.cells[1].clone(clone_material=True)
    >>> new_cell.material.number 
    100

Universes
---------

MontePy supports MCNP universes as well.
``problem.universes`` will contain all universes in a problem.
These are stored in :class:`~montepy.universes.Universes` as :class:`~montepy.universe.Universe` instances. 
If a cell is not assigned to any universe it will be assigned to Universe 0, *not None*, while reading in the input file.
To change what cells are in a universe you can set this at the cell level.
This is done to prevent a cell from being assigned to multiple universes

.. testcode::

    universe = problem.universes[350]
    for cell in problem.cells[1:5]:
        cell.universe = universe
    
We can confirm this worked with the generator ``universe.cells``:

.. doctest:: 

    >>> [cell.number for cell in universe.cells]
    [1, 2, 3, 5, 4]

Claiming Cells
^^^^^^^^^^^^^^

The ``Universe`` class also has the method: :func:`~montepy.universe.Universe.claim`.
This is a shortcut to do the above code.
For all cells passed (either as a single ``Cell``, a ``list`` of cells, or a ``Cells`` instance)
will be removed from their current universe, and moved to this universe.
This simplifies the above code to just being:

.. testcode::

   universe = problem.universes[350]
   universe.claim(problem.cells[1:5])

Creating a new Universe
^^^^^^^^^^^^^^^^^^^^^^^

Creating a new universe is very straight forward.
You just need to initialize it with a new number,
and then add it to the problem:

.. testcode::
   
   universe = montepy.Universe(333)
   problem.universes.append(universe)

Now you can add cells to this universe as you normally would.

.. note::

   A universe with no cells assigned will not be written out to the MCNP input file, and will "dissapear".

.. note::

   Universe number collisions are not checked for when a universe is created,
   but only when it is added to the problem.
   Make sure to plan accordingly, and consider using :func:`~montepy.numbered_object_collection.NumberedObjectCollection.request_number`.



Filling Cells
^^^^^^^^^^^^^

What's the point of creating a universe if you can't fill a cell with it, and therefore use it?
Filling is handled by the :class:`~montepy.data_cards.fill.Fill` object in ``cell.fill``.

To fill a cell with a specific universe you can just run:

.. testcode::

    cell = problem.cells[2]
    cell.fill.universe = universe

This will then fill the cell with a single universe with no transform.
You can also easy apply a transform to the filling universe with:

.. testcode::

   import numpy as np
   transform = montepy.data_inputs.transform.Transform()
   transform.number = 5
   transform.displacement_vector = np.array([1, 2, 0])
   cell.fill.tranform = transform

.. note::

   MCNP supports some rather complicated cell filling systems.
   Mainly the ability to fill a cell with different universes for every lattice site,
   and to create an "anonymous transform" in the fill card.

   MontePy can understand and manipulate fills with these features in the input.
   However, generating these from scratch may be cumbersome.
   If you use this feature, and have input on how to make it more user friendly,
   please reach out to the developers.

References
^^^^^^^^^^

See the following cell properties for more details:

* :func:`~montepy.cell.Cell.universe`
* :func:`~montepy.cell.Cell.lattice`
* :func:`~montepy.cell.Cell.fill`

Running as an Executable
------------------------

MontePy can be ran as an executable. 
Currently this only supports checking an MCNP input file for errors.

Checking Input files for Errors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

MontePy can be ran to try to open an MCNP input file and to read as much as it can and try to note all errors it finds.
If there are many errors not all may be found at once due to how errors are handled.
This is done by executing it with the ``-c`` flag, and specifying a file, or files to check.
You can also use linux globs::

        python -m montepy -c tests/inputs/*.imcnp

MontePy will then show which file it is reading, and show a warning for every potential error with the input file it has found.

If you want to try to troubleshoot errors in python you can do this with the following steps.

.. warning::
   This following guide may return an incomplete problem object that may break in very wierd ways.
   Never use this for actual file editing; only use it for troubleshooting.

1. Setup a new Problem object:

   .. testcode::
        
       problem = montepy.MCNP_Problem("foo.imcnp") 

1. Next load the input file with the ``check_input`` set to ``True``.

   .. testcode::
        
        problem.parse_input(True)


**Remember: make objects, not regexes!**
