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
The other allowed classes are: ``Exceptions``, :class:`~montepy.mcnp_card.MCNP_Card`, :class:`~montepy.mcnp_problem.MCNP_Problem`, :class:`~montepy.cell.Cell`,
:class:`~montepy.particle.Particle`, and :class:`~montepy.universe.Universe`.
Utility functions are allowed at this level as well.


input_parser
^^^^^^^^^^^^
The :mod:`montepy.input_parser` contains all functions and classes involved in syntax parsing.
Generally this is all invoked through :func:`~montepy.input_parser.input_reader.read_input`,
which returns an :class:`~montepy.mcnp_problem.MCNP_Problem` instance.


data_inputs
^^^^^^^^^^^
This package is for all :class:`~montepy.mcnp_card.MCNP_Card` children that should exist
in the data block in an MCNP input. 
For example :class:`~montepy.data_inputs.material.Material` lives here.

surfaces
^^^^^^^^
This package contains all surface classes.
All classes need to be children of :class:`~montepy.surfaces.surface.Surface`.
When possible new surface classes should combine similar planes.
For example :class:`~montepy.surfaces.axis_plane.AxisPlane` covers ``PX``, ``PY``, and ``PZ``.


Introduction to SLY and Syntax Trees
------------------------------------

In MontePy 0.2.0 the core of MontePy was radically changed. 
A *real* syntax parser was actually used that actually does things like work with a Lexer, and an L-R table.
This parsing engine is `SLY (Sly Lex-Yacc) <https://sly.readthedocs.io/en/latest/>`_.
The parsers used by MontePy are designed to return "syntax trees".
These are based on `Abstract Syntax Tree <https://en.wikipedia.org/wiki/Abstract_syntax_tree>`_, but are not true sytax trees per se.
These trees are not abstract. The white-space, and comment information is preserved.

Example Syntax Tree
^^^^^^^^^^^^^^^^^^^

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
""""""""""""""""

For geometry this syntax tree is a binary tree as well and applies the grouping rules properly to build the 
correct logic into the tree. 
For instance the previous example's geometry::

        1 -2 -3

Would become::
   
         Geometry
            / \
           /   \
          1  & / \
              / & \ 
            -2    -3

Introduction To Data Types
""""""""""""""""""""""""""

A syntax tree consists of a series of instances of various node objects.
All node classes are sub-classes of the :class:`montepy.input_parser.syntax_node.SyntaxNodeBase` class.
The classes are:

* :class:`~montepy.input_parser.syntax_node.SyntaxNode` is one of the most commonly used class, and represents a syntax tree. 
  This is basically a wrapper for a dict (which will be ordered thanks to python 3.8).
* :class:`~montepy.input_parser.syntax_node.ValueNode`  is the most commonly used classes. It represents the leaves of the syntax tree.
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
* :class:`~montepy.input_parser.syntax_node.IsotopesNode` is a node that represents an MCNP style isotope identifier (e.g., ``1001.80c``).

Many of these nodes (which aren't leaves) behave like dicts and lists, and can be accessed with indices. 
For more detail in how to work with them read the next section on MCNP_Objects: :ref:`mcnp-object-docs`.

Inheritance
-----------

There are many abstract or simply parent classes that are designed to be subclassed extensively.

.. _mcnp-object-docs:

Input: :class:`~montepy.mcnp_object.MCNP_Object`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All classes that represent a single input card *must* subclass this. 
For example: some children are: :class:`~montepy.cell.Cell`, :class:`~montepy.surfaces.surface.Surface`.

How to __init__
"""""""""""""""
Your init function signature should be: ``def __init__(self, input)``.
You should then immediately populate default values, and then
call ``super().__init__(input, self._parser)``.
This way if ``super().__init__`` fails, 
there will be enough information for the error reporting to not fail,
when trying to convert the objects to strings.
This will then populate the parameters: ``_tree``, and ``comments``.
Now you should (inside an in if block checking ``input_card``) parse 
``self._tree``.
Classes need to support "from scratch" creation e.g., ``cell = Cell()``.

