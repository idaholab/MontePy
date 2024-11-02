.. _migrate 0 1:

Migration plan for MontePy 1.0.0
================================

.. meta::
   :description: Migration plan for moving from MontePy 0.x to MontePy 1.0.0

Necessity
---------

The MCNP 6.2 and 6.3 manuals are ambiguously worded around whether nuclides can be repeated in a material definition.
Due to this the authors of MontePy in MontePy 0.x.x assumed that repeated nuclides were not allowed.
Due to this assumption material composition data were stored in  python dictionary,
where the keys were the nuclide and their library.
Due to this if duplicate nuclides are present only the last instance of that nuclide will have its information preserved in the model.
This is clearly not a desired outcome.

However, it has been confirmed that  duplicate nuclides are allowed in MCNP,
and can be advantageous. 
See :issue:`504` for more details.
Due to this it was decided that the best way forward was to abandon the old design,
and to create a brand new data structure.
This means that backwards compatibility *will* be broken, 
and so this fix is leading to a major version release.


Deprecations
------------
The following properties and objects are currently deprecated, 
and will be removed in MontePy 1.0.0.

* :func:`montepy.data_inputs.material.Material.material_components`. 
  This is the dictionary that caused this design problem. 

* :class:`montepy.data_inputs.material_components.MaterialComponents`
  This is the class that stores information in the above dictionary. 
  It is largely excess object wrapping, that makes the material interface 
  overly complex.

* :class:`montepy.data_inputs.Isotope` will be renamed to ``Nuclide``. 
  This is to better align with MCNP documentation,
  and better reflect that the nuclear data for a nuclide can represent 
  isotopic, isomeric, or atomic data.


New Interface & Migration
-------------------------

.. note::

        This design is not finalized and is subject to change.
        This is the currently planned design for ``1.0.0a1``.
        If you have input you can `join the discussion <https://github.com/idaholab/MontePy/discussions/475>`_.
        This is alos where alpha-testing will be announced.

``material_components`` removal
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Material composition data has moved from ``Material.material_components`` to the ``Material`` itself.
``Material`` is now a list-like iterable.
It is a list of tuples which are ``(nuclide, fraction)`` pairs.

.. testcode::
   :skipif: True # avoid running on < 1.0.0

   >>> import montepy 
   >>> problem = montepy.read_input("tests/inputs/test.imcnp")
   >>> mat = problem.materials[1]
   >>> mat[0]
   (Nuclide('92235.80c'), 5)
   >>> mat[1]
   (Nuclide('92238.80c'), 95)

Searching Components
^^^^^^^^^^^^^^^^^^^^

Finding a specific ``Nuclide`` in a ``Material`` is now much easier.
First there will be a ``Material.find`` method that takes either a ``Nuclide`` string,
or various over search criteria (e.g., ``element``),
and creates a generator of all matching component tuples.

If you want to check if a ``Material`` contains a specific ``Nuclide``
you can simply test ``nuclide in material``.
The ``Material.contains`` function will provide more options,
such as setting a minimum threshold, and testing for multiple nuclides at once.

Adding Nuclides
^^^^^^^^^^^^^^^
Adding a new nuclide will be easiest with the ``add_nuclide`` function.

Editing Nuclide Compositon
^^^^^^^^^^^^^^^^^^^^^^^^^^
Editing a material composition will be very similar to editing a ``list``.
Existing components can be set to a nuclide component nuclide.
Also existing components can be deleted with ``del``. 


``Isotope`` Deprecation and Removal
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The decision was made to remove the name ``Isotope``.
This is because not all material components are an isotope,
they may be an isomer, or event an element.
Rather the MCNP generalized terminology of ``Nuclide`` was adopted.
The idea of a specific nuclide, e.g., ``H-1`` was separated from an
MCNP material component e.g., ``1001.80c``. 
The actual ``Nuclide`` information was moved to a new class: ``Nucleus``,
that is immutable. 
The ``Nuclide`` wraps this and adds a ``Library`` object to specify the nuclear data that is used.
It makes sense to be able to change a library.
It does not make sense to change the intrinsic properties of a nuclide (i.e., ``Z``, ``A``, etc.).
