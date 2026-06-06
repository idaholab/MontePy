.. meta::
   :description lang=en:
        MontePy design philosophy, style guide, and naming conventions for contributors.

Design Philosophy and Style Guide
===================================

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
   (:attr:`~montepy.Surface.surface_constants`, really should have been ``constants`` in hind-sight).
