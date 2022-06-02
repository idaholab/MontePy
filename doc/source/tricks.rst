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
These examples use [python lambda expressions](https://docs.python.org/3/tutorial/controlflow.html#lambda-expressions),
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
