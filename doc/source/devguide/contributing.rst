.. meta::
   :description lang=en:
        How to contribute to MontePy: getting started, semantic versioning, and dependency support policy.

Contributing, Versioning, and Dependency Support
=================================================

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
