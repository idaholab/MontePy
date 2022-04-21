Getting Started with MCNPy
==========================

MCNPy is a python API for reading, editing, and writing MCNP input files.
It does not run MCNP nor does it parse MCNP output files.
The library provides a semantic interface for working with input files, or problems.
It understands that the second entry on a cell card is the material number,
and will link the cell with its material object.

Reading a File
--------------
MCNPy offers the ``read_input()`` function for getting started.
It will read the specified MCNP input file, and return an MCNPy ``MCNP_Problem`` object.

>>> import mcnpy
>>> problem = mcnpy.read_input("foo.imcnp")
>>> len(problem.cells)
4


Remember: make objects, not regexs!
