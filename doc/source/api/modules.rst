MontePy API 
===========


Base Problem
------------

.. toctree::
   :maxdepth: 1

   montepy.mcnp_problem

Base Objects
------------

.. toctree::
   :maxdepth: 1

   montepy.cell
   montepy.universe

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
   montepy.data_inputs.nuclide
   montepy.data_inputs.material
   montepy.data_inputs.material_component
   montepy.data_inputs.thermal_scattering
   montepy.data_inputs.isotope

Misc.
^^^^^

.. toctree::
   :maxdepth: 1
   
   montepy.data_inputs.transform
   montepy.data_inputs.mode

Developer Focused Objects
-------------------------

Abstract Classes
^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1
   

   montepy.mcnp_object
   montepy.data_inputs.cell_modifier
   montepy.data_inputs.data_input
   montepy.numbered_mcnp_object
   montepy.numbered_object_collection
   montepy.geometry_operators


Universal Utilities and constants
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   montepy.constants
   montepy.exceptions
   montepy.utilities
   montepy.surfaces.surface_type
   montepy.particle
   
Object Builders
^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   montepy.data_inputs.data_parser
   montepy.surfaces.surface_builder
   montepy.input_parser.input_syntax_reader
   montepy.input_parser.input_reader

Parsers 
^^^^^^^

.. toctree::
   :maxdepth: 1

   montepy.input_parser.parser_base
   montepy.input_parser.material_parser
   montepy.input_parser.data_parser
   montepy.input_parser.cell_parser
   montepy.input_parser.surface_parser
   montepy.input_parser.tokens
   montepy.input_parser.thermal_parser
   montepy.input_parser.tally_seg_parser
   montepy.input_parser.tally_parser
   montepy.input_parser.read_parser


Parser Data Types
^^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   montepy.input_parser.syntax_node
   montepy.input_parser.input_file
   montepy.input_parser.shortcuts
   montepy.input_parser.block_type
   montepy.input_parser.mcnp_input

