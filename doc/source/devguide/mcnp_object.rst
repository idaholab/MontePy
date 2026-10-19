.. meta::
   :description lang=en:
        How to subclass MCNP_Object in MontePy: init, syntax tree access, str/repr, and formatting for MCNP input.

.. _mcnp-object-docs:

Input: :class:`~montepy.mcnp_object.MCNP_Object`
=================================================

All classes that represent a single input *must* subclass this.
For example: some children are: :class:`~montepy.Cell`, :class:`~montepy.Surface`.

How to ``__init__``
-------------------

Most subclasses should **not** define a custom ``__init__``.
The base class ``MCNP_Object.__init__`` handles both from-scratch creation and
input parsing (including JIT parsing).
Instead, subclasses implement three hook methods that the base ``__init__`` calls:

* :meth:`~montepy.mcnp_object.MCNP_Object._init_blank` — called first, before any parsing.
  Initialize every internal attribute to a safe default value here.
  This ensures that even a partially-constructed object can still be converted
  to a string for error reporting.

* :meth:`~montepy.mcnp_object.MCNP_Object._parse_tree` — called after a full parse has
  occurred (i.e., ``self._tree`` is populated).
  Extract semantic values from the syntax tree and store them as internal attributes.

* :meth:`~montepy.mcnp_object.MCNP_Object._generate_default_tree` — called when no
  ``input`` argument is provided (from-scratch creation, e.g., ``Cell()``).
  Build a default syntax tree and store it in ``self._tree``.
  Use ``self._generate_default_node(type, default_value)`` for individual leaf nodes.
  Any keyword arguments passed to ``__init__`` beyond ``input`` and ``jit_parse``
  are forwarded here via ``**kwargs``.

If you need a custom ``__init__`` (e.g., to add extra constructor arguments), match
the parent signature and delegate to ``super().__init__``:

.. code-block:: python

    @args_checked
    def __init__(self, input: InitInput = None, *, number: ty.PositiveInt = None,
                 jit_parse: bool = True):
        super().__init__(input, jit_parse=jit_parse, number=number)

Classes need to support "from scratch" creation, e.g., ``cell = Cell()``.

Working with Parsers and the Syntax Tree
-----------------------------------------

Each subclass must implement the abstract ``@staticmethod`` ``_parser()``, which must
return a **new parser instance** each time it is called:

.. code-block:: python

   class MyInput(MCNP_Object):

       @staticmethod
       def _parser():
           return MyFullParser()

       _JitParser = MyJitParser

``_JitParser`` is a companion class attribute for just-in-time parsing (see
:ref:`jit-parsing`).
It should be set to the lightweight JIT parser class for this object.
If ``_JitParser`` is not defined and JIT parsing is requested, the ``AttributeError``
is caught and the object automatically falls back to a full parse.

If the input was parsed correctly the syntax tree returned will be stored in ``self._tree``.
If not the errors will be raised automatically.
The top of the tree will always be an instance of :class:`~montepy.input_parser.syntax_node.SyntaxNode`.
This will behave like a dictionary, and can be acessed by their keys::

        self._number = self._tree["cell_number"]

Almost all leaves on the trees will be instances of :class:`~montepy.input_parser.syntax_node.ValueNode`.
This has many support functions that you should not try to implement yourself.
The actual semantic values are stored in ``node.value``, for instance the float value for a float ValueNode.
This property can be set, and should be.

You should not store the nested value; instead you should store the entire ValueNode in a private attribute,
and then use :func:`~montepy.utilities.make_prop_val_node` to provide the appropriate property.
Even if an input isn't provided a ValueNode needs to be stored. The utility :meth:`~montepy.mcnp_object.MCNP_Object._generate_default_node` can help simplify this.

The parsers can't always know what data type should in a specific position, so largely it treats all numerical values as floats.
This should be changed during the init so the value_nodes are the correct data type.
First: if the sign of the value (positive/negative) carries information beyond the value being negative, this should be marked.
For instance, on a cell the density can be positive or negative depending on if it's atom or mass density.
This doesn't mean the density is negative.
To mark this set the :func:`~montepy.input_parser.syntax_node.ValueNode.is_negatable_float` to ``True`` for floats,
and :func:`~montepy.input_parser.syntax_node.ValueNode.is_negatable_identifier` for integers.
This will make it so that ``value`` always returns a positive value, and so :func:`~montepy.input_parser.syntax_node.ValueNode.is_negative` returns a boolean value.

