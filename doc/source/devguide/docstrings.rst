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

#. A class level "MCNP Manual references" section referencing the user manuals, using the ``.. mcnp-manuals::`` directive (see below).


#. An examples code block. These should start with a section header: "Exampes". All code blocks should use `sphinx doctest <https://www.sphinx-doc.org/en/master/usage/extensions/doctest.html>`_.

How to Link to the MCNP Manuals
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


For the reference section of a class docstring use the ``mcnp-manuals`` directive, rather than writing
a list of roles by hand:

.. code-block:: rst

  MCNP Manual references
  ----------------------

  .. mcnp-manuals::

     :632sec: 5.2
     :631sec: 5.2
     :62: 55

Each field name is a role name without the ``manual`` prefix, and the field body is the section or page.
The newest manual with an entry is always shown, and the others are collapsed under "Older manuals".
The order you write them in does not matter.
An unknown key, an empty value, or content that is not a field list is a build error.
The directive is defined in ``doc/source/_extension/mcnp_manuals.py``.
Use the roles directly (``:manual632:`` etc.) for references in running prose.

MontePy docstrings features custom commands for linking to MCNP user manuals when citing them outisde of doc strings.
These in general follow the ``:manual62:``, ``:manual63:``, ``:manual631:``, ``:manual632:`` pattern.

The MCNP 6.2.0 manual only supports linking to a specific page, and not a section, so the argument it takes is a
page number: ``:manual62:`123```: becomes :manual62:`123`.
The manuals for MCNP 1, 2, 3A, 4B, 4C, MCNPX, and 5 are also linkable by page only, with
``:manual1:``, ``:manual2:``, ``:manual3a:``, ``:manual4b:``, ``:manual4c:``, ``:manualx:``, and ``:manual5:``.
The number is the PDF page index, which may differ from the printed page number.

.. note::

  The ``:manual5:`` PDF is only Volume I of the MCNP 5 manual (overview and theory).
  The input syntax is in Volume II, which LANL does not publicly distribute, so ``:manual5:`` is for theory only.
  Likewise the MCNPX 2.3.0 manual (``:manualx:``) only describes changes to MCNP, not the base input cards.

The MCNP 6.3 manuals do support linking to section anchors.
Which anchor is linked depends on the suffix of the command:

.. list-table::
  :header-rows: 1

  * - Suffix
    - Links to
    - Example
  * - ``chapter``
    - A chapter
    - ``:manual63chapter:`5```
  * - ``part``
    - A part
    - ``:manual63part:`5```
  * - ``sec``
    - A section
    - ``:manual63sec:`5.6```
  * - (none)
    - A subsection (the default)
    - ``:manual63:`5.6.1```
  * - ``sub``
    - A subsubsection
    - ``:manual63sub:`5.6.1.1```

For example, ``:manual63:`5.6.1``` becomes: :manual63:`5.6.1`.
The same suffixes work for ``:manual631:`` and ``:manual632:``. For the exact definitions see ``doc/source/conf.py``.

When citing:

* Cite the section that supports the statement, not the whole manual or chapter.
* Check that the link goes to the right place in the PDF.
* Prefer citing the latest manual version (currently MCNP 6.3.2, ``:manual632:``) that contains the information.
  Where practical also cite the 6.3.1, 6.3.0, and 6.2 manuals. Older manuals are optional.

The PDF URLs are defined once in ``doc/source/conf.py`` (``MCNP_MANUAL_PDFS``) and listed in ``index.rst``.

.. note::

   ``make linkcheck`` skips every manual link that has a ``#fragment``, so the many section links don't flood
   ``mcnp.lanl.gov`` with requests. Only the bare PDF URLs in ``index.rst`` are checked, once each.
   The anchors themselves are therefore *not* validated by CI.
   Check them with ``python doc/check_manual_refs.py check -v``, which compares every reference in ``montepy/``
   against local copies of the PDFs (fetch them once with ``python doc/check_manual_refs.py download``;
   it needs ``mutool`` and ``pdftotext`` installed).
   ``-v`` prints the heading each reference lands on so you can confirm it is the right one.
   It also checks that ``index.rst`` lists every manual exactly once.
   ``python doc/check_manual_refs.py search "Cell Cards"`` finds a heading in every manual.

   For the older manuals that only link by page, the number must be the *physical* page index of the PDF (what
   a PDF viewer opens for ``#page=N``), not the page number printed on the page.

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

        MCNP Manual references
        ----------------------

        .. mcnp-manuals::

           :632sec: 5.2
           :631sec: 5.2
           :63sec: 5.2
           :62: 55


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
