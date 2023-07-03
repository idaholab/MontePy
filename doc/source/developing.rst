Developer's Guide
=================

MCNPy can be thought of as having two layers: the syntax, and the semantic layers.
The syntax layers handle the boring syntax things: like multi-line inputs, and comments, etc.
The semantic layer takes this information and makes sense of it, like what the material number in a cell card is.

.. note::
   Punchcards are dead.
   For this reason MCNPy refrains from using antiquated terminology like "cards" and "decks".
   Instead MCNPy refers to "inputs", and "files" or "problems". 

Contributing
------------

Here is a getting started guide to contributing. 
If you have any questions Micah and Travis are available to give input and answer your questions.

Setting up and Typical Development Workflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Clone the repository.

#. Install the required packages. 
   MCNPy comes with two requirements files. 
   One (``requirements/common.txt``) is for packages MCNPy depends on.
   The other (``requirements/dev.txt``) is for packages that are generally necessary for developing.
   To install these simply run: 
   
   ``pip install -r requirements/dev.txt``

#. Tie your work to an issue. All work on MCNPy is tracked through issues. 
   If you are working on a new feature or bug that is not covered by an issue, please file an issue first.

#. Work on a new branch. The branches: ``develop`` and ``main`` are protected. 
   All new code must be accepted through a merge request. 
   The easiest way to make this branch is to "create merge request" from gitlab.
   This will create a new branch (though with an unwieldy name) that you can checkout and work on.

#. Run the test cases. MCNPy relies heavily on its over 200 tests for the development process.
   These are configured so if you run: ``python -m pytest`` from the root of the git repository 
   all tests will be found and ran.

#. Develop test cases. This is especially important if you are working on a bug fix.
   A merge request will not be accepted until it can be shown that a test case can replicate the 
   bug and does in deed fail without the bug fix in place.
   To achieve this, it is recommended that you commit the test first, and push it to gitlab.
   This way there will be a record of the CI pipeline failing that can be quickly reviewed as part of the merge request.

   Though MCNPy uses ``pytest`` for running the tests,
   it actually uses `unittest <https://docs.python.org/3/library/unittest.html>`_ for setting up all test fixtures. 
   Generally unit tests of new features go in the test file with the closest class name. 
   Integration tests have all been dumped in ``tests/test_integration.py``. 
   For integration tests you can likely use the ``tests/inputs/test.imcnp`` input file.
   This is pre-loaded as an :class:`~mcnpy.mcnp_problem.MCNP_Problem` stored as: ``self.simple_problem``.
   If you need to mutate it at all you must first make a ``copy.deepcopy`` of it.

#. Write the code.

#. Document all new classes and functions. MCNPy uses `Sphinx docstrings <https://sphinx-rtd-tutorial.readthedocs.io/en/latest/docstrings.html>`_.

#. Format the code with ``black``. You can simply run ``black mcnpy tests``

#. Add more test cases as necessary. The merge request should show you the code coverage.
   The general goal is near 100\% coverage.

#. Update the documentation. Read the "Getting Started" guide and the "Developer's Guide", and see if any information there should be updated.
   If you expect the feature to be commonly used it should be mentioned in the getting started guide.
   Otherwise just the docstrings may suffice.
   Another option is to write an example in the "Tips and Tricks" guide.

#. Update the version, and authors as necessary. The version is stored in ``mcnpy/__init__.py``. See the version numbering system described in ``README.md``.
   The authors information is in ``AUTHORS`` and ``mcnpy/__init__.py``. 

#. Start a merge request review. Generally Micah or Travis are good reviewers.


Deploy Process
^^^^^^^^^^^^^^
MCNPy currently does not use a continuous deploy process.
Rather changes are staged on the ``develop`` branch prior to a release.
Both ``develop`` and ``main`` are protected branches.
``main`` should only be used for releases.
If someone clones ``main`` they will get the most recent official release.
Only a select few core-developers are allowed to approve a merge to ``main`` and therefore a new release.
``develop`` should be production quality code that has been approved for release,
but is waiting on the next release.
So all new features and bug fixes must first be merged onto ``develop``. 

