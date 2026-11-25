.. meta::
   :description lang=en:
        How to implement collections, numbered objects, surfaces, and data inputs in MontePy.

Collections and Numbered Objects
==================================

Collection: :class:`~montepy.numbered_object_collection.NumberedObjectCollection`
-----------------------------------------------------------------------------------
This should be subclassed for any collection of objects that are numbered.
For example: cells, surfaces, materials, universes, tallies, etc.
By default you need to do almost nothing.
The class that will be added to this collection must have the property ``obj.number``.

How to ``__init__``
^^^^^^^^^^^^^^^^^^^^
Your init signature should be ``def __init__(self, objects=None)``
All you need to then do is call super,
with the class this will wrap.
For example the init function for ``Cells``

.. code-block:: python

        def __init__(self, cells=None):
            super().__init__(montepy.Cell, cells)

Collection: :class:`~montepy.numbered_object_collection.NumberedDataObjectCollection`
---------------------------------------------------------------------------------------
This is a subclass of :class:`~montepy.numbered_object_collection.NumberedObjectCollection`,
which is designed for :class:`~montepy.data_inputs.data_input.DataInputAbstract` instances.
It is a wrapper that will ensure that all of its items are also in :attr:`~montepy.MCNP_Problem.data_inputs`.


Numbered Object: :class:`~montepy.numbered_mcnp_object.Numbered_MCNP_Object`
------------------------------------------------------------------------------
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


Surface: :class:`~montepy.Surface`
------------------------------------
This is the parent class for all Surface classes.
You will also need to update :func:`~montepy.surfaces.surface_builder.parse_surface`.
You should expose clear parameters such as ``radius`` or ``location``.
``format_for_mcnp_input()`` is handled by default.

How the Classes are Built
^^^^^^^^^^^^^^^^^^^^^^^^^^

All of the children of :class:`~montepy.Surface` use the ``montepy.surfaces.surface._SurfaceClassFactory`` metaclass.
This takes a ``spec`` that is of type ``_SurfaceTypeSpec``,
which then contains a list of ``_SurfaceParamSpec`` instances.
The metaclass then adds the given ``_SurfaceParamSpec`` as properties to the class,
and handles ensuring that the data is properly loaded during parsing.
For more details see the current implementations of existing classes as examples.


Data Inputs: :class:`~montepy.data_inputs.data_input.DataInputAbstract`
-------------------------------------------------------------------------
This class is the parent for all inputs that show up in the data block.
When adding a child you will also need to update the
:func:`~montepy.data_inputs.data_parser.parse_data` function.
This can be done by adding the class to ``PREFIX_MATCHES``.
In general first comply with standards for this class's parent: :class:`~montepy.mcnp_object.MCNP_Object`.
If you need to link objects after parsing (e.g. resolving number references to objects), override :meth:`~montepy.mcnp_object.MCNP_Object._parse_tree`.

During init the inputs' "name word" (e.g., ``M3``, ``kcode``, ``f7:n``) is validated and parsed.
Conceptually these names can contain up to four sections.
This information is stored in an instance of :class:`~montepy.input_parser.syntax_node.ClassifierNode`.

#. A ``prefix_modifier`` this modifies the whole input with a special character such as ``*tr5``
#. A ``Prefix``, which is a series of letters that identifies the type such as ``m``
#. A ``number``, which numbers it. These must be an unsigned integer.
#. A particle classifier such as ``:n,p``.

You control the parsing behavior through three methods: :func:`~montepy.data_inputs.data_input.DataInputAbstract._class_prefix`,
:func:`~montepy.data_inputs.data_input.DataInputAbstract._has_number`,
and :func:`~montepy.data_inputs.data_input.DataInputAbstract._has_classifier`.
See the documentation for how to set these.


Using the :func:`~montepy.data_inputs.data_parser.parse_data` Function
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The function :func:`~montepy.data_inputs.data_parser.parse_data` handles converting a ``data_input`` to the correct class automatically.
It uses the set ``PREFIX_MATCH`` to do this.
This lists all classes that the function will look into for a matching class prefix.
Inputs that should not be parsed can have their prefix added to ``VERBOTEN`` in that file.

The ``parse_data`` function will use the ``fast_parse`` option for parsing the data_input.
This method will only match the first word/classifier using the :class:`~montepy.input_parser.data_parser.ClassifierParser`.
Based upon this the function will decide which class to run for a full parse.
By default all subclasses will use the :class:`~montepy.input_parser.data_parser.DataParser` class.
If you need to use a custom parser you do so by setting ``self._parser``.

How to Add an Object to :class:`~montepy.MCNP_Problem`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :class:`~montepy.MCNP_Problem` automatically consumes problem level data inputs,
and adds them to itself.
Inputs this would be appropriate for would be things like ``mode`` and ``kcode``.
To do this it uses the dictionary ``inputs_to_property`` in the ``__load_data_inputs_to_object`` method.
To add a problem level data Object you need to

#. Add it ``inputs_to_property``. The key will be the object class, and the value will be a string for the attribute it should be loaded to.
#. Add a property that exposes this attribute in a desirable way.


Making a Numbered Object: :class:`~montepy.numbered_mcnp_object.Numbered_MCNP_Object`
----------------------------------------------------------------------------------------
MCNP allows many types of number objects like cells, surfaces, and tallies.
First you need to provide the property ``number``, and ``old_number``.
The parent class provides a system to link to a problem via ``self._problem``.
Note this field can be ``None``.
When setting a number you must check for numbering collisions with the method:
:func:`~montepy.numbered_object_collection.NumberedObjectCollection.check_number`.
This function returns nothing, but will raise an error when a number collision occurs.
