.. meta::
   :description lang=en:
        Working with MCNP materials in MontePy: nuclides, components, libraries, finding, and mixing.

.. _mat_tutorial:

Materials
=========

.. testsetup:: *

   import montepy
   problem = montepy.read_input("tests/inputs/test.imcnp")
   mat = problem.materials[1]

Materials are how the nuclide concentrations in cells are specified.
MontePy has always supported materials, but since version 1.0.0,
the design of the interface has significantly improved.

Specifying Nuclides
-------------------

To specify a material, one needs to be able to specify the nuclides that are contained in it.
This is done through :class:`~montepy.Nuclide` objects.
This actually a wrapper of a :class:`~montepy.Nucleus` and a :class:`~montepy.Library` object.
Users should rarely need to interact with the latter two objects, but it is good to be aware of them.
The general idea is that a ``Nuclide`` instance represents a specific set of ACE data that for a ``Nucleus``,
which represents only a physical nuclide with a given ``Library``.

The easiest way to specify a Nuclide is by its string name.
MontePy supports all valid MCNP ZAIDs for MCNP 6.2, and MCNP 6.3.0.
See :class:`~montepy.Nuclide` for how metastable isomers are handled.
However, ZAIDs (like many things in MCNP) are cumbersome.
Therefore, MontePy also supports its own nuclide names as well, which are meant to be more intuitive.
These are very similar to the names introduced with MCNP 6.3.1 (section 1.2.2): this follows:

.. code-block::

   Nn[-A][mS][.library]

Where:

* ``Nn`` is the atomic symbol of the nuclide, case insensitive. This is required.
* ``A`` is the atomic mass. Zero-padding is not needed. Optional.
* ``S`` is the metastable isomeric state. Only states 1 - 4 are allowed. Optional.
* ``library`` is the library extension of the nuclide. This only supports MCNP 6.2, 6.3 formatting, i.e., 2 - 3 digits followed by a single letter. Optional.

The following are all valid ways to specify a nuclide:

.. doctest::

   >>> import montepy
   >>> montepy.Nuclide("1001.80c")
   Nuclide('H-1.80c')
   >>> montepy.Nuclide("H-1.80c")
   Nuclide('H-1.80c')
   >>> montepy.Nuclide("H-1.710nc")
   Nuclide('H-1.710nc')
   >>> montepy.Nuclide("H")
   Nuclide('H-0')
   >>> montepy.Nuclide("Co-60m1")
   Nuclide('Co-60m1')
   >>> montepy.Nuclide("Co")
   Nuclide('Co-0')


.. note::

   The new SZAID and Name syntax for nuclides introduced with MCNP 6.3.1 is not currently supported by MontePy.
   This support likely will be added soon, but probably not prior to MCNP 6.3.1 being available on RSICC.


Working with Material Components
---------------------------------

Iterating over Material Components
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Materials are list-like iterables of tuples.

.. testcode::

    mat = problem.materials[1]

    for comp in mat:
        print(comp)

This shows:

.. testoutput::

    (Nuclide('U-235.80c'), 5.0)
    (Nuclide('U-238.80c'), 95.0)

If you need just the nuclide or just the fractions, these are accessible by:
:attr:`~montepy.Material.nuclides` and
:attr:`~montepy.Material.values`, respectively.

.. testcode::

    for nuclide in mat.nuclides:
        print(repr(nuclide))
    for fraction in mat.values:
        print(fraction)

shows:

.. testoutput::

    Nuclide('U-235.80c')
    Nuclide('U-238.80c')
    5.0
    95.0

Updating Components of Materials
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Materials are also list-like in that they are settable by index.
The material must always be set to a tuple of a nuclide and a fraction.

For instance:

.. testcode::

    nuclide = mat[0][0]
    mat[0] = (nuclide, 4.0)

Generally this is pretty clunky, so
:attr:`~montepy.Material.nuclides` and
:attr:`~montepy.Material.values` are also settable.
To undo the previous changes:

.. testcode::

    mat.values[0] = 5.0
    print(mat[0])

This outputs:

.. testoutput::

    (Nuclide('U-235.80c'), 5.0)

Adding Components to a Material
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To add components to a material use either
:func:`~montepy.Material.add_nuclide`, or
:func:`~montepy.Material.append`.
:func:`~montepy.Material.add_nuclide` is generally the easier method to use.
It accepts a nuclide or the name of a nuclide, and its fraction.

.. note::

    When adding a new component it is not possible to change whether the fraction is in atom fraction
    or mass fraction.
    This is settable through :attr:`~montepy.Material.is_atom_fraction`.

.. testcode::

    mat.add_nuclide("B-10.80c", 1e-6)
    for comp in mat:
        print(comp)

.. testoutput::

    (Nuclide('U-235.80c'), 5.0)
    (Nuclide('U-238.80c'), 95.0)
    (Nuclide('B-10.80c'), 1e-06)


Libraries
---------

MCNP nuclear data comes pre-packaged in multiple different libraries that come from different nuclear data sources
(e.g., ENDF/B-VIII.0),
at different temperatures,
and for different data needs, e.g., neutron data vs. photo-atomic data.
For more details see `LA-UR-17-20709 <https://www.osti.gov/biblio/1342828>`_, or
`LANL's nuclear data libraries <https://nucleardata.lanl.gov/>`_.

