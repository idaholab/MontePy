Getting Started with MCNPy
==========================

MCNPy is a python API for reading, editing, and writing MCNP input files.
It does not run MCNP nor does it parse MCNP output files.
The library provides a semantic interface for working with input files, or our preferred terminology: problems.
It understands that the second entry on a cell card is the material number,
and will link the cell with its material object.

.. warning::
    MCNPy is built primarily to support MCNP 6.2. Some success maybe achieved with MCNP 6.1, and 5.1.60, 
    but there may be issues due to new features in MCNP 6.2, not being backwards compatible.
    Use earlier versions of MCNP with MCNPy at your own risk.

    Due to the manuals for these earlier versions of MCNP being export controlled, these versions will likely never be fully supported.

Reading a File
--------------

MCNPy offers the :func:`mcnpy.read_input` (actually :func:`mcnpy.input_parser.input_reader.read_input`) function for getting started.
It will read the specified MCNP input file, and return an MCNPy :class:`mcnpy.mcnp_problem.MCNP_Problem` object.

>>> import mcnpy
>>> problem = mcnpy.read_input("foo.imcnp")
>>> len(problem.cells)
4

Writing a File
--------------

The :class:`mcnpy.mcnp_problem.MCNP_Problem` object has the method :func:`mcnpy.mcnp_problem.MCNP_Problem.write_to_file`, which writes the problem's current 
state as a valid MCNP input file.

>>> problem.write_to_file("bar.imcnp")

.. warning::
   Be careful with overwriting the original file when writing a modified file out.
   This will wipe out the original version, and if you have no version control,
   may lead to losing information.

If no changes are made to the problem in MCNPy the entire file will be just parroted out as it was in the original file.
However any objects (e.g., two cells) that were changed (i.e., mutated) will have their original formatting discarded,
and MCNPy will decide how to format that object in the input file.

.. note::
    This behavior will change with version 0.1.5.
    The main scope of this release will be fundamental design change that will preserve all user formatting.

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

We can then open this file in MCNPy, and then modify it slightly, and save it again::

        import mcnpy
        problem = mcnpy.read_input("foo.imcnp")
        problem.cells[1].number = 5
        problem.surfaces[1].number = 1000
        problem.write_to_file("bar.imcnp")

This new file we can see is now reformatted according to MCNPy's preferences for formatting::

        Example Problem
        5 0
              -1000 2 -3
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

In addition to the reformatting of cell 5,
notice that the geometry definition for cell 5 was automatically updated to reference the new surface number.
MCNPy links objects together and will automatically update "pointers" in the file for you.

Setting Cell Importances
------------------------
All cells have an importance that can be modified. 
This is generally accessed through ``cell.importance``. 
You can access the importance for a specific particle type by its name.
For example: ``cell.importance.neutron`` or ``cell.importance.photon``.

You can also quickly get the information by passing an instance of:class:`mcnpy.particle.Particle` as a key to importance.
For example: ::
    
    for particle in problem.mode:
        print(cell.importance[particle])

There's also a lot of convenient ways to do bulk modifications.
There is the ``all`` property that lets you set the importance for all particles in the problem at once.
For example: ::

    problem.set_mode("n p")
    cell.importance.all = 2.0

This will set the importances for the neutron and photon. 

There is also the method: :func:`mcnpy.cells.Cells.set_equal_importance`.
This method sets all of the cells for all particles in the problem to the same importance.
You can optionally pass a list of cells to this function.
These cells are the "vacuum boundary" cells.
Their importances will all be set to 0.



Setting How Cell Data Gets displayed in the Input file
------------------------------------------------------

Much of the cell data can show up in the cell block or the data block, like the importance card.
These are referred to MCNPy as "cell modifiers".
You can change how these cell modifiers are printed with :func:`mcnpy.mcnp_problem.MCNP_Problem.print_in_data_block`.
This acts like a dictionary where the key is the MCNP card name.
So to make cell importance data show up in the cell block just run:
``problem.print_in_data_block["imp"] = False``.

What Information is Kept
------------------------

So what does MCNPy keep, and what does it forget? 
In general the philosophy of MCNPy is: meaning first; formatting second. 
Its first priority is to preserve the semantic meaning and discard complex formatting for now.

