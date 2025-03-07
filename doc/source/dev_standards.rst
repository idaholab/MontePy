Development Standards
=====================

Contributing
------------

Here is a getting started guide to contributing. 
If you have any questions Micah and Travis are available to give input and answer your questions.
Before contributing you should review the :ref:`scope` and design philosophy.


Versioning
----------

Version information is stored in git tags,
and retrieved using `setuptools scm <https://setuptools-scm.readthedocs.io/en/latest/>`_.
The version tag shall match the regular expression:

``v\d\.\d+\.\d+``.

These tags will be applied by a maintainer during the release process,
and cannot be applied by normal users.

MontePy follows the semantic versioning standard to the best of our abilities. 

Additional References:

#. `Semantic versioning standard <https://semver.org/>`_

Design Philosophy
-----------------

#. **Do Not Repeat Yourself (DRY)**
#. If it's worth doing, it's worth doing well.
#. Use abstraction and inheritance smartly.
#. Use ``_private`` fields mostly. Use ``__private`` for very private things that should never be touched.
#. Use ``@property`` getters, and if needed setters. Setters must verify and clean user inputs. For the most part use :func:`~montepy.utilities.make_prop_val_node`, and :func:`~montepy.utilities.make_prop_pointer`.
#. Fail early and politely. If there's something that might be bad: the user should get a helpful error as
   soon as the error is apparent. 
#. Test. test. test. The goal is to achieve 100% test coverage. Unit test first, then do integration testing. A new feature merge request will ideally have around a dozen new test cases.
#. Do it right the first time. 
#. Document all functions.
#. Expect everything to mutate at any time.
#. Avoid relative imports when possible. Use top level ones instead: e.g., ``import montepy.cell.Cell``.
#. Defer to vanilla python, and only use the standard library. Currently the only dependencies are `numpy <https://numpy.org/>`_ and `sly <https://github.com/dabeaz/sly>`_. 
   There must be good justification for breaking from this convention and complicating things for the user.

Style Guide
-----------

#. Thou shall be `PEP 8 <https://peps.python.org/pep-0008/>`_, and use `black <https://black.readthedocs.io/en/stable/index.html>`_.
#. Spaces not tabs with 4 spaces for an indent.
#. External imports before internal imports with a blank line in between. All imports are alphabetized. 

Doc Strings
-----------

All public (not ``_private``) classes and functions *must* have doc strings.
Most ``_private`` classes and functions should still be documented for other developers.

Mandatory Elements
^^^^^^^^^^^^^^^^^^

#. One line descriptions.
#. Type annotations in the function signature
#. Description of all inputs.
#. Description of return values (can be skipped for None).
#. ``.. versionadded::``/ ``.. versionchanged::`` information for all new functions and classes. This information can
   be dropped with major releases.
#. Example code for showing how to use objects that implement atypical ``__dunders__``, e.g., for ``__setitem__``, ``__iter__``, etc.
#. `Type hints <https://docs.python.org/3/library/typing.html>`_ on all new or modified functions.

.. note::

    Class ``__init__`` arguments are documented in the class docstrings and not in ``__init__``. 

.. note::

    MontePy is in the process of migrating to type annotations, so not all functions will have them.
    Eventually MontePy may use a type enforcement engine that will use these hints.
    See :issue:`91` for more information.
    If you have issues with circular imports add the import: ``from __future__ import annotations``,
    this is from `PEP 563 <https://peps.python.org/pep-0563/>`_.


Highly Recommended.
^^^^^^^^^^^^^^^^^^^

#. A class level ``.. seealso:`` section referencing the user manuals.


#. An examples code block. These should start with a section header: "Exampes". All code blocks should use `sphinx doctest <https://www.sphinx-doc.org/en/master/usage/extensions/doctest.html>`_.

.. note::

   MontePy docstrings features custom commands for linking to MCNP user manuals.
   These in general follow the ``:manual62:``, ``:manual63:``, ``:manual631:`` pattern.

   The MCNP 6.2.0 manual only supports linking to a specific page, and not a section, so the argument it takes is a
   page number: ``:manual62:`123```: becomes :manual62:`123`.

   The MCNP 6.3 manuals do support linking to section anchors.
   By default the command links to a ``\\subsubsection``, e.g., ``:manual63:`5.6.1``` becomes: :manual63:`5.6.1`.
   For other sections see: ``doc/source/conf.py``. 

Example 
^^^^^^^

Here is the docstrings for :class:`~montepy.cell.Cell`.

.. code-block:: python

    class Cell(Numbered_MCNP_Object):
        """
        Object to represent a single MCNP cell defined in CSG.

        Examples
        ^^^^^^^^

        First the cell needs to be initialized.

        .. testcode:: python

            import montepy
            cell = montepy.Cell()

        Then a number can be set.
        By default the cell is voided:

        .. doctest:: python

            >>> cell.number = 5
            >>> cell.material
            None
            >>> mat = montepy.Material()
            >>> mat.number = 20
            >>> mat.add_nuclide("1001.80c", 1.0)
            >>> cell.material = mat
            >>> # mass and atom density are different
            >>> cell.mass_density = 0.1

        Cells can be inverted with ``~`` to make a geometry definition that is a compliment of
        that cell.

        .. testcode:: python

            complement = ~cell


        .. seealso::

                * :manual63sec:`5.2`
                * :manual62:`55`

        :param input: the input for the cell definition
        :type input: Input

        """
        
        # snip

        def __init__(self, input: montepy.input_parser.mcnp_input.Input = None):

Testing
-------

Pytest is the official testing framework for MontePy.
In the past it was unittest, and so the test suite is in a state of transition. 
Here are the principles for writing new tests:

#. Do not write any new tests using ``unittest.TestCase``.
#. Use ``assert`` and not ``self.assert...``, even if it's available.
#. `parametrizing <https://docs.pytest.org/en/7.1.x/example/parametrize.html>`_ is preferred over verbose tests.
#. Use `fixtures <https://docs.pytest.org/en/7.1.x/reference/reference.html#pytest.fixture>`_.
#. Use property based testing with `hypothesis <https://hypothesis.readthedocs.io/en/latest/>`_, when it makes sense.
   This is generally for complicated functions that users use frequently, such as constructors.
   See this `tutorial for an introduction to property based testing
   <https://semaphoreci.com/blog/property-based-testing-python-hypothesis-pytest>`_. 

Test Organization
^^^^^^^^^^^^^^^^^

Tests are organized in the ``tests`` folder in the following way:

#. Unit tests are in their own files for each class or a group of classes.
#. Integration tests go in ``tests/test_*integration.py``. New integration files are welcome.
#. Interface tests with other libraries, e.g., ``pickle`` go in ``tests/test_interface.py``. 
#. Test classes are preffered to organize tests by concepts.
   Each MontePy class should have its own test class. These should not subclass anything.
   Methods should accept ``_`` instead of ``self`` to note that class structure is purely organizational. 

Test Migration
^^^^^^^^^^^^^^

Currently the test suite does not conform to these standards fully.
Help with making the migration to the new standards is appreciated.
So don't think something is sacred about a test file that does not follow these conventions.
