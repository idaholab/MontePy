.. meta::
   :description lang=en:
        How to read, write, and check MCNP input files with MontePy.

Reading and Writing Files
=========================

.. testsetup:: *

   import montepy

Reading a File
--------------

MontePy offers the :func:`montepy.read_input` function for getting started.
It will read the specified MCNP input file, and return an MontePy :class:`~montepy.MCNP_Problem` object.

>>> import montepy
>>> problem = montepy.read_input("foo.imcnp")
>>> len(problem.cells)
2

Performance: Just-in-Time Parsing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default MontePy uses **just-in-time (JIT) parsing**, though this can be disabled
by passing ``jit_parse=False`` to :func:`~montepy.input_parser.input_reader.read_input`.
When JIT parsing is enabled, each input is only parsed enough to categorize it and
record its number on first read.
The full parse of each object is deferred until you actually access its data.

This means:

* **The first access** of any object's data may be slightly slower while the full parse
  runs. Subsequent accesses are normal speed.
* **Iterating over all objects** (e.g., looping over every cell to read densities) will
  trigger a full parse of every object and can therefore be slow for large files.

.. note::

   If you need to pre-parse everything up front (for example, to ensure all errors
   surface immediately), you can pass ``jit_parse=False`` to
   :func:`~montepy.input_parser.input_reader.read_input`, or call
   :func:`~montepy.mcnp_object.MCNP_Object.full_parse` on individual objects.

Operations that trigger mass parsing
"""""""""""""""""""""""""""""""""""""

Some operations force every object in the problem to be fully re-parsed at once.
For large problems these can be a significant one-time cost.

* **Switching a cell-modifier between the cell block and the data block** — via
  :attr:`~montepy.MCNP_Problem.print_in_data_block` — forces every cell
  to be fully re-parsed, because each cell's syntax tree must be rebuilt to either
  absorb or expel the modifier.

* **Accessing generators pointing back to parent objects does not trigger mass parsing**.
  MontePy has a number of object properties, which are generators, that list parent objects that use the given object.
  For instance :meth:`montepy.Surface.cells` lists all of the cells that use the given surface.
  To determine if a cell uses a given surface a full parse is necessary.
  However, using these generators will not trigger a parsing of every cell.
  Instead, the :meth:`~montepy.Cell.search` method is used to search for the surface's number first.
  This reduces the number of cells that need to be fully parsed to only to those which have the exact number of the surface somewhere in their definition.
  For long surface numbers this should yield very few false positives.