All :class:`~montepy.Nuclide` have a :attr:`~montepy.Nuclide.library`,
though it may be just ``""``.
These can be manually set for each nuclide.
If you wish to change all of the components in a material to use the same library you can use
:func:`~montepy.Material.change_libraries`.

MCNP has a precedence system for determining which library use in a specific instance.
This precedence order is:

#. The library specified with the nuclide e.g., ``80c`` in ``1001.80c``.
#. The library specified as default for the material e.g., ``nlib = 80c``.
#. The library specified as default in the default material, ``M0``.
#. The first matching entry in the ``XSDIR`` file.

.. note::

    MontePy currently does not support reading an ``XSDIR`` file. It will not provide information for
    that final step.

Which library will be used for a given nuclide, material, and problem can be checked with:
:func:`~montepy.Material.get_nuclide_library`.

.. seealso::

    * :manual63:`5.6.1`
    * :manual62:`108`


Finding Materials and Nuclides
-------------------------------

Next, we will cover how to find if

* a nuclide is in a material
* multiple nuclides are in a material
* a range of nuclides (e.g., transuranics) is in a material
* specific materials are in a problem.

Check if Nuclide in Material
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

First, you can test if a :class:`~montepy.Nuclide`
(or :class:`~montepy.Nucleus`, or :class:`~montepy.Element`, or ``str``),
is in a material.
This is generally interpreted broadly rather than explicitly.
For instance, if the test nuclide has no library this will match
for all libraries, not just the empty library.
Similarly, an elemental nuclide, e.g., ``H-0``, will match all nuclides based
on the element, not just the elemental nuclide.

.. doctest::

    >>> montepy.Nuclide('H-1.80c') in mat
    False
    >>> montepy.Element(92) in mat
    True
    >>> "U-235" in mat
    True
    >>> "U-235.70c" in mat
    False
    >>> montepy.Nuclide("B-0") in mat
    True

For more complicated checks there is the :func:`~montepy.Material.contains_all`, and
:func:`~montepy.Material.contains_any`.
These functions take a plurality of nuclides as well as a threshold.
The function ``contains_all`` returns ``True`` if and only if the material contains *all* nuclides
with a fraction above the threshold.
The function ``contains_any`` returns ``True`` if any of the material contains *any* nuclides
with a fraction above the threshold.

.. doctest::

    >>> mat.contains_all("H-1.80c")
    False
    >>> mat.contains_all("U-235", "U-238", threshold=1.0)
    True
    >>> mat.contains_all("U-235.80c", "B-10")
    True
    >>> mat.contains_all("U-235.80c", "B-10", threshold=1e-3)
    False
    >>> mat.contains_all("H-1.80c", "U-235.80c")
    False
    >>> mat.contains_any("H-1.80c", "U-235.80c")
    True

Finding Nuclides
^^^^^^^^^^^^^^^^

Often you may need to only work a subset of the components in a material.
:func:`~montepy.Material.find`.
This returns a Generator of the index of the matching component, and then the component tuple.

.. testcode::

    # find all uraium nuclides
    for idx, (nuclide, fraction) in mat.find("U"):
        print(idx, nuclide, fraction)

.. testoutput::

    0  U-235   (80c) 5.0
    1  U-238   (80c) 95.0

There are also other fancy ways to pass slices, for instance to find all transuranics.
See the examples in :func:`~montepy.Material.find` for more details.

There is a related function as well :func:`~montepy.Material.find_vals`,
which accepts the same arguments but only returns the matching fractions.
This is great for instance to calculate the heavy metal fraction of a fuel:

.. testcode::

    # get all heavy metal fractions
    hm_fraction = sum(mat.find_vals(element=slice(90,None))) # slice is requires an end value to accept a start
    print(hm_fraction)

Shows:

.. testoutput::

    100.0

Finding Materials
^^^^^^^^^^^^^^^^^

There are a lot of cases where you may want to find specific materials in a problem,
for instance getting all steels in a problem.
This is done with the function :func:`~montepy.Materials.get_containing_all`
of :class:`~montepy.Materials`.
It takes the same arguments as :func:`~montepy.Material.contains_all`
previously discussed.

Mixing Materials
----------------

Commonly materials are a mixture of other materials.
For instance a good idea for defining structural materials might be to create a new material for each element,
that adds the naturally occurring nuclides of the element,
and then mixing those elements together to make steel, zircaloy, etc.
This mixing is done with :func:`~montepy.Materials.mix`.
Note this is a method of ``Materials`` and not ``Material``.

.. note::

    Materials can only be combined if they are all atom fraction or mass fraction.

.. note::

    The materials being mixed will be normalized prior to mixing (the original materials are unaffected).

.. testcode::

    mats = problem.materials
    h2o = montepy.Material()
    h2o.number = 1
    h2o.add_nuclide("1001.80c", 2.0)
    h2o.add_nuclide("8016.80c", 1.0)

    boric_acid = montepy.Material()
    boric_acid.number = 2
    for nuclide, fraction in {
        "1001.80c": 3.0,
        "B-10.80c": 1.0 * 0.189,
        "B-11.80c": 1.0 * 0.796,
        "O-16.80c": 3.0
    }.items():
        boric_acid.add_nuclide(nuclide, fraction)

    # boric acid concentration
    boron_conc = 100e-6 # 100 ppm
    borated_water = mats.mix([h2o, boric_acid], [1 - boron_conc, boron_conc])