.. note::
   This paradigm will change dramatically with release 0.1.5.

Information Kept
^^^^^^^^^^^^^^^^
#. The optional message block at the beginning of the problem (it's a niche feature checkout section 2.4 of the user manual)
#. The problem title
#. ``C`` style comments (e.g., ``C this is a banana``)
#. (Almost) all MCNP inputs (cards). Only the read card is discarded.

Information Lost
^^^^^^^^^^^^^^^^
#. Dollar sign comments (e.g., ``1 0 $ this is a banana``)
#. Read cards. These are handled properly, but when written out these cards themselves will disappear. 
   When MCNPy encounters a read card it notes the file in the card, and then discard the card. 
   It will then read these extra files and append their contents to the appropriate block.
   So If you were to write out a problem that used the read card in the surface block the surface
   cards in that file from the read card will appear at the end of the new surface block in the newly written file.
#. MCNP shortcuts for numbers. The shortcuts like: ``1 9r`` will be expanded to its meaning, and will not be
   recompressed, easily. Jumps will be subsituted with the valued :class:`mcnpy.input_parser.mcnp_input.Jump`.
   When writing cell modifiers (e.g., ``imp``, ``vol``, etc.) recompression will be attempted,
   as there can be a lot of information here.
   The only shortcuts currently recompressed are repeats and jumps though.

What a Problem Looks Like
-------------------------

The :class:`mcnpy.mcnp_problem.MCNP_Problem` is the object that represents an MCNP input file/problem.
The meat of the Problem is its collections, such as ``cells``, ``surfaces``, and ``materials``. 
Technically these are :class:`mcnpy.numbered_object_collection.NumberedObjectCollection`, 
but it looks like a ``dict``, walks like a ``dict``, and quacks like ``dict``, so most users can just treat it like that.

.. note::
   Though these collections are based on a dict, they don't behave exactly like a dict.
   For a dict the iteration (e.g., ``for key in dict:``) iterates over the keys.
   Also when you check if an item is in a dict (e.g., ``if key in dict:``) it checks if the item is a key.
   For :class:`mcnpy.numbered_object_collection.NumberedObjectCollection` this is reversed.
   When iterating it is done over the items of the collection (e.g., ``for cell in cells:``).
   Similar checking will be done for the object being in the collection (e.g., ``if cell in cells:``).

Collections are Accessible by Number
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As mentioned before :class:`mcnpy.numbered_object_collection.NumberedObjectCollection` 
looks like a ``dict``, walks like a ``dict``, and quacks like ``dict``.
This mainly means you can quickly get an object (e.g., :class:`mcnpy.cell.Cell`, :class:`mcnpy.surfaces.surface.Surface`, :class:`mcnpy.data_cards.material.Material`) 
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

>>> import mcnpy
>>> prob = mcnpy.read_input("foo.i")
>>> cell = mcnpy.Cell()
>>> cell.number = 2
prob.cells.append(cell)
---------------------------------------------------------------------------
NumberConflictError                       Traceback (most recent call last)
<ipython-input-5-52c64b5ddb4b> in <module>
----> 1 prob.cells.append(cell)
~/dev/mcnpy/doc/mcnpy/numbered_object_collection.py in append(self, obj)
    130         assert isinstance(obj, self._obj_class)
    131         if obj.number in self.numbers:
