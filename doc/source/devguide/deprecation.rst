.. meta::
   :description lang=en:
        MontePy deprecation guidelines for major and mid-major releases.

Deprecation Guidelines
=======================

Deprecation is an important part of the development life-cycle and a signal for users to help with migrations.
Deprecations can occur either during a major release, or between major releases.
The deprecation process is really part of a larger migration documentation process,
and it provides a good last line of defense for users on how to migrate their code.

.. note::

   See :ref:`Versioning` section for more details on release types.


Major Release Deprecations
---------------------------

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
--------------------------------

These are deprecations that are not during a major release. That is when the version matches:
``Major.Minor.0`` or ``Major.Minor.Patch``.
The guidelines are:

#. Do not break anything
#. Warn with a ``DeprecationWarning`` (or ``PendingDeprecationWarning``, or ``FutureWarning`` as appropriate. `See the
   guide on warnings <https://docs.python.org/3/library/warnings.html#warning-categories>`_.)
#. Add clear documentation on the fact it is deprecated and what the alternative is.
#. Clear these warnings and documentation notations at the next major release.
