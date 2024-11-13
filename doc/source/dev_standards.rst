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

Doc Strings
-----------