The expectation is that features once merged onto ``develop`` are stable,
well tested, well documented, and well-formatted.

Merge Checklist
^^^^^^^^^^^^^^^

Here are some common issues to check before approving a merge request.

#. If this is a bug fix did the new testing fail without the fix?
#. Was the version number incremented?
#. Were the authors and credits properly updated?
#. Check also the authors in ``mcnpy/__init__.py``
#. Is this merge request tied to an issue?

Package Structure
-----------------

Top Level 
^^^^^^^^^
The top level of the package is reserved for only a select few objects.
All children of :class:`~mcnpy.numbered_object_collection.NumberedObjectCollection` can live here.
The other allowed classes are: ``Exceptions``, :class:`~mcnpy.mcnp_card.MCNP_Card`, :class:`~mcnpy.mcnp_problem.MCNP_Problem`, :class:`~mcnpy.cell.Cell`,
:class:`~mcnpy.particle.Particle`, and :class:`~mcnpy.universe.Universe`.
Utility functions are allowed at this level as well.


input_parser
^^^^^^^^^^^^
The :mod:`mcnpy.input_parser` contains all functions and classes involved in syntax parsing.
Generally this is all invoked through :func:`~mcnpy.input_parser.input_reader.read_input`,
which returns an :class:`~mcnpy.mcnp_problem.MCNP_Problem` instance.


data_inputs
^^^^^^^^^^^
This package is for all :class:`~mcnpy.mcnp_card.MCNP_Card` children that should exist
in the data block in an MCNP input. 
For example :class:`~mcnpy.data_inputs.material.Material` lives here.

surfaces
^^^^^^^^
This package contains all surface classes.
All classes need to be children of :class:`~mcnpy.surfaces.surface.Surface`.
When possible new surface classes should combine similar planes.
For example :class:`~mcnpy.surfaces.axis_plane.AxisPlane` covers ``PX``, ``PY``, and ``PZ``.

Design Philosophy
-----------------
#. **Do Not Repeat Yourself (DRY)**
#. Use abstraction and inheritance smartly.
#. Use ``_private`` fields mostly. Use ``__private`` for very private things that should never be touched.
#. Use ``@property`` getters, and if needed setters. Setters must verify and clean user inputs. For the most part use :func:`~mcnpy.utilities.make_prop_val_node`, and :func:`~mcnpy.utilities.make_prop_pointer`.
#. Fail early and politely. If there's something that might be bad: the user should get a helpful error as
   soon as the error is apparent. 
#. Test. test. test. The goal is to achieve 100% test coverage. Unit test first, then do integration testing. A new feature merge request will ideally have around a dozen new test cases.
#. Do it right the first time. 
#. Document all functions.
#. Expect everything to mutate at any time.
#. Avoid relative imports when possible. Use top level ones instead: e.g., ``import mcnpy.cell.Cell``.
#. Defer to vanilla python, and only use the standard library. Currently the only dependencies are ``numpy`` and ``sly``. 
   There must be good justification for breaking from this convention and complicating things for the user.

Style Guide
-----------
#. Use ``black`` to autoformat all code.
#. Spaces for indentation, tabs for alignment. Use spaces to build python syntax (4 spaces per level), and tabs for aligning text inside of docstrings.


Inheritance
-----------

There are many abstract or simply parent classes that are designed to be subclassed extensively.

Card: :class:`~mcnpy.mcnp_object.MCNP_Object`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All classes that represent a single input card *must* subclass this. 
For example: some children are: :class:`~mcnpy.cell.Cell`, :class:`~mcnpy.surfaces.surface.Surface`.

