.. meta::
   :description lang=en:
        MontePy is a Python library for reading, editing, and writing MCNP input files.
        MontePy provides an object-oriented interface for MCNP input files. 
        This allows for easy automation of many different tasks for working with MCNP input files.
    

MontePy: a Python library for MCNP input files.
===============================================

MontePy is the most user-friendly Python library for reading, editing, and writing MCNP input files.
MontePy provides an object-oriented interface for MCNP input files. 
This allows for easy automation of many different tasks for working with MCNP input files.

Installing
----------

MontePy can be installed with pip:

.. code-block:: shell

   pip install montepy


Use cases
---------

Here are some possible use cases for MontePy:

* Automated updating of an MCNP input file, or MCNP deck, for reactor reconfiguration, fuel shuffling, etc.
* Parameterizing an MCNP input file to check for explore the parametric space of your MCNP modeling problem
* Updating an MCNP model with the results from another code, such as depletion results from ORIGEN.
* To convert an MCNP model to another Monte Carlo code like OpenMC, SERPENT, etc. 


.. toctree::
   :maxdepth: 2
   :caption: Table of Contents:

   users
   dev_tree
   api/modules

See Also
--------

* `MontePy github Repository <https://github.com/idaholab/montepy>`_
* `MontePy PyPI Project <https://pypi.org/project/montepy/>`_
* `MontePy journal Article <https://doi.org/10.21105/joss.07951>`_ DOI: `10.21105/joss.07951 <https://doi.org/10.21105/joss.07951>`_
* `MCNP 6.3.1 User Manual <https://www.osti.gov/biblio/2372634>`_ DOI: `10.2172/2372634 <https://doi.org/10.2172/2372634>`_
* `MCNP 6.3 User Manual <https://www.osti.gov/biblio/1889957>`_ DOI: `10.2172/1889957 <https://doi.org/10.2172/1889957>`_
* `MCNP 6.2 User Manual <https://mcnp.lanl.gov/pdf_files/TechReport_2017_LANL_LA-UR-17-29981_WernerArmstrongEtAl.pdf>`_
* `MCNP Forum <https://mcnp.discourse.group/>`_

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
