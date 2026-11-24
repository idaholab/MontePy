.. meta::
   :description lang=en:
        Working with MCNP surfaces in MontePy: surface types, type-based access, and boundary conditions.

Surfaces
========

.. testsetup:: *

   import montepy
   problem = montepy.read_input("tests/inputs/test.imcnp")
   cell = problem.cells[3]

.. versionchanged:: 1.4.0

   In past versions the classes: :class:`~montepy.CylinderOnAxis`, :class:`~montepy.CylinderParAxis`,
   and :class:`~montepy.AxisPlane` were the preferred and only way to work with the surface types:
   ``CX``, ``C/X``, and ``PX`` respectively.
   Now the preferred classes are :class:`~montepy.XCylinder`, :class:`~montepy.XCylinderParAxis`,
   and :class:`~montepy.XPlane` respectively.
   These all inherit from the original classes (e.g., ``XPlane`` inherits from ``AxisPlane``),
   so :func:`python:isinstance` still works the same as before this change.
   There is no plan to deprecate these root classes,
   just the documentation will not recommend using them directly.

The most important unsung heroes of an MCNP problem are the surfaces.
They may be tedious to work with but you can't get anything done without them.
MCNP supports *a lot* of types of surfaces, and all of them are special in their own way.
You can see all the surface types here: :class:`~montepy.SurfaceType`.
All surfaces are an inherit from :class:`~montepy.Surface`, or are directly an instance of :class:`~montepy.Surface`.
They will always have the properties: :attr:`~montepy.Surface.surface_type`, and :attr:`~montepy.Surface.surface_constants`.
For almost all surface types (except for axisymmetric surfaces defined by points, i.e., :attr:`~montepy.SurfaceType.X`, :attr:`~montepy.SurfaceType.Y`, and :attr:`~montepy.SurfaceType.Z`),
a custom class is defined for it.
For example, :class:`~montepy.XPlane` represents all :attr:`~montepy.SurfaceType.PX` surfaces by default.
These classes expose the ``surface_constants`` through more intuitive property names like: :attr:`~montepy.XPlane.location`.
See the :doc:`API documentation <../api/modules>` for specific surface classes and their documentation.



Getting Surfaces by Type the Easy Way
--------------------------------------
So there is a convenient way to update a surface, but how do you easily get the surfaces you want?
For instance what if you want to shift a cell up in Z by 10 cm?
It would be horrible to have to get each surface by their number, and hoping you don't change the numbers along the way.

The :class:`~montepy.surface_collection.Surfaces` collection has a generator for every type of surface in MCNP.
These are very easy to find: they are just the lower case version of the
MCNP surface mnemonic.
This previous code is much simpler now:

.. testcode::

    for surface in cell.surfaces.pz:
        surface.location += 10

Setting Boundary Conditions
----------------------------

As discussed in :manual63:`5.3.1`, surfaces can have three boundary conditions:

* Reflective boundary
* Periodic boundary
* White boundary

.. note::

   Several Monte Carlo codes have vacuum boundary conditions as a fourth type.
   In MCNP, a vacuum boundary is defined by a cell with zero importance.
   These are often called the "graveyard".
   Refer to the :ref:`CellImportance` section to see how to set these.

The reflective and white boundary conditions are easiest to set as they are Boolean conditions.
These are controlled by :attr:`~montepy.Surface.is_reflecting` and
:attr:`~montepy.Surface.is_white_boundary` respectively.
For Example:

.. testcode::

   from montepy.surfaces.surface_type import SurfaceType

   bottom = montepy.ZPlane()
   bottom.is_reflecting = True

   cyl = montepy.surfaces.ZCylinder()
   cyl.is_white_boundary = True


Setting a Periodic boundary is slightly more difficult.
In this case the boundary condition must be set to the other periodic surface with :attr:`~montepy.Surface.periodic_surface`.
So to continue with the previous example:

.. testcode::

   bottom.location = 0.0
   bottom.is_reflecting = False

   top = montepy.ZPlane()
   top.location = 1.26

   bottom.periodic_surface = top
