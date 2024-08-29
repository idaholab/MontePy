.. _migrate 0 1:

Migration plan for MontePy 1.0.0
================================

.. meta::
   :description: Foo bar

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


New Interface
-------------
Currently the replacement interface has not been fully designed yet.
If you have input you can `join the discussion <https://github.com/idaholab/MontePy/discussions/475>`_.
There will also be some alpha-testing announced in that discussion.

Once MontePy 1.0.0 is released this will be updated with information about the new interface,
and how to migrate to it.
