Getting Started with MontePy
============================

MontePy is a python API for reading, editing, and writing MCNP input files.
It does not run MCNP nor does it parse MCNP output files.
The library provides a semantic interface for working with input files, or our preferred terminology: problems.
It understands that the second entry on a cell card is the material number,
and will link the cell with its material object.

.. warning::
    MontePy is built primarily to support MCNP 6.2. Some success maybe achieved with MCNP 6.1, and 5.1.60, 
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


#. Install it from `PyPI <https://pypi.org>`_ by running ``pip install --user montepy``.

Install specific version for a project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The best way maybe to setup a project-specific `conda <https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html>`_, 
`Mamba <https://mamba.readthedocs.io/en/latest/user_guide/concepts.html>`_, 
or a `venv <https://docs.python.org/3/library/venv.html>`_ environment.
The steps for installing inside one of those environments are the same as the previous steps.

Another option is to clone the repository and to use symbolic-links. In this scenario we'll assume that your local
repository is located at ``~/dev/montepy``, and your project is located at ``~/foo/bar``. 

#. Move to the repository parent folder: ``cd ~/dev``
#. Clone this repository: ``git clone https://github.com/idaholab/montepy.git`` 
#. Enter the repository: ``cd montepy``
#. Checkout the specific version you want. These are tagged with git tags
    #. You can list all tags with ``git tag``
    #. You can then checkout that tag: ``git checkout <tag>``
#. Install the dependent requirements: ``pip install -r requirements/common.txt``
#. Move to your project folder: ``cd ~/foo/bar``
#. Create a symbolic link in the project folder to the repository: ``ln -s ~/dev/montepy/montepy montepy``

Now when you run a python script in that folder (*and only in that folder*) ``import montepy`` will use the specific version you want. 

Reading a File
--------------

MontePy offers the :func:`montepy.read_input` (actually :func:`~montepy.input_parser.input_reader.read_input`) function for getting started.
It will read the specified MCNP input file, and return an MontePy :class:`~montepy.mcnp_problem.MCNP_Problem` object.

>>> import montepy
>>> problem = montepy.read_input("foo.imcnp")
>>> len(problem.cells)
4

Writing a File
--------------

The :class:`~montepy.mcnp_problem.MCNP_Problem` object has the method :func:`~montepy.mcnp_problem.MCNP_Problem.write_to_file`, which writes the problem's current 
state as a valid MCNP input file.

>>> problem.write_to_file("bar.imcnp")

.. warning::
   Be careful with overwriting the original file when writing a modified file out.
   This will wipe out the original version, and if you have no version control,
   may lead to losing information.

If no changes are made to the problem in MontePy the entire file will be just parroted out as it was in the original file.
However any objects (e.g., two cells) that were changed (i.e., mutated) may have their formatting changed slightly.
MontePy will do its best to guess the formatting of the original value and to replicate it with the new value. 
However, this may not always be possible, especially if more digits are needed to keep information (e.g., ``10`` versus ``1000``).
In this case MontePy will warn you that value will take up more space which may break your pretty formatting.

For example say we have this simple MCNP input file (saved as foo.imcnp) ::
  
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

We can then open this file in MontePy, and then modify it slightly, and save it again::

        import montepy
        problem = montepy.read_input("foo.imcnp")
        problem.cells[1].number = 5
        problem.surfaces[1].number = 1000
        problem.write_to_file("bar.imcnp")

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
#. The optional message block at the beginning of the problem (it's a niche feature checkout section 2.4 of the user manual)
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

>>> prob.cells[2]
CELL: 2
MATERIAL: 2, ['iron']
density: 8.0 atom/b-cm
SURFACE: 1005, RCC


Collections are Iterable
^^^^^^^^^^^^^^^^^^^^^^^^

Collections are also iterable, meaning you can iterate through it quickly and easily.
For instance say you want to increase all cell numbers by 1,000. 
This can be done quickly with a for loop::
        
        for cell in problem.cells:
          cell.number += 1000

Number Collisions (should) be Impossible
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``NumberedObjectCollection`` has various mechanisms internally to avoid number collisions 
(two objects having the same number).

>>> import montepy
>>> prob = montepy.read_input("foo.i")
>>> cell = montepy.Cell()
>>> cell.number = 2
prob.cells.append(cell)
---------------------------------------------------------------------------
NumberConflictError                       Traceback (most recent call last)
<ipython-input-5-52c64b5ddb4b> in <module>
----> 1 prob.cells.append(cell)
~/dev/montepy/doc/montepy/numbered_object_collection.py in append(self, obj)
    130         assert isinstance(obj, self._obj_class)
    131         if obj.number in self.numbers:
--> 132             raise NumberConflictError(
    133                 (
    134                     "There was a numbering conflict when attempting to add "
NumberConflictError: There was a numbering conflict when attempting to add CELL: 2
None
 to <class 'montepy.cells.Cells'>. Conflict was with CELL: 2
None
SURFACE: 4, CZ
SURFACE: 5, PZ
SURFACE: 6, PZ

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

>>> for number in problem.cells.numbers:
>>>    print(number)
1
2

You can also check if a number is in use:

>>> 1 in problem.cells.numbers
True
>>> 1000 in problem.cells.numbers
False

Using the generators in this way does not cause any issues, but there are ways to cause issues
by making "stale" information.
This can be done by making a copy of it with ``list()``. 

>>> for num in problem.cells.numbers:
>>>   print(num)
1
2
>>> numbers = list(problem.cells.numbers)
>>> numbers
[1,2]
>>> problem.cells[1].number = 1000
>>> 1000 in problem.cells.numbers
True
>>> 1000 in numbers
False

Oh no! When we made a list of the numbers we broke the link, and the new list won't update when the numbers of the cells change, 
and you can cause issues this way.
The simple solution is to just access the generators directly; don't try to make copies for your own use.

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

One way you might think of is: oh let's just filter the surfaces by their type?::

  for surface in cell.surfaces:
    if surface.surface_type == montepy.surfaces.surface_type.SurfaceType.PZ:
      surface.location += 10

Wow that's rather verbose. 
This was the only way to do this with the API for awhile.
But MontePy 0.0.5 fixed this with: you guessed it: generators.

The :class:`~montepy.surface_collection.Surfaces` collection has a generator for every type of surface in MCNP.
These are very easy to find: they are just the lower case version of the 
MCNP surface mnemonic. 
This previous code is much simpler now::

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
For example: ::
    
    for particle in problem.mode:
        print(cell.importance[particle])
    print(cell.importance[montepy.Particle.NEUTRON])

There's also a lot of convenient ways to do bulk modifications.
There is the :func:`~montepy.data_inputs.importance.Importance.all` property that lets you set the importance for all particles in the problem at once.
For example: ::

    problem.set_mode("n p")
    cell.importance.all = 2.0

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

>>> cell.mass_density
9.8
>>> cell.atom_density 
None
>>> cell.atom_density = 0.5
>>> cell.mass_density
None

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

>>> type(+bottom_plane)
montepy.surfaces.half_space.UnitHalfSpace
>>> type(-bottom_plane)
montepy.surfaces.half_space.UnitHalfSpace

For cells the plus/minus operator doesn't make sense. 
Instead you use the binary not operator (``~``).

>>> type(~capsule_cell)
montepy.surfaces.half_space.HalfSpace


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

.. code-block:: python

   #make weird truncated fuel sample
   slug_half_space = +bottom_plane & -top_plane & -fuel_cylinder
   gas_gap = ~slug_half_space & +bottom_plane & -top_plane & -clad_cylinder
   cladding = ~gas_gap & ~slug_half_space & +bottom_plane & -top_plane & -clad_od

   # make weird multi-part cell
  slugs = (+bottom_plane & -top_plane & -fuel_cylinder) | (+bottom_plane & -top_plane & -other_fuel)

.. note::
  MontePy does not check if the geometry definition is "rational".
  It doesn't check for being finite, existant (having any volumen at all), or being infinite.
  Nor does it check for overlapping geometry.

Setting and Modifying Geometry
""""""""""""""""""""""""""""""

The half-space defining a cell's geometry is stored in ``cell.geometry`` (:func:`~montepy.cell.Cell.geometry`).
This property can be rather simply set.::

    fuel_cell.geometry = +bottom_plane & - top_plane & - fuel_cylinder

This will completely redefine the cell's geometry. You can also modify the geometry with augmented assign operators, ``&=``, and ``|=``.::

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

Universes
---------

MontePy supports MCNP universes as well.
``problem.universes`` will contain all universes in a problem.
These are stored in :class:`~montepy.universes.Universes` as :class:`~montepy.universe.Universe` instances. 
If a cell is not assigned to any universe it will be assigned to Universe 0, *not None*, while reading in the input file.
To change what cells are in a universe you can set this at the cell level.
This is done to prevent a cell from being assigned to multiple universes

.. code-block:: python
    
    universe = problem.universes[350]
    for cell in problem.cells[1:5]:
        cell.universe = universe
    
We can confirm this worked with the generator ``universe.cells``:

>>> [cell.number for cell in universe.cells]
[1, 2, 3, 4, 5]

Claiming Cells
^^^^^^^^^^^^^^

The ``Universe`` class also has the method: :func:`~montepy.universe.Universe.claim`.
This is a shortcut to do the above code.
For all cells passed (either as a single ``Cell``, a ``list`` of cells, or a ``Cells`` instance)
will be removed from their current universe, and moved to this universe.
This simplifies the above code to just being:

.. code-block:: python

   universe = problem.universes[350]
   universe.claim(problem.cells[1:5])

Creating a new Universe
^^^^^^^^^^^^^^^^^^^^^^^

Creating a new universe is very straight forward.
You just need to initialize it with a new number,
and then add it to the problem:

.. code-block:: python
   
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

.. code-block:: python

        cell.fill.universe = universe

This will then fill the cell with a single universe with no transform.
You can also easy apply a transform to the filling universe with:

.. code-block:: python

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

        python -m montepy -c inputs/*.imcnp

MontePy will then show which file it is reading, and show a warning for every potential error with the input file it has found.

If you want to try to troubleshoot errors in python you can do this with the following steps.

.. warning::
   This following guide may return an incomplete problem object that may break in very wierd ways.
   Never use this for actual file editing; only use it for troubleshooting.

1. Setup a new Problem object:

   .. code-block:: python
        
       problem = montepy.MCNP_Problem("foo.imcnp") 

1. Next load the input file with the ``check_input`` set to ``True``.

   .. code-block:: python
        
        problem.parse_input(True)


**Remember: make objects, not regexes!**