Working with Parsers, and the Syntax Tree
"""""""""""""""""""""""""""""""""""""""""

The parent class init function requires an instance of a parser object.
Note this is an instance, and not the class itself.
The init function will then run ``parser.parse()``. 
Most objects in MontePy will initialize and keep the parser object at the (MontePy) class level, to reduce overhead.

.. code-block:: python

   class Cell(MCNP_Object):
       # Snip
       _parser = CellParser()
       # snip


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
Even if an input isn't provided a ValueNode needs to be stored. The utility :func:`~montepy.mcnp_object.MCNP_Object._generate_default_node` can help simplify this.

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
   will convert the ValueNode to an integer ValueNode (via :func:`~montepy.input_parser.syntax_node.ValueNode._convert_to_int`).

Next, if you do not need to change the :func:`~montepy.input_parser.syntax_node.ValueNode.type` for the ValueNode, but do not need to markt the ValueNode as negative;
there are methods to handle this.
These methods are :func:`~montepy.input_parser.syntax_node.ValueNode._convert_to_int`, and
:func:`~montepy.input_parser.syntax_node.ValueNode._convert_to_enum`.
``_convert_to_int`` is a rather straight forward function to run, and takes no arguments.
It should be noted that the value is found by running ``int(self.token)``, that is that the original string value, and not the float value is converted.
This is in order to avoid allowing ``1.5`` as a valid int, since in this case the floor would be taken.
``_convert_to_enum`` takes a class instance, which is a subclass of ``Enum``. 
You can specify a ``format_type``, which specifies what the data should be treated as while formatting it with new data.
For example :class:`~montepy.surfaces.surface_type.SurfaceType` (e.g., ``PZ``) uses ``str`` as its format type,
whereas :class:`~montepy.data_inputs.lattice.Lattice` (e.g., ``1`` or ``2``) uses ``int`` is its format type.

How to __str__ vs __repr__
""""""""""""""""""""""""""
All objects must implement ``__str__`` (called by ``str()``), 
and ``__repr__`` (called by ``repr()``).
See `this issue <https://github.com/idaholab/MontePy/issues/82>`_ for a more detailed discussion.
In general ``__str__`` should return a one line string with enough information to uniquely identify the object.
For numbered objects this should include their number, and a few high level details.
For ``__repr__`` this should include debugging information.
This should include most if not all internal state information.

See this example for :class:`~montepy.cell.Cell`

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
"""""""""""""""""""""""""""""""""""""""
MontePy (via :func:`~montepy.mcnp_problem.MCNP_Problem.write_problem`) writes
a class to file path or file handle  by calling its :func:`~montepy.mcnp_object.MCNP_Object.format_for_mcnp_input` method.
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
For instance :class:`~montepy.cell.Cell` will update its material number based on ``self.material.number``,
since the cell object does not control a material's number.
Finally ``self._tree`` is formatted.
Remember ``self._tree`` is a syntax tree of type :class:`~montepy.input_parser.syntax_node.SyntaxNode`.
:func:`~montepy.input_parser.syntax_node.SyntaxNodeBase.format` will create a string based on the syntax tree,
which is updated with the new values that have been provided.
The ValueNode's implementation does most of the heavy lifting here with reverse engineering the user value,
and then replicating that formatting with the new value.


Collection: :class:`~montepy.numbered_object_collection.NumberedObjectCollection`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This should be subclassed for any collection of objects that are numbered.
For example: cells, surfaces, materials, universes, tallies, etc.
By default you need to do almost nothing.
The class that will be added to this collection must have the property ``obj.number``.

