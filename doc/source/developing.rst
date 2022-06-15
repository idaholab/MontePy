Developer's Guide
=================

MCNPy can be thought of as having two layers: the syntax, and the semantic layers.
The syntax layers handle the boring syntax things: like multi-line cards, and comments, etc.
The semantic layer takes this information and makes sense of it, like what the material number in a cell card is.

Package Structure
-----------------

Top Level 
^^^^^^^^^
The top level of the package is reserved for only a select few objects.
All children of :class:`mcnpy.numbered_object_collection.NumberedObjectCollection` can live here.
The other allowed classes are: ``Exceptions``, :class:`mcnpy.mcnp_card.MCNP_Card`, :class:`mcnpy.mcnp_problem.MCNP_Problem`,
and :class:`mcnpy.cell.Cell`.
Utility functions are allowed at this level as well.


input_parser
^^^^^^^^^^^^
The :mod:`mcnpy.input_parser` contains all functions and classes involved in syntax parsing.
Generally this is all invoked through :func:`mcnpy.input_parser.input_reader.read_input`,
which returns an :class:`mcnpy.mcnp_problem.MCNP_Problem` instance.

data_cards
^^^^^^^^^^
This package is for all :class:`mcnpy.mcnp_card.MCNP_Card` children that should exist
in the data block in an MCNP input. 
For example :class:`mcnpy.data_cards.material.Material` lives here.

surfaces
^^^^^^^^
This package contains all surface classes.
All classes need to be children of :class:`mcnpy.surfaces.surface.Surface`.
When possible new surface classes should combine similar planes.
For example :class:`mcnpy.surfaces.axis_plane.AxisPlane` covers ``PX``, ``PY``, and ``PZ``.

Design Philosophy
-----------------
#. **Do Not Repeat Yourself (DRY)**
#. Use abstraction and inheritance smartly.
#. Use ``_private`` fields mostly. Use ``__private`` for very private things that should never be touched.
#. Use ``@property`` getters, and if needed setters. Setters must verify and clean user inputs.
#. Fail early and politely. If there's something that might be bad: the user should get a helpful error as
   soon as the error is apparent. 
#. Test. test. test. The goal is to achieve 100% test coverage. Unit test first, then do integration testing. A new feature merge request will ideally have around a dozen new test cases.
#. Do it right the first time. 
#. Document all functions.
#. Expect everything to mutate at any time.
#. Avoid relative imports when possible. Use top level ones instead: e.g., ``import mcnpy.cell.Cell``.
#. Defer to vanilla python, and only use the standard library. Currently the only dependency is ``numpy``. 
   There must be good justification for breaking from this convention and complicating things for the user.

Style Guide
-----------
#. Use ``black`` to autoformat all code.
#. Spaces for indentation, tabs for alignment. Use spaces to build python syntax (4 spaces per level), and tabs for aligning text inside of docstrings.

Inheritance
-----------

There are many abstract or simply parent classes that are designed to be subclassed extensively.

Card: :class:`mcnpy.mcnp_card.MCNP_Card`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All classes that represent a single input card *must* subclass this. 
For example: some children are: :class:`mcnpy.cell.Cell`, :class:`mcnpy.surfaces.surface.Surface`.

How to __init__
"""""""""""""""
Your init function signature should be: ``def __init__(self, input_card=None, comment=None)``.
You should the immediately call ``super().__init__(input_card, comment)``.
This will then populate the parameters: ``input_card``, ``words``, and ``comment``.
Now you should (inside an in if block checking ``input_card``) parse 
self.words.
New classes need to support "from scratch" creation e.g., ``cell = Cell()``.

Mutation
""""""""
MCNPy supports copying the exact input unless an object changes at all,
which is inconvenient.
This is handled by ``self._mutated``. 
Whenever an object parameter is set the setter must set ``self._mutated=True``. 


Format for MCNP Input
"""""""""""""""""""""
All children must implement this abstract method.
This is the method for how :func:`mcnpy.mcnp_problem.MCNP_Problem.write_to_file` writes
this class to the file.
It must return a list of strings that faithfully represent this objects state.
Each string in the list represents one line in the MCNP input file to be written.

First if ``self._mutated = False`` the ``input_lines`` must be parroted out.
Note you must check if any of the objects that affect this one are mutated as well.
For example a cell must check if its surfaces has changed, because it's likely that
the surface's number has changed.

