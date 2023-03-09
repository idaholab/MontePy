Tips and Tricks
===============

Here's a random collection of some tips and tricks that should make your life easier.

.. contents:: Table of Contents
   :depth: 3

Getting The Highest Plane
-------------------------

With the :class:`mcnpy.surface_collection.Surfaces` mnemonic generators you can quickly 
get the "extreme" surfaces, using the max and min function.

By default though these functions will sort the surfaces by surface number.
Rather you need to use the key argument to change how the surfaces are sorted.
These examples use `python lambda expressions <https://docs.python.org/3/tutorial/controlflow.html#lambda-expressions>`_,
which are very short anonymous functions.

Here are some examples:

Getting Highest PZ plane
~~~~~~~~~~~~~~~~~~~~~~~~

>>> max(surfaces.pz, key = lambda x: x.location)
Surface: 1 PZ

Getting the Lowest PZ plane
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Similarly you can get the lowest surface with the min function:

>>> min(surfaces.pz, key = lambda x: x.location)
Surface: 5 PZ

Getting the Largest CZ Cylinder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Similar to before you can use this method to find cylinders by their radius:

>>> max(surfaces.cz, key = lambda x: x.radius)
surface: 10 CZ

Translating Cells
-----------------

Translating experiment axially
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For some problems you can quickly move a whole problem axially (in z) with a simple loop like:

>>> for surface in problem.surfaces.pz:
>>>     surface.location += 10

.. note::
   This only works for problems that are infinite in Z, with "cutting" PZ planes, such as a fuel rod.
   This is because only the PZ surfaces are moving. If you had a sphere in the problem for instance,
   this would break the problem geometry then as the sphere would not move as well.

.. note::
   Make sure you loop over all the surfaces in the problem, and not over all the cells. For instance:
   
   >>> for cell in problem.cells:
   >>>     for surface in cell.surfaces:
   >>>         surface.location += 10

   will cause geometry errors. Surfaces are commonly used by multiple cells so each surface may be translated repeatedly.
