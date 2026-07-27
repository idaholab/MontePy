.. meta::
   :description lang=en:
        This guide provides details on how MontePy works,
        and guidance on how to make contributions.
        MontePy is the most user-friendly Python library for reading, editing, and writing MCNP input files.

Developer's Reference
=====================

MontePy can be thought of as having two layers: the syntax, and the semantic layers.
The syntax layers handle the boring syntax things: like multi-line cards, and comments, etc.
The semantic layer takes this information and makes sense of it, like what the material number in a cell card is.

.. note::

   Punchcards are dead.
   For this reason MontePy refrains from using antiquated terminology like "cards" and "decks".
   Instead MontePy refers to "inputs", and "files" or "problems".

.. note::
   Demo code is based on `tests/inputs/test.imcnp`.
   You can load this with:

    .. testcode::

        import montepy
        problem = montepy.read_input("tests/inputs/test.imcnp")



Package Structure
-----------------

Top Level
^^^^^^^^^
The top level of the package is reserved for only a select few objects.
All children of :class:`~montepy.numbered_object_collection.NumberedObjectCollection` can live here.
The other allowed classes are: ``Exceptions``, :class:`~montepy.mcnp_object.MCNP_Object`, :class:`~montepy.MCNP_Problem`, :class:`~montepy.Cell`,
:class:`~montepy.particle.Particle`, and :class:`~montepy.Universe`.
Utility functions are allowed at this level as well.


input_parser
^^^^^^^^^^^^
The ``montepy.input_parser`` contains all functions and classes involved in syntax parsing.
Generally this is all invoked through :func:`~montepy.input_parser.input_reader.read_input`,
which returns an :class:`~montepy.MCNP_Problem` instance.


data_inputs
^^^^^^^^^^^
This package is for all :class:`~montepy.mcnp_object.MCNP_Object` children that should exist
in the data block in an MCNP input.
For example :class:`~montepy.Material` lives here.

surfaces
^^^^^^^^
This package contains all surface classes.
All classes need to be children of :class:`~montepy.Surface`.
Nearly all classes that are necessary are now implemented.

.. toctree::
   :maxdepth: 2

   devguide/type_enforcement
   devguide/jit_parsing
   devguide/syntax_trees
   devguide/mcnp_object
   devguide/collections_dev
   devguide/cell_modifier
   devguide/pointers_generators