How to __init__
"""""""""""""""
Your init function signature should be: ``def __init__(self, input_card=None, comment=None)``.
You should then immediately populate default values, and then
call ``super().__init__(input_card, comment)``.
This way if ``super().__init__`` fails, 
there will be enough information for the error reporting to not fail,
when trying to convert the objects to strings.
This will then populate the parameters: ``input_card``, ``words``, and ``comment``.
Now you should (inside an in if block checking ``input_card``) parse 
self.words.
New classes need to support "from scratch" creation e.g., ``cell = Cell()``.

.. note::
   This system will be changed drastically with 0.2.0.

How to __str__ vs __repr__
""""""""""""""""""""""""""""
All objects must implement ``__str__`` (called by ``str()``), 
and ``__repr__`` (called by ``repr()``).
See `this issue <https://hpcgitlab.hpc.inl.gov/experiment_analysis/mcnpy/-/issues/41>`_ for a more detailed discussion.
In general ``__str__`` should return a one line string with enough information to uniquely identify the object.
For numbered objects this should include their number, and a few high level details.
For ``__repr__`` this should include debugging information.
This should include most if not all internal state information.

See this example for :class:`~mcnpy.cell.Cell`

>>> str(cell)
CELL: 2, mat: 2, DENS: 8.0 g/cm3
>>> repr(cell)
CELL: 2
MATERIAL: 2, ['iron']
density: 8.0 atom/b-cm
SURFACE: 1005, RCC


Mutation
""""""""
MCNPy supports copying the exact input unless an object changes at all,
which is inconvenient.
This is handled by ``self._mutated``. 
Whenever an object parameter is set the setter must set ``self._mutated=True``. 

.. note::
   This system will be removed in 0.2.0

Format for MCNP Input
"""""""""""""""""""""
All children must implement this abstract method.
This is the method for how :func:`~mcnpy.mcnp_problem.MCNP_Problem.write_to_file` writes
this class to the file.
It must return a list of strings that faithfully represent this objects state.
Each string in the list represents one line in the MCNP input file to be written.

First if ``self._mutated = False`` the ``input_lines`` must be parroted out.
This can be mostly handled by the helper: ``self._format_for_mcnp_unmutated(mcnp_version)``.
Note you must check if any of the objects that affect this one are mutated as well.
For example a cell must check if its surfaces has changed, because it's likely that
the surface's number has changed.

You have three helper functions to achieve this end goal. 
You should not try to count the number of characters in a line!
These are :func:`~mcnpy.mcnp_card.MCNP_Card.format_for_mcnp_input`,
:func:`~mcnpy.mcnp_card.MCNP_Card.wrap_words_for_mcnp`,
and :func:`~mcnpy.mcnp_card.MCNP_Card.wrap_string_for_mcnp`.
First you need to store a list from ``super().format_for_mcnp_input``.
This function will handle adding comments, etc.
If you don't care about the formatting just create a list of strings,
representing each word in order that MCNP requires, 
and pass this to ``self.wrap_words_for_mcnp``.
If you care more about formatting create the string for each line you desire.
Then pass these strings through ``self.wrap_string_for_mcnp``,
which will then wrap any long lines to ensure it doesn't break MCNP.

Example taken from :class:`~mcnpy.data_inputs.mode.Mode`

.. code-block:: python

    def format_for_mcnp_input(self, mcnp_version):
        if self._mutated:
            ret = super().format_for_mcnp_input(mcnp_version)
            ret.append("MODE")
            for particle in self.particles:
                ret.append(particle.value)
        else:
            ret = self._format_for_mcnp_unmutated(mcnp_version)

        return ret


Collection: :class:`~mcnpy.numbered_object_collection.NumberedObjectCollection`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This should be subclassed for any collection of objects that will are numbered.
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
            super().__init__(mcnpy.Cell, cells)

Numbered Object :class:`~mcnpy.numbered_mcnp_object.Numbered_MCNP_Object`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
MCNP allows many types of number objects like cells, surfaces, and tallies. 
The only thing special about this is that it requires there be the properties:
``number`` and ``old_number``.
The ``old_number`` is what was read from the input file, and should not mutate.
The ``number`` is the object's current number and should mutate.
The parent class provides a system to link to a problem via ``self._problem``.
Note this field can be ``None``. 
When setting a number you must check for numbering collisions with the method:
:func:`~mcnpy.numbered_object_collection.NumberedObjectCollection.check_number`.
This function returns nothing, but will raise an error when a number collision occurs.
For example the ``Surface`` number setter looks like::
        
    @number.setter
    def number(self, number):
        assert isinstance(number, int)
        assert number > 0
        if self._problem:
            self._problem.surfaces.check_number(number)
        self._mutated = True
        self._surface_number = number


Surface: :class:`~mcnpy.surfaces.surface.Surface`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This is the parent class for all Surface classes.
You will also need to update :func:`~mcnpy.surfaces.surface_builder.surface_builder`.
You should expose clear parameters such as ``radius`` or ``location``.
``format_for_mcnp_input()`` is handled by default.

How to __init__
"""""""""""""""
This is very similar to how ``MCNP_Card`` works. 
You need to first run ``super().__init__(input_card, comment)``.
You will then have access to ``self.surface_type``, and ``self.surface_constants``.
You then need to verify that the surface type is correct, and there are the correct number of surface constants. 

