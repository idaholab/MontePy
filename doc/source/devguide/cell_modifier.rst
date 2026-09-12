.. meta::
   :description lang=en:
        How to implement CellModifierInput subclasses in MontePy for data inputs that modify cells.

Data Inputs that Modify Cells: :class:`~montepy.data_inputs.cell_modifier.CellModifierInput`
============================================================================================
This is a subclass of :class:`~montepy.data_inputs.data_input.DataInputAbstract` that is meant to handle data inputs that specify information about,
and modify cells.
For example ``IMP`` changes the importance of a cell and ``VOL`` specifies its volume.
Both of these are appropriate uses of this class.

This class adds a lot of machinery to handle the complexities of these data inputs,
that is because these data can be specified in the Cell *or* Data block.

How to ``__init__``
--------------------
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


On Data Ownership
------------------

Objects that subclass this one will only be owned by ``Cell`` and ``Cells`` objects.
They will only be public properties for ``Cell``.
All "data" must be only in the ``Cell`` level object once the problem has been fully initialized.
This means that the object owned by ``Cells`` should not know the importance of an individual cell,
only the object owned by ``Cell`` should know this.

The general rule is that the ``Cell`` level the object (or some part of it) should be available as a public property.
At the ``Cells`` level the object should be stored in a ``_protected`` attribute.
See more below.


How These Objects are Added to :class:`~montepy.Cell` and :class:`~montepy.Cells`
-----------------------------------------------------------------------------------

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
For finding which class to use the ``PREFIX_MATCHES`` set is used. See above.
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
-------------------------------------------------------------------------------------

For the most part the complexity of switching between the cell and data block printing is automatically handled by this parent function.
In general this looks a lot like the workflow for the base ``format_for_mcnp_input`` implementation.
However, must internal calls are wrapped in another function, allowing overriding of those wrappers to change behavior for more complex situations.
In all cases :func:`~montepy.data_inputs.cell_modifier.CellModifierInput._is_worth_printing` is checked to see if there is information to be printed.
The default implementation checks :func:`~montepy.data_inputs.cell_modifier.CellModifierInput.has_information` for either the cell or cells.

Next the values need to be updated via :func:`~montepy.mcnp_object.MCNP_Object._update_values`.
For the cell level instance this calls :func:`~montepy.data_inputs.cell_modifier.CellModifierInput._update_cell_values`,
which needs to be implemented.
For the data-block isntance this is a bit more complicated.
First all new data for every cell is collected by :meth:`~montepy.data_inputs.cell_modifier.CellModifierInput._collect_new_values`.
By default this will get the *ValueNode* that is returned from the abstract method :meth:`~montepy.data_inputs.cell_modifier.CellModifierInput._tree_value`.
These values will then be passed to :meth:`~montepy.input_parser.syntax_node.ListNode.update_with_new_values`.

Finally, the syntax tree is formatted.
Once again this is wrapped to allow adding more complexity.
The tree is formatted by :meth:`~montepy.data_inputs.cell_modifier.CellModifierInput._format_tree`.

:func:`~montepy.data_inputs.cell_modifier.CellModifierInput.merge`
--------------------------------------------------------------------

This abstract method allows multiple objects of the same type to be combined,
and one will be consumed by the other.
One use case for this is combining the data from: ``IMP:N,P=1 IMP:E=0.5`` into one object
so there's no redundant data.
This will automatically be called by the loading hooks, and you do not need to worry about
deleting other.
If merging isn't allowed :exc:`~montepy.exceptions.MalformedInputError` should be raised.


:func:`~montepy.data_inputs.cell_modifier.CellModifierInput.push_to_cells`
-----------------------------------------------------------------------------

This is how data provided in the data block are provided to the ``Cell`` objects.
There should be a ``self.in_cell_block`` guard.

You need to check that there was no double specifying of data in both the cell and data block.
This should be raise :exc:`~montepy.exceptions.MalformedInputError`.
This checking and error handling is handled by the method :meth:`~montepy.data_inputs.cell_modifier.CellModifierInput._check_redundant_definitions`.

:func:`~montepy.data_inputs.cell_modifier.CellModifierInput._clear_data`
--------------------------------------------------------------------------

This method will get called on data block instances.
The goal is to delete any internal data that has already been pushed to the cells
so that if a user goes crazy and somehow access this object they cannot modify the data,
and get into weird end-use behavior.

:attr:`~montepy.MCNP_Problem.print_in_data_block`
---------------------------------------------------

There is a flag system for controlling if data are output in the cell block or the data block.
This is controlled by :attr:`~montepy.MCNP_Problem.print_in_data_block`.
This acts like a dictionary.
The key is the string prefix that mcnp uses but is case insensitive.
So controlling the printing of ``cell.importance`` data is handled by:
``problem.print_in_data_block["IMP"]``.
Most of the work with this property is automated.