--> 132             raise NumberConflictError(
    133                 (
    134                     "There was a numbering conflict when attempting to add "
NumberConflictError: There was a numbering conflict when attempting to add CELL: 2
None
 to <class 'mcnpy.cells.Cells'>. Conflict was with CELL: 2
None
SURFACE: 4, CZ
SURFACE: 5, PZ
SURFACE: 6, PZ

There are a number of tools to avoid this though:

#. :func:`mcnpy.numbered_object_collection.NumberedObjectCollection.append_renumber` politely 
   renumbers the added object if there is a number conflict.
#. :func:`mcnpy.numbered_object_collection.NumberedObjectCollection.request_number` will give you the
   number you requested. If that's not possible it will find a nearby number that works.
   Note you should immediately use this number, and append the object to the Collection, 
   because this number could become stale.
#. :func:`mcnpy.numbered_object_collection.NumberedObjectCollection.next_number` will find the next 
   number available by taking the highest number used and increasing it.

The collections also have a property called :func:`mcnpy.numbered_object_collection.NumberedObjectCollection.numbers`, which lists all numbers that are in use.
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
You can see all the surface types here: :class:`mcnpy.surfaces.surface_type.SurfaceType`.
By default all surfaces are an instance of :class:`mcnpy.surfaces.surface.Surface`.
They will always have the properties: ``surface_type``, and ``surface_constants``.
If you need to modify the surface you can do so through the ``surface_constants`` list.
But for some of our favorite surfaces 
(``CX``, ``CY``, ``CZ``, ``C\X``, ``C\Y``, ``C\Z``, ``PX``, ``PY``, ``PZ``),
these will be a special subclass of ``Surface``, 
that will truly understand surface constants for what the mean.
See :mod:`mcnpy.surfaces` for specific classes, and their documentation.

Two useful examples are the :class:`mcnpy.surfaces.cylinder_on_axis.CylinderOnAxis`, 
which covers ``CX``, ``CY``, and ``CZ``,
and the :class:`mcnpy.surfaces.axis_plane.AxisPlane`,
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
    if surface.surface_type == mcnpy.surfaces.surface_type.SurfaceType.PZ:
      surface.location += 10

Wow that's rather verbose. 
This was the only way to do this with the API for awhile.
But MCNPy 0.0.5 fixed this with: you guessed it: generators.

The :class:`mcnpy.surface_collection.Surfaces` collection has a generator for every type of surface in MCNP.
These are very easy to find: they are just the lower case version of the 
MCNP surface mnemonic. 
This previous code is much simpler now::

  for surface in cell.surfaces.pz:
    surface.location += 10

Cells 
-----
Density
^^^^^^^
This gets a bit more complicated.
MCNP supports both atom density, and mass density. 
So when you access ``cell.density`` on its own,
the result is ambiguous, 
because it could be in g/cm3 or atom/b-cm.
No; MCNPy does not support negative density; it doesn't exist!
For this reason ``cell.density`` is deprecated.
Instead there is now ``cell.atom_density`` and ``cell.mass_density``. 

``cell.atom_density`` is in units of atomcs/b-cm,
and ``cell.mass_density`` is in units of g/cm3.
Both will never return a valid number simultaneously.
If the cell density is set to a mass density ``cell.atom_density`` will return ``None``.
Setting the value for one of these densities will change the density mode.
MCNPy does not convert mass density to atom density and vice versa.

>>> cell.mass_density
9.8
>>> cell.atom_density 
None
>>> cell.atom_density = 0.5
>>> cell.mass_density
None


Universes
---------

MCNPy supports MCNP universes as well.
``problem.universes`` will contain all universes in a problem.
These are stored in :class:`mcnpy.universes.Universes` as :class:`mcnpy.universe.Universe` instances. 
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

The ``Universe`` class also has the method: :func:`mcnpy.universe.Universe.claim`.
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
   
   universe = mcnpy.Universe(333)
   problem.universes.append(universe)

Now you can add cells to this universe as you normally would.

.. note::
   A universe with no cells assigned will not be written out to the MCNP input file, and will "dissapear".

.. note::
   Universe number collisions are not checked for when a universe is created,
   but only when it is added to the problem.
   Make sure to plan accordingly, and consider using :func:`mcnpy.numbered_object_collection.NumberedObjectCollection.request_number`.



Filling Cells
^^^^^^^^^^^^^

What's the point of creating a universe if you can't fill a cell with it, and therefore use it?
Filling is handled by the :class:`mcnpy.data_cards.fill.Fill` object in ``cell.fill``.

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

   MCNPy can understand and manipulate fills with these features in the input.
   However, generating these from scratch may be cumbersome.
   If you use this feature, and have input on how to make it more user friendly,
   please reach out to the developers.



References
^^^^^^^^^^

See the following cell properties for more details:

* :func:`mcnpy.cell.Cell.universe`
* :func:`mcnpy.cell.Cell.lattice`
* :func:`mcnpy.cell.Cell.fill`

Remember: make objects, not regexes!
====================================
