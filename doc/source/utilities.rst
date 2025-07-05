Utility Scripts
===============

Package Level Execution Options
-------------------------------
.. code-block:: console

        usage: montepy [-h] [-c [input_file ...]]

        Tool for editing and working with MCNP input files.

        options:
          -h, --help            show this help message and exit
          -c [input_file ...], --check [input_file ...]
                                Check the given input file(s) for errors. Accepts globs, and multiple arguments.

Checking Input Files for Errors
-------------------------------
MontePy can be used to check for errors that it will check for.
MontePy will check for:

* general syntax errors
* syntax errors for all MCNP Objects supported (e.g., cells, surfaces, materials, etc.)
* Bad references to other object when the object referring to another object is supported.
* Bad mode options

It will print all errors it found in the input to the terminal.

To use this run:

.. code-block:: console

   python -m montepy -c [files]

.. _convert_ascii:

Converting Encoding to ASCII
----------------------------

.. _ascii_command:

Command Line Options
++++++++++++++++++++
.. code-block:: console

        usage: Change_to_ascii [-h] [-d | -w] in_file out_file

        Change the encoding of a file to strict ASCII. Everything not compliant will be removed.

        positional arguments:
          in_file           The input file to convert
          out_file          The input file to convert

        options:
          -h, --help        show this help message and exit
          -d, --delete      Delete any non-ascii characters. This is the default.
          -w, --whitespace  Replace non-ascii characters with a space.


.. _encoding_background:

Background
++++++++++
`Character encoding <https://en.wikipedia.org/wiki/Character_encoding>`_ is the process of representing all characters as numbers,
so they may be used by a computer.
It is the bane of almost all programmers.

The `American Standard Code for Information Interchange (ASCII) <https://en.wikipedia.org/wiki/ASCII>`_ is one of the oldest,
and simplest encoding standards.
It uses one byte per character, 
and only goes from 0 – 127.
This has some issues, being very American-centric,
and also only allowing 128 characters, 
52 of them being the English alphabet.
One solution to this was `"Extended ASCII" <https://en.wikipedia.org/wiki/Extended_ASCII>`_,
which used the final bit, and allowed the encoding system
to include 0 – 255.
There isn't one "Extended ASCII",
but one of the most popular encodings is Windows CP-1252.
This isn't great.

The most commonly used encoding now is `UTF-8 <https://en.wikipedia.org/wiki/UTF-8>`_, or "unicode".
UTF-8 can support almost any printable character in any language, including emojis.
The complexity is that each character is a variable-length of bytes.
This means that older software, like fortran, may get confused by it.

As far as I can tell MCNP does not document what encoding it uses.
ASCII is the most conservative bet, 
so MontePy by default tries to read input files in strict ASCII.

Dealing with Encoding Issues
++++++++++++++++++++++++++++

You are likely here because you got an error message something like this:

>>> import montepy   # doctest: +SKIP
>>> montepy.read_input("example.imcnp") # doctest: +SKIP
UnicodeDecodeError                        Traceback (most recent call last)
<snip>
UnicodeDecodeError: 'ascii' codec can't decode byte 0xc2 in position 1132: ordinal not in range(128)

You can either change the encoding used by :func:`~montepy.input_parser.input_reader.read_input`,
or just force the entire file to be strictly ASCII.

MontePY offers the ``change_to_ascii`` script. 
The options are listed above: :ref:`ascii_command`.
For any non-ASCII character it will either remove
the character or replace it with a space (``' '``).
It defaults to deleting.
To replace it with a space instead use ``-w``. 
Otherwise the arguments are the input file to correct,
and the path to write the output file to.

.. code-block:: console

   change_to_ascii -w unicode_input.imcnp ascii_input.imcnp
