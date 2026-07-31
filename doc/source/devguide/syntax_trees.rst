.. meta::
   :description lang=en:
        How MontePy uses SLY (Sly Lex-Yacc) to parse MCNP inputs into syntax trees, and how to subclass the parser infrastructure.

Introduction to SLY and Syntax Trees
=====================================

In MontePy 0.2.0 the core of MontePy was radically changed.
A *real* syntax parser was actually used that actually does things like work with a Lexer, and an L-R table.
This parsing engine is `SLY (Sly Lex-Yacc) <https://sly.readthedocs.io/en/latest/>`_.
The parsers used by MontePy are designed to return "syntax trees".
These are based on `Abstract Syntax Tree <https://en.wikipedia.org/wiki/Abstract_syntax_tree>`_, but are not true sytax trees per se.
These trees are not abstract. The white-space, and comment information is preserved.

Example Syntax Tree
-------------------

Let's look at a typical cell definition::

        1 10 -5.0 1 -2 -3 IMP:N=1 Vol 5.0

This can be broken into large chunks by their type of information

+-------------+-----------------+----------+---------------------+-------------+-------------+
|                                  High-level                                                |
+=============+=================+==========+=====================+=============+=============+
| Cell Number | Material Definition        | Geometry Definition | Parameters                |
+-------------+-----------------+----------+---------------------+-------------+-------------+
| ``1``       | ``10 -5.0``                | ``1 -2 -3``         | ``IMP:N=1 Vol 5.0``       |
+-------------+-----------------+----------+---------------------+-------------+-------------+
| Cell Number | Material Number | Density  | Geometry Definition | Importance  |   Volume    |
+-------------+-----------------+----------+---------------------+-------------+-------------+
| ``1``       | ``10``          | ``-5.0`` | ``1 -2 -3``         | ``IMP:N=1`` | ``Vol 5.0`` |
+-------------+-----------------+----------+---------------------+-------------+-------------+

This example shows the first-and-a-half levels of the syntax tree for a Cell.
This structure does break down a bit further.

Geometry Example
^^^^^^^^^^^^^^^^

For geometry this syntax tree is a binary tree as well and applies the grouping rules properly to build the
correct logic into the tree.
For instance the previous example's geometry::

        1 -2 -3

Would become::

         Geometry
            / \
           /   \
          1  & / \
              / &
            -2    -3

Introduction to Data Types
^^^^^^^^^^^^^^^^^^^^^^^^^^^

A syntax tree consists of a series of instances of various node objects.
All node classes are sub-classes of the :class:`montepy.input_parser.syntax_node.SyntaxNodeBase` class.
The classes are:

* :class:`~montepy.input_parser.syntax_node.SyntaxNode` is one of the most commonly used class, and represents a syntax tree.
  This is basically a wrapper for a dict (which will be ordered thanks to python 3.8).
* :class:`~montepy.input_parser.syntax_node.ValueNode` is the most commonly used classes. It represents the leaves of the syntax tree.
  It is meant to hold a single value, both its semantic value and its text representation, and its surrounding white-space (and comments), or padding.
* :class:`~montepy.input_parser.syntax_node.PaddingNode` is the companion to the ``ValueNode``. It encapsulates all following padding for a value.
  Padding is considered to be white-space or a comment (:class:`~montepy.input_parser.syntax_node.CommentNode`).
* :class:`~montepy.input_parser.syntax_node.ListNode` is a node meant to contain a list of arbitrary length of values.
* :class:`~montepy.input_parser.syntax_node.ShortcutNode` is a helper to a ``ListNode`` for when MCNP shortcuts (e.g., ``1 10r``) are used.
  They are nested inside of a ``ListNode`` and should be mostly transparent to the user and developer.
* :class:`~montepy.input_parser.syntax_node.ParametersNode` is a node to hold the parameters for an input.
  The parameters are the key-value pairs that can come at the end of most inputs.
* :class:`~montepy.input_parser.syntax_node.GeometryTree` is a node for holding the binary trees for the CSG set logic for a cell's geometry definition.
  It is the most recursive data structure of any of these nodes.
* :class:`~montepy.input_parser.syntax_node.ClassifierNode` is a node to represent the data classification "word" that describes what the data are for.
  For example for a material it would contain ``M34``. For a cell importance it could be ``imp:n``.
  It can contain: a data keyword, a number, a particle designator (:class:`~montepy.input_parser.syntax_node.ParticleNode`), and a modifier character (e.g., ``*`` in ``*TR5``).
* :class:`~montepy.input_parser.syntax_node.MaterialsNode` is a node that represents an MCNP style isotope identifier (e.g., ``1001.80c``).

Many of these nodes (which aren't leaves) behave like dicts and lists, and can be accessed with indices.
For more detail in how to work with them read the next section on MCNP_Objects: :ref:`mcnp-object-docs`.

Syntax Objects: :class:`~montepy.input_parser.mcnp_input.ParsingNode`
-----------------------------------------------------------------------

This represents all low level components in MCNP syntax, such as:
Messages, titles, and Inputs.
Similar to ``MCNP_Object`` you will need to implement ``format_for_mcnp_input``.
In this case though you will not have access the nice helper functions.
You will be responsible for ensuring that you do not exceed the maximum
number of column numbers allowed in a line.

How to ``__init__``
^^^^^^^^^^^^^^^^^^^
You need to call ``super().__init__(input_lines)``,
and this will provide by ``self.input_lines``.

Parsers: :class:`~montepy.input_parser.parser_base.MCNP_Parser`
-----------------------------------------------------------------

This is the base class for all parsers in MontePy.
It is a wrapper for a :class:`sly.Parser` instance.
It has had to implement some janky metaclass properties in order to allow subclassing.

.. warning::

        The new subclassing system breaks the SLY magic that allows function overloading (multiple function definitions with the same name),
        when subclassed.
        So if you define a new function with the same name as from the parent class it will hide the parent implementation,
        and will likely break a lot of things.

First, read the `SLY Documentation <https://sly.readthedocs.io/en/latest/sly.html#writing-a-parser>`_.
You should also be aware of the tokens that are available.
See the tokens module: ``montepy.input_parser.tokens`` for what tokens are available.
The tokenization process is slightly contextual.
The context is only changed by the :class:`~montepy.input_parser.block_type.BlockType`.
The lexers used are:

* cell block: :class:`~montepy.input_parser.tokens.CellLexer`.
* surface block: :class:`~montepy.input_parser.tokens.SurfaceLexer`.
* data block: :class:`~montepy.input_parser.tokens.DataLexer`.

Most likely you are writing a parser for parsing a complex input in the data block.
You will then be subclassing :class:`montepy.input_parser.data_parser.DataParser`.
