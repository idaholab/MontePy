Getting Started with MCNPy
==========================

MCNPy is a python API for reading, editing, and writing MCNP input files.
It does not run MCNP nor does it parse MCNP output files.
The library provides a semantic interface for working with input files, or our preferred terminology: problems.
It understands that the second entry on a cell card is the material number,
and will link the cell with its material object.

Note: Due to a conservative approach to export control restrictions MCNPy only supports MCNP 6.2 currently.

Reading a File
--------------

MCNPy offers the :func:`mcnpy.read_input` function for getting started.
It will read the specified MCNP input file, and return an MCNPy :class:`mcnpy.mcnp_problem.MCNP_Problem` object.

>>> import mcnpy
>>> problem = mcnpy.read_input("foo.imcnp")
>>> len(problem.cells)
4

Writing a File
--------------

The :class:`mcnpy.mcnp_problem.MCNP_Problem` object has the method :func:`mcnpy.mcnp_problem.MCNP_Problem.write_to_file`, which writes the problem's current 
state to a valid MCNP input file.

>>> problem.write_to_file("bar.imcnp")

If no changes are made to the problem in MCNPy the entire file will be just parroted out as it was in the original file.
However any objects (e.g., two cells) that were changed (mutated) will have their original formatting discarded,
and MCNPy will decide how to format that object in the input file.

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

What Information is Kept
------------------------

So what does MCNPy keep, and what does it forget? 
In general the philosophy of MCNPy is: meaning first; formatting second. 
Its first priority is to preserve the semantic meaning and discard complex formatting for now.

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
   recompressed. The jump (e.g, ``2j``) shortcut isn't currently expanded.

What a Problem Looks Like
-------------------------

The :class:`mcnpy.mcnp_problem.MCNP_Problem` is the object that represents an MCNP input file/problem.
The meat of the Problem is its collections, such as ``cells``, ``surfaces``, and ``materials``. 
Technically these are :class:`mcnpy.numbered_object_collection.NumberedObjectCollection`, 
but it looks like a ``dict``, walks like a ``dict``, and quacks like ``dict``, so most users can just treat it like that.

Collections are Accessible by Number
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As mentioned before :class:`mcnpy.numbered_object_collection.NumberedObjectCollection` 
looks like a ``dict``, walks like a ``dict``, and quacks like ``dict``.
This mainly means you can quickly get an object (e.g., :class:`mcnpy.cell.Cell`, :class:`mcnpy.surfaces.surface.Surface`, :class:`mcnpy.data_cards.material.Material`) 
by its number.

So say you want to access cell 6005 from a problem it is accessible quickly by:

>>> prob.cells[6005]
CELL: 2
None
SURFACE: 4, CZ
SURFACE: 5, PZ
SURFACE: 6, PZ


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

The collections also have a property called ``numbers``, which lists all numbers that are in use.
Note that using this property has some perils that will be covered in the next section.


Beware the Generators!
^^^^^^^^^^^^^^^^^^^^^^

The Collections ( ``cells``, ``surfaces``, ``materials``, etc.) offer many generators. 
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

To remove this ambiguity you need to check ``cell.is_atom_dens``.
As the name suggests it will return ``True`` if the density is an atom density,
and ``False`` if it is a mass density.

To avoid this ambiguity when setting ``cell.density`` you cannot set it to just a number.
Instead you must set it using a tuple. 
This tuple must contain a ``float``, and ``bool``.
The number is the density,
and the boolean indicates whether or not the density 
is in atom density.
``True`` means it is an atom density,
and ``False`` means it is a mass density.

Trying to set the density as a float will fail:

>>> cell.density = 5.0
---------------------------------------------------------------------------
TypeError                                 Traceback (most recent call last)
<ipython-input-3-8bc0463ae415> in <module>
----> 1 prob.cells[1].density = 5
~/dev/mcnpy/doc/mcnpy/cell.py in density(self, density_tuple)
    199             :type is_atom_dens: bool
    200         """
--> 201         density, is_atom_dens = density_tuple
    202         assert isinstance(density, float)
    203         assert isinstance(is_atom_dens, bool)
TypeError: cannot unpack non-iterable int object

Instead you must specify what density type you are providing:

>>> cell.density = (5.0, False)
>>> cell.density
5.0
>>> cell.is_atom_dens
False
>>> cell.density = (0.01, True)
>>> cell.density
0.01
>>> cell.is_atom_dens
True

Remember: make objects, not regexs!