Avoid Mass Parsing with ``search``
""""""""""""""""""""""""""""""""""

All objects will have the :meth:`~montepy.mcnp_object.MCNP_Object.search` method.
This will search the object for the given string in its input from the file,
without triggering a full parse.
This can be used to avoid a mass parse when searching on a specific attribute.
For instance you could try the following to find all cells with a density of :math:`8.912 \rm \frac{g}{cm^3}`.

.. testcode::

   import math

   TEST_DENSITY = 8.912

   matching_cells = []
   for cell in problem.cells:
       if cell.search(str(TEST_DENSITY)) and not cell.is_atom_dens:
           if math.isclose(cell.mass_density, TEST_DENSITY):
               matching_cells.append(cell)


Writing a File
--------------

The :class:`~montepy.MCNP_Problem` object has
the method :func:`~montepy.MCNP_Problem.write_problem`, which writes the problem's current
state as a valid MCNP input file.

>>> problem.write_problem("bar.imcnp")

The :func:`~montepy.MCNP_Problem.write_problem` method does take an optional argument: ``overwrite``.
By default if the file exists, it will not be overwritten and an error will be raised.
This can be changed by ``overwrite=True``.

.. warning::
   Overwriting the original file (with ``overwrite=True``) when writing a modified file out is discouraged.
   This is because if your script using MontePy is buggy you have no real way to debug,
   and recover from the issue if your original file has been been modified.
   Instead of constantly having to override the same file you can add a timestamp to the output file,
   or create an always unique file name with the `UUID <https://docs.python.org/3/library/uuid.html>`_ library.

The method :func:`~montepy.MCNP_Problem.write_problem`
also accepts an open file handle, stream, or other object with a ``write()`` method.

>>> with open("foo_bar.imcnp", "w") as fh:
...     problem.write_problem(fh)
>>> new_problem = montepy.read_input("foo_bar.imcnp")
>>> len(new_problem.cells)
2


If no changes are made to the problem in MontePy, the entire file should just be parroted out as it was in the original file
(see Issues :issue:`397` and :issue:`492`).
However any objects (e.g., two cells) that were changed (i.e., mutated) may have their formatting changed slightly.
MontePy will do its best to guess the formatting of the original value and to replicate it with the new value.
However, this may not always be possible, especially if more digits are needed to keep information (e.g., ``10`` versus ``1000``).
In this case MontePy will warn you that value will take up more space which may break your pretty formatting.

For example say we have this simple MCNP input file (saved as :download:`foo.imcnp <../foo.imcnp>`) ::

        Example Problem
        1 0  -1 2 -3
        2 0  -4 5 -6

        1 CZ 0.5
        2 PZ 0
        3 PZ 1.5
        4 CZ 0.500001
        5 PZ 1.5001
        6 PZ 2.0

        kcode 1.0 100 25 100
        TR1 0 0 1.0
        TR2 0 0 1.00001

We can then open this file in MontePy, and then modify it slightly, and save it again:

.. doctest::

        import montepy
        problem = montepy.read_input("foo.imcnp")
        problem.cells[1].number = 5
        problem.surfaces[1].number = 1000
        problem.write_problem("bar.imcnp")

This new file we can see is now reformatted according to MontePy's preferences for formatting::

        Example Problem
        5 0  -1000 2 -3
        2 0  -4 5 -6

        1000 CZ 0.5
        2 PZ 0
        3 PZ 1.5
        4 CZ 0.500001
        5 PZ 1.5001
        6 PZ 2.0

        kcode 1.0 100 25 100
        TR1 0.0 0.0 1.0
        TR2 0.0 0.0 1.00001

In addition to the renumbering of cell 5,
notice that the geometry definition for cell 5 was automatically updated to reference the new surface number.
MontePy links objects together and will automatically update "pointers" in the file for you.

What Information is Kept
------------------------

So what does MontePy keep, and what does it forget?

Information Kept
^^^^^^^^^^^^^^^^
#. The optional message block at the beginning of the problem (it's a niche feature; check out section :manual63:`4.4.1` of the user manual)
#. The problem title
#. ``C`` style comments (e.g., ``C this is a banana``)
#. (Almost) all MCNP inputs. Only the read input is discarded.
#. Dollar sign comments (e.g., ``1 0 $ this is a banana``)
#. Other user formatting and spaces. If extra spaces between values are given the space will be expanded or shortened to try to keep
   the position of the next value in the same spot as the length of the first value changes.
#. MCNP shortcuts for numbers. All shortcuts will be expanded to their meaning.
   Jumps will be subsituted with the value: :class:`~montepy.input_parser.mcnp_input.Jump`.
   On write MontePy will attempt to recompress all shortcuts. It does this by looking at shortcuts in the original file,
   and trying to "consume" their nearest neighbors. So for instance if you had ``imp:n 1 10r 0`` and added a new cell with an importance of ``1.0``
   second to the end MontePy will print ``imp:n 1 11r 0`` and not ``imp:n 1 10r 1 0``.
   MontePy will not automatically "spot" various sequences that could be shortcuts and will not automatically make shortcuts out of them.
   The one exception to this rule is for jumps. If a sequence of new Jump values are added they will automatically combined as ``2J`` instead of printing them as ``J J``.

Information Lost
^^^^^^^^^^^^^^^^
#. Read inputs. These are handled properly, but when written out these inputs themselves will disappear.
   When MontePy encounters a read input it notes the file in the input, and then discards the input.
   It will then read these extra files and append their contents to the appropriate block.
   So If you were to write out a problem that used the read input in the surface block the surface
   inputs in that file from the read input will appear at the end of the new surface block in the newly written file.

.. note::

   This will hopefully change soon and read "subfiles" will be kept, and will automatically be written as their own files.



Running as an Executable
------------------------

MontePy can be ran as an executable.
Currently this only supports checking an MCNP input file for errors.

Checking Input files for Errors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

MontePy can be ran to try to open an MCNP input file and to read as much as it can and try to note all errors it finds.
If there are many errors not all may be found at once due to how errors are handled.
This is done by executing it with the ``-c`` flag, and specifying a file, or files to check.
You can also use linux globs::

        python -m montepy -c tests/inputs/*.imcnp

MontePy will then show which file it is reading, and show a warning for every potential error with the input file it has found.

If you want to try to troubleshoot errors in python you can do this with the following steps.

.. warning::
   This following guide may return an incomplete problem object that may break in very weird ways.
   Never use this for actual file editing; only use it for troubleshooting.

#. Setup a new Problem object:

   .. testcode::

       problem = montepy.MCNP_Problem("foo.imcnp")

#. Next load the input file with the ``check_input`` set to ``True``.

   .. testcode::

        problem.parse_input(True)


**Remember: make objects, not regexes!**