:func:`~mcnpy.surfaces.surface.Surface.find_duplicate_surfaces`
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
This function is meant to find very similar surfaces that cause geometry errors,
such as two ``PZ`` surfaces that are 1 micron apart.
This should return a list of surfaces that are within the provided tolerance similar to this one.
Things to consider.

#. The list provided will include ``self``, ``self`` is not considered redundant with regards to ``self``.
#. Surfaces can be modified in many ways including: being periodic with respect to a surface, being transformed, being a periodic surface, and
   being a white surface. To say that two surfaces are duplicate all of these factors must be considered. 


Data Inputs: :class:`~mcnpy.data_inputs.data_input.DataInputAbstract`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This class is the parent for all inputs that show up in the data block. 
When adding a child you will also need to update the 
:func:`~mcnpy.data_inputs.data_parser.parse_data` function.
In general first comply with standards for this class's parent: :class:`~mcnpy.mcnp_card.MCNP_Card`.
In addition you will need to implement :func:`~mcnpy.data_inputs.data_input.DataInputAbstract.update_pointers` 
if you need it.

During init the inputs' "name word" (e.g., ``M3``, ``kcode``, ``f7:n``) is validated and parsed.
Conceptually these names can contain up to four sections.

#. A ``prefix_modifier`` this modifies the whole card with a special character such as ``*tr5`` 
#. A ``Prefix``, which is a series of letters that identifies the type such as ``m``
#. A ``number``, which numbers it. These must be an unsigned integer.
#. A particle classifier such as ``:n,p``.

You control the parsing behavior through three parameters: ``class_prefix``, ``has_number``, and ``has_classifier``.
See the documentation for how to set these.


Using the :func:`~mcnpy.data_inputs.data_parser.parse_data` function:
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

The function :func:`~mcnpy.data_inputs.data_parser.parse_data` handles converting a ``data_card`` to the correct class automatically.
It uses the dictionary ``PREFIX_MATCH`` to do this. 
This maps the prefix describes above to a specific class.


How to add an object to :class:`~mcnpy.mcnp_problem.MCNP_Problem`
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

the :class:`~mcnpy.mcnp_problem.MCNP_Problem` automatically consumes problem level data inputs,
and adds them to itself.
Cards this would be appropriate for would be things like ``mode`` and ``kcode``. 
To do this it uses the dictionary ``inputs_to_property`` in the ``__load_data_inputs_to_object`` method.
To add a problem level data Object you need to 

#. Add it ``inputs_to_property``. The key will be the object class, and the value will be a string for the attribute it should be loaded to.
#. Add a property that exposes this attribute in a desirable way.

Making a numbered Object :class:`~mcnpy.numbered_mcnp_object.Numbered_MCNP_Object`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
MCNP allows many types of number objects like cells, surfaces, and tallies. 
First you need to provide the property ``number``, and ``old_number``.
The parent class provides a system to link to a problem via ``self._problem``.
Note this field can be ``None``. 
When setting a number you must check for numbering collisions with the method:
:func:`~mcnpy.numbered_object_collection.NumberedObjectCollection.check_number`.
This function returns nothing, but will raise an error when a number collision occurs.
For example the ``Surface`` number setter looks like::
        
    @number.setter
    def number(self, number):
        assert isinstance(number, int)
        assert number > 0
        if self._problem:
            self._problem.surfaces.check_number(number)
        self._mutated = True
        self._surface_number = number