How to __init__
"""""""""""""""
Your init signature should be ``def __init__(self, objects=None)``
All you need to then do is call super, 
with the class this will wrap.
For example the init function for ``Cells`` 

.. code-block:: python

        def __init__(self, cells=None):
            super().__init__(montepy.Cell, cells)

Collection: :class:`~montepy.numbered_object_collection.NumberedDataObjectCollection`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This is a subclass of :class:`~montepy.numbered_object_collection.NumberedObjectCollection`,
which is designed for :class:`~montepy.data_inputs.data_input.DataInputAbstract` instances.
It is a wrapper that will ensure that all of its items are also in :func:`~montepy.mcnp_problem.MCNP_Problem.data_inputs`.


Numbered Object :class:`~montepy.numbered_mcnp_object.Numbered_MCNP_Object`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
MCNP allows many types of number objects like cells, surfaces, and tallies. 
The only thing special about this is that it requires there be the properties:
``number`` and ``old_number``.
The ``old_number`` is what was read from the input file, and should not mutate.
The ``number`` is the object's current number and should mutate.
The parent class provides a system to link to a problem via ``self._problem``.
Note this field can be ``None``. 
When setting a number you must check for numbering collisions with the method:
:func:`~montepy.numbered_object_collection.NumberedObjectCollection.check_number`.
This function returns nothing, but will raise an error when a number collision occurs.
For example the ``Surface`` number setter looks like:
        
.. code-block:: python

    @number.setter
    def number(self, number):
        assert isinstance(number, int)
        assert number > 0
        if self._problem:
            self._problem.surfaces.check_number(number)
        self._surface_number = number


Surface: :class:`~montepy.surfaces.surface.Surface`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This is the parent class for all Surface classes.
You will also need to update :func:`~montepy.surfaces.surface_builder.surface_builder`.
You should expose clear parameters such as ``radius`` or ``location``.
``format_for_mcnp_input()`` is handled by default.

How to __init__
"""""""""""""""
After running the super init method
you will then have access to ``self.surface_type``, and ``self.surface_constants``.
You will need to implement a ``_allowed_surface_types`` to specify which surface types are allowed for your class.
You then need to verify that there are the correct number of surface constants. 
You will also need to add a branch in the logic for :func:`montepy.surfaces.surface_builder.surface_builder`.

:func:`~montepy.surfaces.surface.Surface.find_duplicate_surfaces`
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
This function is meant to find very similar surfaces that cause geometry errors,
such as two ``PZ`` surfaces that are 1 micron apart.
This should return a list of surfaces that are within the provided tolerance similar to this one.
Things to consider.

#. The list provided will *not* include ``self``, ``self`` is not considered redundant with regards to ``self``.
#. Surfaces can be modified in many ways including: being periodic with respect to a surface, being transformed, being a periodic surface, and
   being a white surface. To say that two surfaces are duplicate all of these factors must be considered. 


Data Inputs: :class:`~montepy.data_inputs.data_input.DataInputAbstract`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This class is the parent for all inputs that show up in the data block. 
When adding a child you will also need to update the 
:func:`~montepy.data_inputs.data_parser.parse_data` function.
This can be done by adding the class to ``PREFIX_MATCHES``.
In general first comply with standards for this class's parent: :class:`~montepy.mcnp_object.MCNP_Object`.
In addition you will need to implement :func:`~montepy.data_inputs.data_input.DataInputAbstract.update_pointers` 
if you need it.

During init the inputs' "name word" (e.g., ``M3``, ``kcode``, ``f7:n``) is validated and parsed.
Conceptually these names can contain up to four sections.
This information is stored in an instance of :class:`~montepy.input_parser.syntax_node.ClassifierNode`.

#. A ``prefix_modifier`` this modifies the whole card with a special character such as ``*tr5`` 
#. A ``Prefix``, which is a series of letters that identifies the type such as ``m``
#. A ``number``, which numbers it. These must be an unsigned integer.
#. A particle classifier such as ``:n,p``.

You control the parsing behavior through three methods: :func:`~montepy.data_inputs.data_input.DataInputAbstract._class_prefix`, 
:func:`~montepy.data_inputs.data_input.DataInputAbstract._has_number`, 
and :func:`~montepy.data_inputs.data_input.DataInputAbstract._has_classifier`.
See the documentation for how to set these.


Using the :func:`~montepy.data_inputs.data_parser.parse_data` function:
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

The function :func:`~montepy.data_inputs.data_parser.parse_data` handles converting a ``data_input`` to the correct class automatically.
It uses the set ``PREFIX_MATCH`` to do this. 
This lists all classes that the function will look into for a matching class prefix.
Inputs that should not be parsed can have their prefix added to ``VERBOTEN`` in that file.

The ``parse_data`` function will use the ``fast_parse`` option for parsing the data_input.
This method will only match the first word/classifier using the :class:`~montepy.input_parser.data_parser.ClassifierParser`.
Based upon this the function will decide which class to run for a full parse. 
By default all subclasses will use the :class:`~montepy.input_parser.data_parser.DataParser` class.
If you need to use a custom parser you do so by setting ``self._parser``.

