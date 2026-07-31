.. meta::
   :description lang=en:
        MontePy testing standards: pytest practices, test organization, and migration from unittest.

Testing
=======

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
   <https://semaphore.io/blog/property-based-testing-python-hypothesis-pytest>`_.

Test Organization
-----------------

Tests are organized in the ``tests`` folder in the following way:

#. Unit tests are in their own files for each class or a group of classes.
#. Integration tests go in ``tests/test_*integration.py``. New integration files are welcome.
#. Interface tests with other libraries, e.g., ``pickle`` go in ``tests/test_interface.py``.
#. Test classes are preffered to organize tests by concepts.
   Each MontePy class should have its own test class. These should not subclass anything.
   Methods should accept ``_`` instead of ``self`` to note that class structure is purely organizational.

Test Migration
--------------

Currently the test suite does not conform to these standards fully.
Help with making the migration to the new standards is appreciated.
So don't think something is sacred about a test file that does not follow these conventions.