Data Cards that Modify Cells :class:`~mcnpy.data_inputs.cell_modifier.CellModifierInput`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This is a subclass of :class:`~mcnpy.data_inputs.data_input.DataInputAbstract` that is meant to handle data inputs that specify information about,
and modify cells.
For example ``IMP`` changes the importance of a cell and ``VOL`` specifies its volume.
Both of these are appropriate uses of this class.

This class adds a lot of machinery to handle the complexities of these data inputs,
that is because these data can be specified in the Cell *or* Data block.

How to __init__
"""""""""""""""
Similar to other inputs you need to match the parent signature and run super on it ::

        def __init__(self, input_card=None, comments=None, in_cell_block=False, key=None, value=None):
             super().__init__(input_card, comments, in_cell_block, key, valuei)  

The added arguments add more information for invoking this from a ``Cell``. 
When doing so the ``in_cell_block`` will obviously be true,
and the ``key``, and ``value`` will be taken from the ``parameters`` dict. 
These will all be automatically called from ``Cell`` as discussed below.
Most of the boiler plate will be handled by super. 
The goals for init function should be: 

#. initialize default values needed for when this is initialized from a blank call.
#. Parse the data provided in the ``input_card``, when ``in_cell_block`` is False.
#. Parse the data given in ``key`` and ``value`` when ``in_cell_block`` is True.


On data Ownership
"""""""""""""""""
Objects that subclass this one will only be owned by ``Cell`` and ``Cells`` objects.
They will only be public properties for ``Cell``.
All "data" must be only in the ``Cell`` level object once the problem has been fully initialized.
This means that the object owned by ``Cells`` should not know the importance of an individual cell,
only the object owned by ``Cell`` should be.

The general rule is that the ``Cell`` level the object (or some part of it) should be available as a public property.
At the ``Cells`` level the object should be stored in a ``_protected`` attribute.
See more below.


How these objects are added to :class:`~mcnpy.cell.Cell` and :class:`~mcnpy.cells.Cells`
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
Due to the number of classes that will ultimately be subclasses of this class,
some automated hooks have been developed.
These hooks use a dictionary and the ``setattr`` function to add multiple objects 
to ``Cell`` or ``Cells`` automatically.