You have three helper functions to achieve this end goal. 
You should not try to count the number of characters in a line!
These are :func:`mcnpy.mcnp_card.MCNP_Card.format_for_mcnp_input`,
:func:`mcnpy.mcnp_card.MCNP_Card.wrap_words_for_mcnp`,
and :func:`mcnpy.mcnp_card.MCNP_Card.wrap_string_for_mcnp`.
First you need to store a list from ``super().format_for_mcnp_input``.
This function will handle adding comments, etc.
If you don't care about the formatting just create a list of strings,
representing each word in order that MCNP requires, 
and pass this to ``self.wrap_words_for_mcnp``.
If you care more about formatting create the string for each line you desire.
Then pass these strings through ``self.wrap_string_for_mcnp``,
which will then wrap any long lines to ensure it doesn't break MCNP.

Collection: :class:`mcnpy.numbered_object_collection.NumberedObjectCollection`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This should be subclassed for any collection of objects that will are numbered.
For example: cells, surfaces, materials, tallies, etc.
By default you need to do almost nothing.
The class that will be added to this collection must have the property ``obj.number``.

How to __init__
"""""""""""""""
Your init signature should be ``def __init__(self, objects=None)``
All you need to then do is call super, 
with the class this will wrap.
For example the init function for ``Cells`` ::

        def __init__(self, cells=None):
            super().__init__(mcnpy.Cell, cells)

Surface: :class:`mcnpy.surfaces.surface.Surface`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This is the parent class for all Surface classes.
You will also need to update :func:`mcnpy.surfaces.surface_builder.surface_builder`.
You should expose clear parameters such as ``radius`` or ``location``.
``format_for_mcnp_input()`` is handled by default.

How to __init__
"""""""""""""""
This is very similar to how ``MCNP_Card`` works. 
You need to first run ``super().__init__(input_card, comment)``.
You will then have access to ``self.surface_type``, and ``self.surface_constants``.
You then need to verify that the surface type is correct, and there are the correct number of surface constants. 

:func:`mcnpy.surfaces.surface.Surface.find_duplicate_surfaces`
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
This function is meant to find very similar surfaces that cause geometry errors,
such as two ``PZ`` surfaces that are 1 micron apart.
This should return a list of surfaces that are within the provided tolerance similar to this one.
Things to consider.

#. The list provided will include ``self``, ``self`` is not considered redundant with regards to ``self``.
#. Surfaces can be modified in many ways including: being periodic with respect to a surface, being transformed, being a periodic surface, and
   being a white surface. To say that two surfaces are duplicate all of these factors must be considered. 


Data Cards: :class:`mcnpy.data_cards.data_card.DataCardAbstract`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This class is the parent for all cards that show up in the data block. 
When adding a child you will also need to update the 
:func:`mcnpy.data_cards.data_parser.parse_data` function.
In general first comply with standards for this class's parent: :class:`mcnpy.mcnp_card.MCNP_Card`.
In addition you will need to implement :func:`mcnpy.data_cards.data_card.DataCard.update_pointers` 
if you need it.

During init the cards' "name word" (e.g., ``M3``, ``kcode``, ``f7:n``) is validated and parsed.
Conceptually these names can contain up to four sections.

#. A ``prefix_modifier`` this modifies the whole card with a special character such as ``*tr5`` 
#. A ``Prefix``, which is a series of letters that identifies the type such as ``m``
#. A number, which numbers it. These must be positive.
#. A particle classifier such as ``:n,p``.

You control the parsing behavior through three parameters: ``class_prefix``, ``has_number``, and ``has_classifier``.
See the documentation for how to set these.

Syntax Objects: :class:`mcnpy.input_parser.mcnp_input.MCNP_Input`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This represents all low level components in MCNP syntax, such as:
Comments, Messages, titles, and Cards. 
Similar to ``MCNP_Card`` you will need to implement ``format_for_mcnp_input``.
In this case though you will not have access the nice helper functions.
You will be responsible for ensuring that you do not exceed the maximum
number of column numbers allowed in a line.

How to __init__
"""""""""""""""
You need to call ``super().__init__(input_lines)``,
and this will provide by ``self.input_lines``.

Making a numbered Object
------------------------
MCNP allows many types of number objects like cells, surfaces, and tallies. 
First you need to provide the property ``number``. 
The parent class provides a system to link to a problem via ``self._problem``.
Note this field can be ``None``. 
When setting a number you must check for numbering collisions with the method:
:func:`mcnpy.numbered_object_collection.NumberedObjectCollection.check_number`.
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
The exception to this is the case of cards that modify another object.
For example the ``MT`` card modifies its parent ``M`` card.
In general the parent object should own its children modifiers.
This is an area of new development, and this may change.

So how do we get a surface to know about the cells it uses? 
With generators!
First, one effectively bi-directional pointer is allowed;
cards are allowed to point to the parent problem.
This is provided through ``self._problem``, and
is established by: :func:`mcnpy.mcnp_card.MCNP_Card.link_to_problem`.
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














