.. meta::
   :description lang=en:
        How to add a new tally type to MontePy: the TallyType member, the Tally subclass, and what to register and implement.

Tallies: :class:`~montepy.Tally`
================================

Every kind of MCNP tally is a :class:`~montepy.TallyType`, identified by its mnemonic, the last digit
of its number, and its modifier (``+``, ``*``, or none), e.g. ``*F4``.
Each kind of tally that scores a different quantity is its own subclass of
:class:`~montepy.Tally`, e.g. :class:`~montepy.CellEnergyFluxTally` for ``*F4``.
Kinds that only differ in units share a class: ``F6`` and ``*F6`` (MeV/g or jerks/g) are both an
:class:`~montepy.EnergyDepositionTally`.

How much work a new tally type is depends on its syntax:

* one that scores over cells or surfaces like the existing ``F`` tallies only needs a
  ``TallyType``, a class, and registering it;
* one with its own syntax, such as detector (``F5``) or mesh tallies, also needs a parser and its
  own implementations of parsing and writing its data.

Adding a Cell or Surface Tally Type
------------------------------------

#. **Add the** :class:`~montepy.TallyType` **member** in ``montepy/data_inputs/tally_type.py``,
   with its units in ``_UNITS``. Every member must have units; a test checks this.

   .. code-block:: python

       CELL_ENERGY_FLUX = _TallyKey("F", 4, "*")
       """.. versionadded:: 1.6.0b4"""

#. **Add a** :class:`~montepy.Score` **member**, if it reports a quantity no existing score
   describes. This is what :attr:`~montepy.Tally.scores` reports when there is no multiplier.

#. **Subclass** :class:`~montepy.CellTally` **or** :class:`~montepy.SurfaceTally`, and set its class
   attributes:

   .. code-block:: python

       class CellEnergyFluxTally(CellTally):
           """``*F4``: cell energy flux tally, in MeV/cm2.

           .. versionadded:: 1.6.0b4
           """

           _TALLY_TYPE = TallyType.CELL_ENERGY_FLUX
           _DEFAULT_SCORES = (Score.ENERGY_FLUX,)

   ``_TALLY_TYPE`` is the type the class is created as from scratch.
   If the new type only differs from an existing class in its units, don't make a new class:
   add the type to that class's ``_OTHER_TALLY_TYPES`` instead, and
   :attr:`~montepy.Tally.tally_units` will switch between them.

   The parent class provides everything else: parsing and writing the scoring bins, the
   ``add_*``/``remove_*`` builders, :attr:`~montepy.CellTally.cells` or
   :attr:`~montepy.SurfaceTally.surfaces`, linking to the problem and to an ``FM`` input, and
   :meth:`~montepy.Tally.clone_as` conversions to other tallies of the same parent class.

#. **Register the type in** ``_TALLY_TYPE_MAP`` at the bottom of ``montepy/data_inputs/tally.py``.
   :meth:`~montepy.Tally.from_input` uses it to pick the class for an input.
   A test checks that every ``TallyType`` is mapped to a class that lists it.

#. **Export and document the class**:

   * import it in ``montepy/__init__.py``;
   * add it to the Tallies ``autosummary`` in ``doc/source/api/modules.rst``;
   * add a row for it to the table of tally types in ``doc/source/guide/tallies.rst``.

   The shorthand aliases (e.g. ``montepy.F4Tally``) are only for the plain and ``+`` types; don't
   add one for others.

#. **Add tests** to ``tests/test_tally.py``: that its input dispatches to the class with the right
   ``tally_type``, ``tally_units``, and ``scores``, and is written back unchanged; and add the class
   to the parametrized list in ``TestTallyBuilders.test_from_scratch_classifier_formatting``.

Adding a Tally with Its Own Syntax
-----------------------------------

A tally that doesn't score over a list of cells or surfaces, such as a detector (``F5``),
radiography (``FIP``/``FIR``/``FIC``), or mesh (``FMESH``/``TMESH``) tally, needs more.
The steps above still apply, except that the class subclasses :class:`~montepy.Tally` directly.

Parsing
^^^^^^^

:class:`~montepy.input_parser.tally_parser.TallyParser` only parses scoring bins.
Write a parser for the new syntax in ``montepy/input_parser/``, and return it from the class's
``_parser()`` static method.
Its tree should keep the ``"data"`` node layout of a tally (``tree["data"]["tally"]`` and
``tree["data"]["end"]``) if the base class's total flag handling is to be reused.

Dispatch
^^^^^^^^

:func:`~montepy.data_inputs.data_parser.parse_data` sends every input with the ``F`` prefix to
:meth:`~montepy.Tally.from_input`, which picks the class from ``_TALLY_TYPE_MAP``.

* ``F5`` inputs are currently kept out of this: ``parse_data`` reads them, and ``FM`` inputs for
  them, as plain data inputs (``tally._is_detector_input``), and ``Tally._dispatch_class`` raises
  :class:`~montepy.exceptions.UnsupportedFeature` for them. Remove both when adding ``F5``.
* A tally with another mnemonic has another prefix. Override ``_class_prefix()``, and add the class
  to ``DATA_CLASSES`` in ``montepy/data_inputs/data_parser.py`` (and remove the prefix from
  ``VERBOTEN``, as for ``fmesh``).

Since it is a :class:`~montepy.Tally`, the problem adds it to :attr:`~montepy.MCNP_Problem.tallies`,
and links an ``FM`` input with the same number to it.

Methods to Implement
^^^^^^^^^^^^^^^^^^^^

The base class assumes a tally's data is its list of scoring bins
(:attr:`~montepy.Tally.groups`). Override these for the new data:

``_init_blank``
    Call ``super()._init_blank()``, then set the default values of the new data.
``_parse_tally_body``
    Parse the new data from ``self._tree``. The base implementation parses the scoring bins and the
    total flag.
``_update_values``
    Write the new data back into ``self._tree`` before it is formatted. The base implementation
    writes the classifier's modifier, the scoring bins, and the total flag.
``_generate_default_tree``
    If a new tally's default tree should have a different ``"data"`` node.
``__contains__``
    What ``in`` means for the new tally, if anything.
``link_to_problem``
    If the new data refers to other objects in the problem, such as cells or materials. Call
    ``super().link_to_problem(problem, deepcopy=deepcopy)`` first.
``_tally_category``
    :meth:`~montepy.Tally.clone_as` only converts between tallies of the same category: the
    classes listed in ``Tally._tally_category``. Add the new base class there if its subclasses
    should convert among each other.

Properties for the new data should follow the usual patterns (see :ref:`jit-parsing`), e.g.
``@needs_full_ast`` getters.