How to add an object to :class:`~montepy.mcnp_problem.MCNP_Problem`
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

the :class:`~montepy.mcnp_problem.MCNP_Problem` automatically consumes problem level data inputs,
and adds them to itself.
Cards this would be appropriate for would be things like ``mode`` and ``kcode``. 
To do this it uses the dictionary ``inputs_to_property`` in the ``__load_data_inputs_to_object`` method.
To add a problem level data Object you need to 

#. Add it ``inputs_to_property``. The key will be the object class, and the value will be a string for the attribute it should be loaded to.
#. Add a property that exposes this attribute in a desirable way.


Making a numbered Object :class:`~montepy.numbered_mcnp_object.Numbered_MCNP_Object`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
MCNP allows many types of number objects like cells, surfaces, and tallies. 
First you need to provide the property ``number``, and ``old_number``.
The parent class provides a system to link to a problem via ``self._problem``.
Note this field can be ``None``. 
When setting a number you must check for numbering collisions with the method:
:func:`~montepy.numbered_object_collection.NumberedObjectCollection.check_number`.
This function returns nothing, but will raise an error when a number collision occurs.
For example the ``Surface`` number setter looks like::
        
    @number.setter
    def number(self, number):
        assert isinstance(number, int)
        assert number > 0
        if self._problem:
            self._problem.surfaces.check_number(number)
        self._surface_number = number

Data Cards that Modify Cells :class:`~montepy.data_inputs.cell_modifier.CellModifierInput`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This is a subclass of :class:`~montepy.data_inputs.data_input.DataInputAbstract` that is meant to handle data inputs that specify information about,
and modify cells.
For example ``IMP`` changes the importance of a cell and ``VOL`` specifies its volume.
Both of these are appropriate uses of this class.

This class adds a lot of machinery to handle the complexities of these data inputs,
that is because these data can be specified in the Cell *or* Data block.

How to __init__
"""""""""""""""
Similar to other inputs you need to match the parent signature and run super on it:

.. code-block:: python

    def __init__(self, input=None, in_cell_block=False, key=None, value=None):
             super().__init__(input, in_cell_block, key, value)  

The added arguments add more information for invoking this from a ``Cell``. 
When doing so the ``in_cell_block`` will obviously be true,
and the ``key``, and ``value`` will be taken from the ``parameters`` syntax tree. 
These will all be automatically called from ``Cell`` as discussed below.
Most of the boiler plate will be handled by super. 
The goals for init function should be: 

#. initialize default values needed for when this is initialized from a blank call.
#. Parse the data provided in the ``input``, when ``in_cell_block`` is False.
#. Parse the data given in ``key`` and ``value`` when ``in_cell_block`` is True.


On data Ownership
"""""""""""""""""

Objects that subclass this one will only be owned by ``Cell`` and ``Cells`` objects.
They will only be public properties for ``Cell``.
All "data" must be only in the ``Cell`` level object once the problem has been fully initialized.
This means that the object owned by ``Cells`` should not know the importance of an individual cell,
only the object owned by ``Cell`` should know this.

The general rule is that the ``Cell`` level the object (or some part of it) should be available as a public property.
At the ``Cells`` level the object should be stored in a ``_protected`` attribute.
See more below.


How these objects are added to :class:`~montepy.cell.Cell` and :class:`~montepy.cells.Cells`
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

Due to the number of classes that will ultimately be subclasses of this class,
some automated hooks have been developed.
These hooks use a dictionary and the ``setattr`` function to add multiple objects 
to ``Cell`` or ``Cells`` automatically.

