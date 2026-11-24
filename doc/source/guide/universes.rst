.. meta::
   :description lang=en:
        Working with MCNP universes in MontePy: claiming cells, creating universes, and filling cells.

Universes
=========

.. testsetup:: *

   import montepy

MontePy supports MCNP universes as well.
``problem.universes`` will contain all universes in a problem.
These are stored in :class:`~montepy.universes.Universes` as :class:`~montepy.Universe` instances.
If a cell is not assigned to any universe it will be assigned to Universe 0, *not None*, while reading in the input file.
To change what cells are in a universe you can set this at the cell level.
This is done to prevent a cell from being assigned to multiple universes

.. testcode::

    problem = montepy.read_input("tests/inputs/test.imcnp")
    universe = problem.universes[350]
    for cell in problem.cells[1:5]:
        cell.universe = universe

We can confirm this worked with the generator ``universe.cells``:

.. doctest::

    >>> [cell.number for cell in universe.cells]
    [1, 2, 3, 5]

Claiming Cells
--------------

The ``Universe`` class also has the method: :func:`~montepy.Universe.claim`.
This is a shortcut to do the above code.
For all cells passed (either as a single ``Cell``, a ``list`` of cells, or a ``Cells`` instance)
will be removed from their current universe, and moved to this universe.
This simplifies the above code to just being:

.. testcode::

   universe = problem.universes[350]
   universe.claim(problem.cells[1:5])

Creating a New Universe
-----------------------

Creating a new universe is very straight forward.
You just need to initialize it with a new number,
and then add it to the problem:

.. testcode::

   universe = montepy.Universe(333)
   problem.universes.append(universe)

Now you can add cells to this universe as you normally would.

.. note::

   A universe with no cells assigned will not be written out to the MCNP input file, and will "disappear".

.. note::

   Universe number collisions are not checked for when a universe is created,
   but only when it is added to the problem.
   Make sure to plan accordingly, and consider using :func:`~montepy.numbered_object_collection.NumberedObjectCollection.request_number`.



Filling Cells
-------------

What's the point of creating a universe if you can't fill a cell with it, and therefore use it?
Filling is handled by the :class:`~montepy.data_inputs.fill.Fill` object in ``cell.fill``.

To fill a cell with a specific universe you can just run:

.. testcode::

    cell = problem.cells[2]
    cell.fill.universe = universe

This will then fill the cell with a single universe with no transform.
You can also easy apply a transform to the filling universe with:

.. testcode::

   import numpy as np
   transform = montepy.data_inputs.transform.Transform(number=5)
   transform.displacement_vector = np.array([1, 2, 0])
   cell.fill.transform = transform

.. note::

   MCNP supports some rather complicated cell filling systems.
   Mainly the ability to fill a cell with different universes for every lattice site,
   and to create an "anonymous transform" in the fill card.

   MontePy can understand and manipulate fills with these features in the input.
   However, generating these from scratch may be cumbersome.
   If you use this feature, and have input on how to make it more user friendly,
   please reach out to the developers.

References
----------

See the following cell properties for more details:

* :attr:`~montepy.Cell.universe`
* :attr:`~montepy.Cell.lattice`
* :attr:`~montepy.Cell.fill`
