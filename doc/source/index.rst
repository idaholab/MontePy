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

or with conda:

.. code-block:: shell

   conda install conda-forge::montepy


Use cases
---------

Here are some possible use cases for MontePy:

* Automated updating of an MCNP input file, or MCNP deck, for reactor reconfiguration, fuel shuffling, etc.
* Parameterizing an MCNP input file to check for explore the parametric space of your MCNP modeling problem
* Updating an MCNP model with the results from another code, such as depletion results from ORIGEN.
* To convert an MCNP model to another Monte Carlo code like OpenMC, SERPENT, etc. 


Try it Now
----------

.. jupyterlite:: 
   :new_tab: True
   :new_tab_button_text: Launch jupyter in your browswer

Contents
--------

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
* MCNP User Manuals (PDFs hosted by LANL; the ``:manual*:`` docstring roles link into these):

  * `MCNP 6.3.2 <https://mcnp.lanl.gov/pdf_files/TechReport_2026_LANL_LA-UR-26-23119Rev.1_KuleszaAdamsEtAl.pdf>`_
  * `MCNP 6.3.1 <https://mcnp.lanl.gov/pdf_files/TechReport_2024_LANL_LA-UR-24-24602Rev.1_KuleszaAdamsEtAl.pdf>`_
  * `MCNP 6.3.0 <https://mcnp.lanl.gov/pdf_files/TechReport_2022_LANL_LA-UR-22-30006Rev.1_KuleszaAdamsEtAl.pdf>`_
  * `MCNP 6.2 <https://mcnp.lanl.gov/pdf_files/TechReport_2017_LANL_LA-UR-17-29981_WernerArmstrongEtAl.pdf>`_
  * `MCNP5 <https://mcnp.lanl.gov/pdf_files/TechReport_2003_LANL_LA-UR-03-1987Revised212008_SweezyBoothEtAl.pdf>`_ (Volume I: overview and theory only. The input syntax is in Volume II, which is not publicly available.)
  * `MCNPX <https://mcnp.lanl.gov/pdf_files/TechReport_2002_LANL_LA-UR-02-2607_Waters.pdf>`_ (version 2.3.0: documents only the changes to MCNP, so it does not describe the base input cards.)
  * `MCNP4C <https://mcnp.lanl.gov/pdf_files/TechReport_2000_LANL_LA-13709-M_Briesmeisterothers.pdf>`_
  * `MCNP4B <https://mcnp.lanl.gov/pdf_files/TechReport_1997_LANL_LA-12625-M_Briesmeisterothers.pdf>`_
  * `MCNP3A <https://mcnp.lanl.gov/pdf_files/TechReport_1986_LANL_LA-7396-MRev.2_BriesmeisterBoothEtAl.pdf>`_
  * `MCNP2 <https://mcnp.lanl.gov/pdf_files/TechReport_1979_LANL_LA-7396-MRev.1_LGT.pdf>`_
  * `MCNP1 <https://mcnp.lanl.gov/pdf_files/TechReport_1978_LANL_LA-7396-M_LGT.pdf>`_
  * `MCNP5 <https://mcnp.lanl.gov/pdf_files/TechReport_2003_LANL_LA-UR-03-1987Revised212008_SweezyBoothEtAl.pdf>`_
  * `MCNPX <https://mcnp.lanl.gov/pdf_files/TechReport_2002_LANL_LA-UR-02-2607_Waters.pdf>`_
  * `MCNP4C <https://mcnp.lanl.gov/pdf_files/TechReport_2000_LANL_LA-13709-M_Briesmeisterothers.pdf>`_
  * `MCNP4B <https://mcnp.lanl.gov/pdf_files/TechReport_1997_LANL_LA-12625-M_Briesmeisterothers.pdf>`_
  * `MCNP3A <https://mcnp.lanl.gov/pdf_files/TechReport_1986_LANL_LA-7396-MRev.2_BriesmeisterBoothEtAl.pdf>`_
  * `MCNP2 <https://mcnp.lanl.gov/pdf_files/TechReport_1979_LANL_LA-7396-MRev.1_LGT.pdf>`_
  * `MCNP1 <https://mcnp.lanl.gov/pdf_files/TechReport_1978_LANL_LA-7396-M_LGT.pdf>`_
* `MCNP Forum <https://mcnp.discourse.group/>`_

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
