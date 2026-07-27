.. meta::
   :description lang=en:
        How MontePy represents an MCNP problem: collections, numbering, generators, cloning, and creating objects from strings.

What a Problem Looks Like
=========================

.. testsetup:: *

   import montepy

The :class:`~montepy.MCNP_Problem` is the object that represents an MCNP input file/problem.
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
-------------------------------------

As mentioned before :class:`~montepy.numbered_object_collection.NumberedObjectCollection`
looks like a ``dict``, walks like a ``dict``, and quacks like ``dict``.
This mainly means you can quickly get an object (e.g., :class:`~montepy.Cell`, :class:`~montepy.Surface`, :class:`~montepy.Material`)
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

Slicing Collections
-------------------

Collections can be sliced to get a new collection containing a subset of objects.
However, the slicing behavior is different from standard Python lists. The indices
used for slicing correspond to the object numbers, and the slice is inclusive of the endpoint.

For example, ``problem.cells[1:3]`` will return a new ``Cells`` collection containing
cells with the numbers 1, 2, and 3, *if* they exist.

.. testcode::

    problem = montepy.read_input("tests/inputs/test.imcnp")
    for cell in problem.cells[1:3]:
        print(cell.number)

.. testoutput::

    1
    2
    3


Collections are Iterable
------------------------

Collections are also iterable, meaning you can iterate through it quickly and easily.
For instance say you want to increase all cell numbers by 1,000.
This can be done quickly with a for loop:

.. testcode::

   for cell in problem.cells:
       cell.number += 1000

Number Collisions Should Be Impossible
---------------------------------------

The ``NumberedObjectCollection`` has various mechanisms internally to avoid number collisions
(two objects having the same number).

.. testcode::

        import montepy
        prob = montepy.read_input("tests/inputs/test.imcnp")
        cell = montepy.Cell(number = 2)
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

The collections also have a property called :attr:`~montepy.numbered_object_collection.NumberedObjectCollection.numbers`, which lists all numbers that are in use.
Note that using this property has some perils that will be covered in the next section.


Beware the Generators!
-----------------------

The Collections ( :class:`~montepy.Cells`, :class:`~montepy.Surfaces`, :class:`~montepy.Materials`, :class:`~montepy.Universes`, etc.) offer many generators.
First, what is a generator?
Basically they are iterators that are dynamically created.
They don't hold any information until you ask for it.

The first example of this is the :attr:`~montepy.numbered_object_collection.NumberedObjectCollection.numbers` property.
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
This can be done by making a copy of it with :class:`list`.

.. doctest::

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
---------------

In the past the only way to make a copy of a MontePy object was with :func:`copy.deepcopy`.
In MontePy 0.5.0 a better way was introduced: :func:`~montepy.mcnp_object.MCNP_Object.clone`.
How numbered objects, for instance :class:`~montepy.Cell`, is more complicated.
If a ``Cell`` or a group of ``Cells`` are cloned their numbers will be to changed to avoid collisions.
However, if a whole :class:`~montepy.MCNP_Problem` is cloned these objects will not have their numbers changed.
For an example for how to clone a numbered object see :ref:`Cloning a Cell`.

Creating Objects from a String
-------------------------------

Sometimes its more convenient to create an MCNP object from its input string for MCNP, rather than setting a lot of properties,
or the object you need isn't supported by MontePy yet.
In this case there are a few ways to generate this object.
First all :class:`~montepy.mcnp_object.MCNP_Object` constructors can take a string:

.. doctest::

   >>> cell = montepy.Cell("1 0 -2 imp:n=1")
   >>> cell.number
   1
   >>> cell.importance[montepy.Particle.NEUTRON]
   1.0
   >>> # surfaces
   >>> surf = montepy.ZPlane("5 PZ 10")
   >>> surf.number
   5
   >>> surf.location
   10.0
   >>> # materials
   >>> mat = montepy.Material("M1 1001.80c 2 8016.80c 1")
   >>> mat.number
   1
   >>> thermal_scat = montepy.ThermalScatteringLaw("MT1 lwrt.40t")
   >>> thermal_scat.old_number
   1
   >>> #object linking hasn't occuring
   >>> print(thermal_scat.parent_material)
   None

For data inputs and surfaces there are some helper functions that help parse all objects of that type,
and return the appropriate object.
For surfaces this is: :func:`~montepy.surfaces.surface_builder.parse_surface`,
and for data inputs this is :func:`~montepy.data_inputs.data_parser.parse_data`.

.. doctest::

   >>> surf = montepy.parse_surface("1 cz 5.0")
   >>> type(surf)
   <class 'montepy.surfaces.surface.ZCylinder'>
   >>> surf.radius
   5.0
   >>> mat = montepy.parse_data("m1 1001.80c 1")
   >>> type(mat)
   <class 'montepy.data_inputs.material.Material'>


This object is still unlinked from other objects, and won't be kept with a problem.
So there is also :func:`~montepy.MCNP_Problem.parse`.
This takes a string, and then creates the MCNP object,
links it to the problem,
links it to its other objects (e.g., surfaces, materials, etc.),
and appends it to necessary collections (if requested):

.. testcode::

   problem = montepy.read_input("tests/inputs/test.imcnp")
   cell = problem.parse("123 0 -1005")
   assert cell in problem.cells
   assert cell.surfaces[1005] is problem.surfaces[1005]
   cell = problem.parse("124 0 -1005", append=False)
   assert cell not in problem.cells
