.. meta::
   :description lang=en:
        MontePy is the most user-friendly Python library for reading, editing, and writing MCNP input files. Install with pip and get started quickly.

Getting Started with MontePy
============================


.. testsetup:: *

   import montepy

MontePy is a Python API for reading, editing, and writing MCNP input files.
The library provides a semantic interface for working with input files ("MCNP problems").
It does not run MCNP, nor does it parse MCNP output files.
It understands that the second entry on a cell input is the material number,
and will link the cell with its material object.

.. note::
    MontePy is built primarily to support MCNP 6.2, and MCNP 6.3. Some success maybe achieved with MCNP 6.1, and 5.1.60,
    but there may be issues due to new features in MCNP 6.2, not being backwards compatible.
    Use earlier versions of MCNP with MontePy at your own risk.

    MCNP 6.3 is not fully supported yet either.
    An MCNP 6.3 file that is backwards compatible with 6.2 should work fine,
    but when using the new syntaxes in 6.3,
    especially for materials,
    MontePy will likely break.

    Due to the manuals for these earlier versions of MCNP being export controlled, these versions will likely never be fully supported.


Run Interactively in your Browser
---------------------------------

You can run python and MontePy straight from your browser below:

.. replite::
   :width: 100%
   :height: 600px
   :prompt: Try MontePy

   %pip install montepy
   import montepy
   problem = montepy.read_input("models/pin_cell.imcnp")

Installing
----------


System Wide (for the current user)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   If you are planning to use this in a jupyter notebook on an HPC,
   the HPC may use modules for python, which may make it so the installed MontePy package doesn't show up in the jupyter environment.
   In this case the easiest way to deal with this is to open a teminal inside of `jupyter lab` and to install the package there.


#. Install it from `PyPI <https://pypi.org/project/montepy>`_ by running ``pip install montepy``.
   You may need to run ``pip install --user montepy`` if you are not allowed to install the package.

Installing Optional Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

MontePy offers multiple optional dependencies which some users may desire,
though this is mostly intended for developers.
Pip can install these through the following command:

``pip install montepy[<extras>]``

Where ``<extras>`` is one of the following options:

#. ``demos``: installs the dependencies for running the demo problems in `jupyter <https://jupyter.org/>`_.

#. ``doc``: installs the dependencies for building the website using `sphinx <https://www.sphinx-doc.org/en/master/>`_.

#. ``build``: installs the dependencies for building the source distribution packages.

#. ``format``: install the dependencies for formatting the code with `black <https://black.readthedocs.io/en/stable/index.html>`_.

#. ``test``: installs the dependencies for testing the software.

#. ``demo-test``: installs the dependencies for testing the demos.

#. ``develop``: installs everything a developer may need, specifically: ``montepy[test,doc,format,demo-test]``.

Install specific version for a project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The best way maybe to setup a project-specific `conda <https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html>`_,
`Mamba <https://mamba.readthedocs.io/en/latest/user_guide/concepts.html>`_,
or a `venv <https://docs.python.org/3/library/venv.html>`_ environment.
The steps for installing inside one of those environments are the same as the previous steps.
You can specify a specific version from `PyPI`_ be installed using:

``pip install montepy==<version>``

Or using conda-forge:

``conda install conda-forge::montepy==<version>``

Tutorials and Demonstrations
----------------------------

We have presented a workshop for using MontePy in the past.
The demonstration Jupyter notebooks are now available in our git repository.

These can be ran in your browser using `jupyter lite <https://jupyterlite.readthedocs.io/en/stable/index.html>`_.

These tutorial can be launched here:

.. jupyterlite::
   :new_tab: True
   :new_tab_button_text: Launch jupyter in your browswer


To access these demonstrations locally you can run:

.. code-block:: bash

   git clone https://github.com/idaholab/MontePy.git
   pip install montepy[demos]
   cd MontePy/demos
   jupyter lab

These notebooks are not complete, and have missing code you need to fill in.
If you get stuck there are complete notebooks in the ``answers`` folder, that you can refer to.

Finally if you want to present these notebooks in a workshop,
we use `RISE <https://rise.readthedocs.io/en/latest/>`_ to turn the notebooks into a slideshow.
You can install this with ``pip install montepy[demo-present]``.

.. toctree::
   :maxdepth: 2

   guide/best_practices
   guide/reading_writing
   guide/problem
   guide/surfaces
   guide/cells
   guide/materials
   guide/universes
   guide/tallies
