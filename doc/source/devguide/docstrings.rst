.. meta::
   :description lang=en:
        MontePy docstring standards: mandatory elements, recommended elements, examples, and adding new objects to the website.

Doc Strings
===========

All public (not ``_private``) classes and functions *must* have doc strings.
Most ``_private`` classes and functions should still be documented for other developers.
`NumPy's style guide is the standard <https://numpydoc.readthedocs.io/en/latest/format.html>`_ used for MontePy doc strings.

Mandatory Elements
------------------

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


Highly Recommended
------------------

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
-------

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

Adding New Objects to the Website
-----------------------------------

The Sphinx website uses `autosummary <https://www.sphinx-doc.org/es/master/usage/extensions/autosummary.html#generating-stub-pages-automatically>`_.
Each class or module must be pointed to in ``doc/source/api/modules.rst``,
it is preferable to point to the classes themselves, and not the modules.