On the Cell level the static dictionary: ``Cell._INPUTS_TO_PROPERTY`` maps how data should be
loaded. 
The key is the class of the object type that should be loaded. 
The value is then a tuple. 
The first element of the tuple is the string of the attribute to where the object of this class should be loaded.
The second element of the tuple is a boolean.
If this boolean is false repeats of this class are allowed and they will be merged.
(e.g., ``IMP:N,P=1 IMP:E=0`` makes sense despite there being two ``IMP`` specified.
If True only one instance of the object is allowed.
(e.g., ``VOL=5 VOL=10`` makes no sense).
For finding which class to use the :func:`~montepy.data_inputs.data_parser.PREFIX_MATCHES` set is used. See above.
The key, value pairs in ``Cell.parameters`` is iterated over. 
If any of the keys is a partial match to the ``PREFIX_MATCHES`` dict then that class is used,
and constructed. 
The new object is then loaded into the ``Cell`` object at the given attribute using ``setattr``.
If your class is properly specified in both dictionaries you should be good to go on the ``Cell`` 
level.
Finally, for objects that are default, and contain no information, a default syntax tree is loaded into the parent ``Cell``'s syntax tree.

At the ``Cells`` level the same dictionary (``Cell._INPUTS_TO_PROPERTY``) is used as well.
This time though it is iterating over ``problem.data_inputs``.
Thanks to ``data_parser`` these objects are already appropriately typed,
and the corresponding object just needs to be loaded into an attribute.
Once again none of these attributes should be exposed through ``@property`` at the ``Cells`` level.

:func:`~montepy.data_inputs.cell_modifier.CellModifierInput.format_for_mcnp_input`
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

For the most part the complexity of switching between the cell and data block printing is automatically handled by this parent function.
In general this looks a lot like the workflow for the base ``format_for_mcnp_input`` implementation.
However, must internal calls are wrapped in another function, allowing overriding of those wrappers to change behavior for more complex situations.
In all cases :func:`~montepy.data_inputs.cell_modifier.CellModifierInput._is_worth_printing` is checked to see if there is information to be printed.
The default implementation checks :func:`~montepy.data_inputs.cell_modifier.CellModifierInput.has_information` for either the cell or cells.

Next the values need to be updated via :func:`~montepy.mcnp_object.MCNP_Object._update_values`.
For the cell level instance this calls :func:`~montepy.data_inputs.cell_modifier.CellModifierInput._update_cell_values`,
which needs to be implemented.
For the data-block isntance this is a bit more complicated.
First all new data for every cell is collected by :func:`~montepy.data_inputs.cell_modifier.CellModifierInput._collect_new_values`.
By default this will get the *ValueNode* that is returned from the abstract method :func:`~montepy.data_inputs.cell_modifier.CellModifierInput._tree_value`.
These values will then be passed to :func:`~montepy.input_parser.syntax_node.ListNode.update_with_new_values`.

Finally, the syntax tree is formatted.
Once again this is wrapped to allow adding more complexity.
The tree is formatted by :func:`~montepy.data_inputs.cell_modifier.CellModifierInput._format_tree`.

:func:`~montepy.data_inputs.cell_modifier.CellModifierInput.merge`
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

This abstract method allows multiple objects of the same type to be combined, 
and one will be consumed by the other.
One use case for this is combining the data from: ``IMP:N,P=1 IMP:E=0.5`` into one object
so there's no redundant data.
This will automatically be called by the loading hooks, and you do not need to worry about
deleting other.
If merging isn't allowed :class:`~montepy.errors.MalformedInputError` should be raised.


:func:`~montepy.data_inputs.cell_modifier.CellModifierInput.push_to_cells`
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

This is how data provided in the data block are provided to the ``Cell`` objects.
There should be a ``self.in_cell_block`` guard.

You need to check that there was no double specifying of data in both the cell and data block.
This should be raise :class:`~montepy.errors.MalformedInputError`.
This checking and error handling is handled by the method :func:`~montepy.data_inputs.cell_modifier.CellModifierInput._check_redundant_definitions`.

:func:`~montepy.data_inputs.cell_modifier.CellModifierInput._clear_data`
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

This method will get called on data block instances.
The goal is to delete any internal data that has already been pushed to the cells
so that if a user goes crazy and somehow access this object they cannot modify the data,
and get into weird end-use behavior.

:func:`~montepy.mcnp_problem.MCNP_Problem.print_in_data_block`
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

There is a flag system for controlling if data are output in the cell block or the data block.
This is controlled by :func:`~montepy.mcnp_problem.MCNP_Problem.print_in_data_block`.
This acts like a dictionary.
The key is the string prefix that mcnp uses but is case insensitive.
So controlling the printing of ``cell.importance`` data is handled by:
``problem.print_in_data_block["IMP"]``.
Most of the work with this property is automated.


Syntax Objects: :class:`~montepy.input_parser.mcnp_input.ParsingNode`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This represents all low level components in MCNP syntax, such as:
Messages, titles, and Inputs. 
Similar to ``MCNP_Object`` you will need to implement ``format_for_mcnp_input``.
In this case though you will not have access the nice helper functions.
You will be responsible for ensuring that you do not exceed the maximum
number of column numbers allowed in a line.

How to __init__
"""""""""""""""
You need to call ``super().__init__(input_lines)``,
and this will provide by ``self.input_lines``.

Parsers: :class:`~montepy.input_parser.parser_base.MCNP_Parser` 
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
See the tokens module: :mod:`montepy.input_parser.tokens` for what tokens are available.
The tokenization process is slightly contextual.
The context is only changed by the :class:`~montepy.input_parser.block_type.BlockType`.
The lexers used are:

* cell block: :class:`~montepy.input_parser.tokens.CellLexer`.
* surface block: :class:`~montepy.input_parser.tokens.SurfaceLexer`.
* data block: :class:`~montepy.input_parser.tokens.DataLexer`.

Most likely you are writing a parser for parsing a complex input in the data block.
You will then be subclassing :class:`montepy.input_parser.data_parser.DataParser`.

On the use of Pointers and Generator
------------------------------------

First you might be saying there are no pointers in python.
There are pointers you just don't see them. 
If these examples aren't clear reach out to one of the core developers.

MontePy abuses pointers a lot. 
This will talk a lot like a Rust reference book about ownership and borrowing.
There aren't true parallels in python though.
In this section ownership is considered the first instance of an object, 
which should basically live for the lifetime of the problem.
For a ``Surface`` it is owned by the ``Surfaces`` collection owned by the ``MCNP_Problem``.
A cell then borrows this object by referencing it in its own ``Surfaces`` collections. 
For example:

.. doctest::

    >>> import montepy
    >>> # owns
    >>> x = montepy.Cell()
    >>> old_id = hex(id(x))
    >>> # borrows
    >>> new_list = [x]
    >>> old_id == hex(id(new_list[0]))
    True

The general principle is that only one-directional pointers should be used,
and bidirectional pointers should never be used.
This is due to the maintenance overhead with mutation.
For instance: a cell knows the surface objects it uses, 
but a surface doesn't always know what cell object uses it. 
This is a one-directional pointer,
if the surfaces did know, this would be bidirectional.

So how do we decide which direction to point?
In general we should default to MCNP. 
So a cell borrows a surface because a cell card in MCNP 
references surface numbers, 
and not vice versa.
The exception to this is the case of inputs that modify another object.
For example the ``MT`` card modifies its parent ``M`` card.
In general the parent object should own its children modifiers.
This is an area of new development, and this may change.

So how do we get a surface to know about the cells it uses? 
With generators!
First, one effectively bi-directional pointer is allowed;
inputs are allowed to point to the parent problem.
This is provided through ``self._problem``, and
is established by: :func:`~montepy.mcnp_object.MCNP_Object.link_to_problem`.
With this the surface can find its cells by::

    @property
    def cells(self):
        if self._problem:
            for cell in self._problem.cells:
                if self in cell.surfaces:
                    yield cell

So why generators and not functions?
This is meant to force the data to be generated on the fly,
so it is tolerant to mutation.
If we were to return a list a user is much more likely to store that,
and use that instead.
If we make it easy to just say::

        if cell in surface.cells:
                pass

Users are more like to use this dynamic code.
In general this philosophy is: if it's not the source of truth,
it should be a generator.

Constants and Meta Data Structures
----------------------------------

MontePy uses constants and data structures to utilize meta-programming
and remove redundant code.
Typical constants can be found in :mod:`montepy.constants`.

Here are the other data structures to be aware of:

* :class:`~montepy.mcnp_problem.MCNP_Problem` ``_NUMBERED_OBJ_MAP``: maps a based numbered object to its collection
  class. This is used for loading all problem numbered object collections in an instance.
* :func:`montepy.data_inputs.data_parser.PREFIX_MATCHES` is a set of the data object classes. The prefix is taken from
  the classes. A data object must be a member of this class for it to automatically parse new data objects.
* :class:`~montepy.cell.Cell` ``_INPUTS_TO_PROPERTY`` maps a cell modifier class to the attribute to load it into for a
  cell.  The boolean is whether multiple input instances are allowed.
