Development Standards
=====================

Contributing
------------

Here is a getting started guide to contributing. 
If you have any questions Micah and Travis are available to give input and answer your questions.
Before contributing you should review the :ref:`scope` and design philosophy.

.. _Versioning:

Versioning
----------

Version information is stored in git tags,
and retrieved using `setuptools scm <https://setuptools-scm.readthedocs.io/en/latest/>`_.
The version tag shall match the regular expression:

``v\d\.\d+\.\d+(a\d+|\.post\d+)?``.

These tags will be applied by a maintainer during the release process,
and cannot be applied by normal users.

MontePy follows the `semantic versioning standard <https://semver.org/>`_ 
and the `PyPA specification for version specifiers <https://packaging.python.org/en/latest/specifications/version-specifiers/>`_ to the best of our abilities. 

The version numbers can be read as ``<Major>.<minor>.<patch>``.
Here is a quick summary of release types used, that is not meant to be authoritative:

* **Major release**: This is a release that break backwards compatibility.
* **Minor release**: This is a release the adds a new feature. 
* **Patch release**: This is a bug-fix release only.
* **Post release**: This is a release that doesn't change any code. This will add an extra ``\.post\d+`` to the end of
  the *previous* version.
* **Alpha release**: This is a testing release. Generally this is preparing for a major release. 
  Features are not locked at this point, and may change.
  This is signified by adding ``a\d+`` to the end of the *next* release.

Dependency Support
------------------

MontePy has adopted `SPEC 0 <https://scientific-python.org/specs/spec-0000/>`_. 

This project supports:

* All minor versions of Python released 36 months prior to the project, and at minimum the two latest minor versions.

* All minor versions of numpy released in the 24 months prior to the project, and at minimum the last three minor versions.
* In ``pyproject.toml``, the ``requires-python`` variable should be set to the minimum supported version of Python. All supported minor versions of Python should be in the test matrix and have binary artifacts built for the release.

Minimum Python and NumPy version support should be adjusted upward on every major and minor release, but never on a patch release.



Design Philosophy
-----------------

#. **Do Not Repeat Yourself (DRY)**
#. If it's worth doing, it's worth doing well.
#. Use abstraction and inheritance smartly.
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

Naming Conventions
^^^^^^^^^^^^^^^^^^

#. Follow `PEP 8 naming conventions <https://peps.python.org/pep-0008/#naming-conventions>`_ e.g.,

   #. ``lower_case_with_underscores`` for variables, methods, functions, and module names, etc.
   #. ``CapitalizedWords`` for class names
       
      * ``MCNP_ClassName`` is an exception. For all Other acronyms use: ``AcronymMoreWords``. Above all, prioritize legibility. 

   #. ``UPER_CASE_WITH_UNDERSCORES`` for pseudo-constant variables
   #. ``_single_leading_underscore`` should be used for almost all internal attributes.
   #. ``__double_leading_underscore`` should be used for private internal attributes that should not be accessed by users or sub-classes.

#. Variables should be nouns/noun-phrases
#. Functions/methods should be verb/verb-phrases.
#. Properties/attributes of classes should be nouns or ``is_adjective`` phrases. 
#. Collections should be a plural noun, and single instances should be singular. In loops there should be consistent
   names, e.g., ``for cell in cells:``.
#. When appropriate names should mirror Python core libraries (e.g.,
   :class:`~montepy.numbered_object_collection.NumberedObjectCollection` tries to mirror methods of ``dict``, ``list``,
   and ``set``).
#. Within reason: avoid abbreviating words. Above all, prioritize legibility.
#. For user facing functions and attributes, short names are best.
   (:func:`~montepy.surfaces.surface.Surface.surface_constants`, really should have been ``constants`` in hind-sight).


Doc Strings
-----------

All public (not ``_private``) classes and functions *must* have doc strings.
Most ``_private`` classes and functions should still be documented for other developers.
`NumPy's style guide is the standard <https://numpydoc.readthedocs.io/en/latest/format.html>`_ used for MontePy doc strings. 

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
        """Object to represent a single MCNP cell defined in CSG.

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
            >>> print(cell.material)
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

        See Also
        --------

        * :manual631sec:`5.2`
        * :manual63sec:`5.2`
        * :manual62:`55`


        .. versionchanged:: 1.0.0

            Added number parameter

        Parameters
        ----------
        input : Union[Input, str]
            The Input syntax object this will wrap and parse.
        number : int
            The number to set for this object.
        """
        
        # snip

        def __init__(
            self,
            input: InitInput = None,
            number: int = None,
        ):


Adding New Object to Website
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Sphinx website uses `autodoc <https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html>`_ to add the doc strings to the website, 
but not ``apidoc``.
Each new file will needs its own ``rst`` file in ``doc/source/api``.
See ``doc/source/api/montepy.cell.rst`` as an example.

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

Deprecation Guidelines
----------------------

Deprecation is an important part of the development life-cycle and a signal for users to help with migrations.
Deprecations can occur either during a major release, or between major releases.
The deprecation process is really part of a larger migration documentation process, 
and it provides a good last line of defense for users on how to migrate their code.

.. note::
    
   See :ref:`Versioning` section for more details on release types.
    

Major Release Deprecations
^^^^^^^^^^^^^^^^^^^^^^^^^^

These are deprecations that occur during a major release. 
Generally these are deprecations necessary for the release to work, and must be at versions: ``Major.0.0``. 
For these deprecations the guidelines are:

#. Try not to break too much.
#. Warn with a ``DeprecationWarning`` if the deprecated function is still usable. Otherwise ``raise`` it as an
   ``Exception``.
#. Add clear documentation on the fact it is deprecated and what the alternative is.
#. Write a migration plan, preferably it should be part of the releases prior the major release.
#. Only clear these ``DeprecationWarnings`` at the next major release.

Mid-Major Release Deprecations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These are deprecations that are not during a major release. That is when the version matches:
``Major.Minor.0`` or ``Major.Minor.Patch``.
The guidelines are:

#. Do not break anything
#. Warn with a ``DeprecationWarning`` (or ``PendingDeprecationWarning``, or ``FutureWarning`` as appropriate. `See the
   guide on warnings <https://docs.python.org/3/library/warnings.html#warning-categories>`_.)
#. Add clear documentation on the fact it is deprecated and what the alternative is.
#. Clear these warnings and documentation notations at the next major release.


