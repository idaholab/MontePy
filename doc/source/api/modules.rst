MontePy API 
===========


Base Problem
------------

.. autosummary::
   :toctree:
   :nosignatures:
   :template: myclass.rst

   montepy.MCNP_Problem

Base Objects
------------

.. autosummary::
   :toctree:
   :template: myclass.rst

   montepy.Cell
   montepy.Universe

Collections
-----------

.. toctree::
   :maxdepth: 1

   montepy.cells
   montepy.materials
   montepy.surface_collection
   montepy.transforms
   montepy.universes

Surfaces
--------

General Surface utilities
^^^^^^^^^^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   montepy.surfaces.surface
   montepy.surfaces.half_space


Cylinders 
^^^^^^^^^

.. toctree::
   :maxdepth: 1

   montepy.surfaces.cylinder_par_axis
   montepy.surfaces.cylinder_on_axis

Planes 
^^^^^^

.. toctree::
   :maxdepth: 1

   montepy.surfaces.general_plane
   montepy.surfaces.axis_plane


Data Inputs
-----------

Cell Modifiers
^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1
   

   montepy.data_inputs.fill
   montepy.data_inputs.importance
   montepy.data_inputs.lattice
   montepy.data_inputs.lattice_input
   montepy.data_inputs.universe_input
   montepy.data_inputs.volume

materials
^^^^^^^^^


.. toctree::
   :maxdepth: 1
   
   montepy.data_inputs.element
   montepy.data_inputs.isotope
   montepy.data_inputs.material
   montepy.data_inputs.material_component
   montepy.data_inputs.nuclide
   montepy.data_inputs.thermal_scattering

Misc.
^^^^^

.. toctree::
   :maxdepth: 1
   
   montepy.data_inputs.mode
   montepy.data_inputs.transform

Developer Focused Objects
-------------------------

Abstract Classes
^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1
   
   montepy.mcnp_object
   montepy.data_inputs.cell_modifier
   montepy.data_inputs.data_input
   montepy.geometry_operators
   montepy.numbered_mcnp_object
   montepy.numbered_object_collection


Universal Utilities and constants
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   montepy.constants
   montepy.exceptions
   montepy.particle
   montepy.surfaces.surface_type
   montepy.utilities
   
Object Builders
^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   montepy.data_inputs.data_parser
   montepy.input_parser.input_reader
   montepy.input_parser.input_syntax_reader
   montepy.surfaces.surface_builder

Parsers 
^^^^^^^

.. toctree::
   :maxdepth: 1

   montepy.input_parser.parser_base
   montepy.input_parser.cell_parser
   montepy.input_parser.data_parser
   montepy.input_parser.material_parser
   montepy.input_parser.read_parser
   montepy.input_parser.surface_parser
   montepy.input_parser.tally_parser
   montepy.input_parser.tally_seg_parser
   montepy.input_parser.thermal_parser
   montepy.input_parser.tokens


Parser Data Types
^^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   montepy.input_parser.block_type
   montepy.input_parser.input_file
   montepy.input_parser.mcnp_input
   montepy.input_parser.shortcuts
   montepy.input_parser.syntax_node