.. note::

   Setting :func:`~montepy.input_parser.syntax_node.ValueNode.is_negatable_identifier` to ``True``
   will convert the ValueNode to an integer ValueNode (via :meth:`~montepy.input_parser.syntax_node.ValueNode.convert_to_int`).

Next, if you do not need to change the :func:`~montepy.input_parser.syntax_node.ValueNode.type` for the ValueNode, but do not need to markt the ValueNode as negative;
there are methods to handle this.
These methods are :meth:`~montepy.input_parser.syntax_node.ValueNode.convert_to_int`, and
:meth:`~montepy.input_parser.syntax_node.ValueNode.convert_to_enum`.

``convert_to_int`` is a rather straight forward function to run, and takes no arguments.
It should be noted that the value is found by running ``int(self.token)``, that is that the original string value, and not the float value is converted.
This is in order to avoid allowing ``1.5`` as a valid int, since in this case the floor would be taken.
``convert_to_enum`` takes a class instance, which is a subclass of ``Enum``.
You can specify a ``format_type``, which specifies what the data should be treated as while formatting it with new data.
For example :class:`~montepy.SurfaceType` (e.g., ``PZ``) uses ``str`` as its format type,
whereas :class:`~montepy.data_inputs.lattice.LatticeType` (e.g., ``1`` or ``2``) uses ``int`` is its format type.

How to ``__str__`` vs ``__repr__``
------------------------------------
All objects must implement ``__str__`` (called by ``str()``),
and ``__repr__`` (called by ``repr()``).
See `this issue <https://github.com/idaholab/MontePy/issues/82>`_ for a more detailed discussion.
In general ``__str__`` should return a one line string with enough information to uniquely identify the object.
For numbered objects this should include their number, and a few high level details.
For ``__repr__`` this should include debugging information.
This should include most if not all internal state information.

See this example for :class:`~montepy.Cell`

.. doctest::
   :skipif: True # skip because multi-line doc tests are kaputt

    >>> cell = problem.cells[2]
    >>> print(str(cell))
    CELL: 2, mat: 2, DENS: 8.0 atom/b-cm
    >>> print(repr(cell))
    CELL: 2
    MATERIAL: 2, ['iron']
    density: 8.0 atom/b-cm
    SURFACE: 1005, RCC
    SURFACE: 1015, CZ
    SURFACE: 1020, PZ
    SURFACE: 1025, PZ

Writing to File (Format for MCNP Input)
-----------------------------------------
MontePy (via :func:`~montepy.MCNP_Problem.write_problem`) writes
a class to file path or file handle by calling its :func:`~montepy.mcnp_object.MCNP_Object.format_for_mcnp_input` method.
This must return a list of strings that faithfully represent this objects state, and tries to replicate the user formatting.
Each string in the list represents one line in the MCNP input file to be written.

For most cases the default implementation should work great.
This is its implementation:

.. code-block:: python

    def format_for_mcnp_input(self, mcnp_version):
        self.validate()
        self._update_values()
        return self.wrap_string_for_mcnp(self._tree.format(), mcnp_version, True)

The first call is to :func:`~montepy.mcnp_object.MCNP_Object.validate`, which is meant to check for illegal states
caused by partially created objects the user hasn't completed yet.
Next the abstract method, :func:`~montepy.mcnp_object.MCNP_Object._update_values` is called.
This function updates the syntax tree with current values.
Most values should not need to be updated, since their value is linked to a ValueNode, which is pointed to and modified by the object.
This should only really by used to update information controlled by other objects.
For instance :class:`~montepy.Cell` will update its material number based on ``self.material.number``,
since the cell object does not control a material's number.
Finally ``self._tree`` is formatted.
Remember ``self._tree`` is a syntax tree of type :class:`~montepy.input_parser.syntax_node.SyntaxNode`.
:func:`~montepy.input_parser.syntax_node.SyntaxNodeBase.format` will create a string based on the syntax tree,
which is updated with the new values that have been provided.
The ValueNode's implementation does most of the heavy lifting here with reverse engineering the user value,
and then replicating that formatting with the new value.
