.. _scope:

MontePy Scope
-------------

This document defines the scope of MontePy so it easier to decide if a feature should live in MontePy or possibly another repository.
This isn't meant to be fully static and is subject to change.
This is less focused on defining a strict scope and more-so on providing guidelines.

Mission
=======

MontePy's mission is to improve the user experience for working with MCNP input files through the power of python automation?

Principles 
==========
Here are the guiding principles of what MontePy should be, and what it aspires to be.

MontePy should be:
------------------

#. Easy to install. 

   #. It should be on PyPi.
   #. Install with ``pip`` for most conceivable platforms. 

#. Lightweight. It should only include the code that all users need, and only the bare essentials for dependencies. 
#. Well documented. All public functions must have documentation.
#. `Pythonic <https://en.wikipedia.org/wiki/Zen_of_Python>`_.
#. Idiomatic.
#. Consistently designed.
#. General. New features shouldn't be only useful for a specific problem, or class of problems.
#. Quick to fail and do so in a verbose helpful manner.
#. Reliable. 
#. Thorough in its validation. If it MontePy finds more issues than MCNP does, that's ok. 
#. Easy to contribute to.
#. Able to support the full (public) MCNP manual, except when it doesn't.

   #. For features that aren't supported yet an UnsuportedFeature error should be raised.
   #. The developers reserve the right to decide a feature is not worth ever supporting.


MontePy shouldn't be:
---------------------

#. A collection of scripts for every use case.
#. A linking code to other software.
#. Written in other languages*

Design Philosophy
=================
#. **Do Not Repeat Yourself (DRY)**
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
#. Use ``black`` to autoformat all code.
#. Spaces for indentation, tabs for alignment. Use spaces to build python syntax (4 spaces per level), and tabs for aligning text inside of docstrings.
#. Follow `PEP 8 <https://peps.python.org/pep-0008/>`_.

MontePy is:
===========

MontePy isn't:
==============

Note on use of other languages
------------------------------

The use of another language in the code base goes against the principle that it should be easy to contribute.
However, there could be cases where the advantages of another language could justify this violation.
Here are guidelines for when it could be appropriate:

#. There needs to be a clear and significant benefit.
#. The rewrite needs to be limited in scope to a module that few developers will modify.
    
  #. Only the input parser seems to meet this criteria.

#. There must be a dependable build system that allows deployment to PyPI.