On the Cell level the static dictionary: ``Cell._CARDS_TO_PROPERTY`` maps how data should be
loaded. 
The key is the class of the object type that should be loaded. 
The value is then a tuple. 
First element is the string of the attribute to where the object of this class should be loaded.
The second element is a boolean.
If this boolean is false repeats of this object are allowed and they will be merged.
(e.g., ``IMP:N,P=1 IMP:E=0`` makes sense despite there being two ``IMP`` specified.
If True only one instance of the object is allowed.
(e.g., ``VOL=5 VOL=10`` makes no sense).
For finding which class to use the :func:`~mcnpy.data_inputs.data_parser.PREFIX_MATCHES` dict is used. See above.
The key, value pairs in ``Cell.parameters`` is iterated over. 
If any of the keys is a partial match to the ``PREFIX_MATCHES`` dict then that class is used,
and constructed. 
The new object is then loaded into the ``Cell`` object at the given attribute using ``setattr``.
If your class is properly specified in both dictionaries you should be good to go on the ``Cell`` 
level.

At the ``Cells`` level the same dictionary (``Cell._CARDS_TO_PROPERTY``) is used as well.
This time though it is iterating over ``problem.data_inputs``.
Thanks to ``data_parser`` these objects are already appropriately typed,
and the corresponding object just needs to be loaded into an attribute.
Once again none of these attributes should be exposed through ``@property``.

``format_for_mcnp_input``
"""""""""""""""""""""""""
This implementation gets a bit more complicated.
Now you must handle being called as either at the ``Cell`` or data block level.

So how will you know the difference? 
Use the property ``self.in_cell_block``. 
This will be True if this instance is owned by a ``Cell``.

For the cell case the goal is to return one or more lines that can be added to the overall cell
input.
In this case the method will only be called if the ``Cell`` has mutated,
so you do not need to check for self mutation in this case.
This means that this will *not* be the first line in this case. ::

    1 0 
         -1
         c this was generated by Importance object
         IMP:N,P=1
         IMP:E=0

For the data_block case the output should be a complete MCNP input that stands on its own.
You should check ``self.has_changed_print_style`` to help determine if the output has mutated.
Next you also need to check the modifier object owned by every cell for if any of them have mutated.
See the :class:`~mcnpy.data_inputs.universe_input.UniverseInput` implementation for an example.

For printing in the data block though you need to remember that this object being called will have no data.
You will need to iterate over: ``self._problem.cells`` and retrieve the data from there.
You may find the new function: :func:`~mcnpy.mcnp_object.MCNP_Object.compress_repeat_values` helpful.

``merge``
"""""""""
This abstract method allows multiple objects of the same type to be combined, 
and one will be consumed by the other.
One use case for this is combining the data from: ``IMP:N,P=1 IMP:E=0.5`` into one object
so there's no redundant data.
This will automatically be called by the loading hooks, and you do not need to worry about
deleting other.

``push_to_cells``
"""""""""""""""""
This is how data provided in the data block are provided to the ``Cell`` objects.
There should be a ``self.in_cell_block`` guard.

You need to check that there was no double specifying of data in both the cell and data block.
This should raise :class:`~mcnpy.errors.MalformedInputError`.
This checking and error handling is handled by the method ``self._check_redundant_definitions()``.

``_clear_data``
""""""""""""""""
This method will get called on data block instances.
The goal is to delete any internal data that has already been pushed to the cells
so that if a user goes crazy and somehow access this object they cannot modify the data,
and get into weird end-use behavior.

``problem.print_in_data_block``
"""""""""""""""""""""""""""""""
There is a flag system for controlling if data are output in the cell block or the data block.
This is controlled by :func:`~mcnpy.mcnp_problem.MCNP_Problem.print_in_data_block`.
This acts like a dictionary.
The key is the string prefix that mcnp uses but is case insensitive.
So controlling the printing of ``cell.importance`` data is handled by:
``problem.print_in_data_block["IMP"]``.
Most of the work with this property is automated.


Syntax Objects: :class:`~mcnpy.input_parser.mcnp_input.MCNP_Input`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This represents all low level components in MCNP syntax, such as:
Comments, Messages, titles, and Cards. 
Similar to ``MCNP_Object`` you will need to implement ``format_for_mcnp_input``.
In this case though you will not have access the nice helper functions.
You will be responsible for ensuring that you do not exceed the maximum
number of column numbers allowed in a line.

How to __init__
"""""""""""""""
You need to call ``super().__init__(input_lines)``,
and this will provide by ``self.input_lines``.

On the use of Pointers and Generator
------------------------------------

First you might be saying there are no pointers in python.
There are pointers you just don't see them. 
If these examples aren't clear reach out to one of the core developers.

MCNPy abuses pointers a lot. 
This will talk a lot like a Rust reference book about ownership and borrowing.
There aren't true parallels in python though.
In this section ownership is considered the first instance of an object, 
which should basically live for the lifetime of the problem.
For a ``Surface`` it is owned by the ``Surfaces`` collection owned by the ``MCNP_Problem``.
A cell then borrows this object by referencing it in its own ``Surfaces`` collections. 
For example:

>>> # owns
>>> x = Cell()
>>> hex(id(x))
'0x7f4c6c89dc30'
>>> # borrows
>>> new_list = [x]
>>> hex(id(new_list[0]))
'0x7f4c6c89dc30'

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
is established by: :func:`~mcnpy.mcnp_object.MCNP_Object.link_to_problem`.
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

