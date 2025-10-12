MontePy API 
===========


Base Problem
------------

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst

   montepy.MCNP_Problem
   montepy.read_input

Base Objects
------------

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst
   
   montepy.Cell
   montepy.Universe

Collections
-----------

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst

   montepy.Cells
   montepy.Materials
   montepy.Surfaces
   montepy.Transforms
   montepy.Universes

Surface Objects
---------------

General Surface utilities
^^^^^^^^^^^^^^^^^^^^^^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst

   montepy.Surface
   montepy.HalfSpace


Cylinders 
^^^^^^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst

   montepy.CylinderParAxis
   montepy.CylinderOnAxis

Planes 
^^^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst

   montepy.GeneralPlane
   montepy.AxisPlane


Data Inputs
-----------

Materials
^^^^^^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst
   
   montepy.Element
   montepy.Material
   montepy.Nuclide
   montepy.ThermalScatteringLaw
   


Cell Modifiers
^^^^^^^^^^^^^^

.. note:: 

   You will rarely create these directly,
   rather use the corresponding property in :class:`montepy.Cell`.

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst
   

   montepy.data_inputs.fill.Fill
   montepy.data_inputs.importance.Importance
   montepy.data_inputs.lattice.LatticeType
   montepy.data_inputs.lattice_input.LatticeInput
   montepy.data_inputs.universe_input.UniverseInput
   montepy.data_inputs.volume.Volume


Misc.
^^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst
   
   montepy.Mode
   montepy.Transform

Developer Focused Objects
-------------------------

Abstract Classes
^^^^^^^^^^^^^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst
   
   montepy.mcnp_object.MCNP_Object
   montepy.data_inputs.cell_modifier.CellModifierInput
   montepy.data_inputs.data_input.DataInputAbstract
   montepy.data_inputs.data_input.ForbiddenDataInput
   montepy.numbered_mcnp_object.Numbered_MCNP_Object
   montepy.numbered_object_collection.NumberedDataObjectCollection
   montepy.numbered_object_collection.NumberedObjectCollection
   montepy.mcnp_object._ExceptionContextAdder
   montepy.input_parser.parser_base.MetaBuilder
   montepy.input_parser.parser_base.SLY_Supressor



Enumerations
^^^^^^^^^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst

   montepy.geometry_operators.Operator
   montepy.particle.Particle
   montepy.SurfaceType
   montepy.input_parser.shortcuts.Shortcuts
   montepy.input_parser.block_type.BlockType

Universal Utilities and constants
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:

   montepy.exceptions
   montepy.utilities

   
Object Builders
^^^^^^^^^^^^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:

   montepy.data_inputs.data_parser.parse_data
   montepy.input_parser.input_syntax_reader
   montepy.surfaces.surface_builder.parse_surface

Parser Data Types
^^^^^^^^^^^^^^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst

   montepy.input_parser.input_file.MCNP_InputFile
   montepy.input_parser.mcnp_input.Input
   montepy.input_parser.mcnp_input.Jump
   montepy.input_parser.mcnp_input.Message
   montepy.input_parser.mcnp_input.ParsingNode
   montepy.input_parser.mcnp_input.ReadInput
   montepy.input_parser.mcnp_input.Title
   montepy.input_parser.syntax_node.ClassifierNode
   montepy.input_parser.syntax_node.CommentNode
   montepy.input_parser.syntax_node.GeometryTree
   montepy.input_parser.syntax_node.ListNode
   montepy.input_parser.syntax_node.MaterialsNode
   montepy.input_parser.syntax_node.PaddingNode
   montepy.input_parser.syntax_node.ParametersNode
   montepy.input_parser.syntax_node.ParticleNode
   montepy.input_parser.syntax_node.ShortcutNode
   montepy.input_parser.syntax_node.SyntaxNode
   montepy.input_parser.syntax_node.SyntaxNodeBase
   montepy.input_parser.syntax_node.ValueNode


Parsers 
^^^^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst

   montepy.input_parser.parser_base.MCNP_Parser
   montepy.input_parser.cell_parser.CellParser
   montepy.input_parser.data_parser.DataParser
   montepy.input_parser.data_parser.ClassifierParser
   montepy.input_parser.data_parser.ParamOnlyDataParser
   montepy.input_parser.material_parser.MaterialParser
   montepy.input_parser.read_parser.ReadParser
   montepy.input_parser.surface_parser.SurfaceParser
   montepy.input_parser.tally_parser.TallyParser
   montepy.input_parser.tally_seg_parser.TallySegmentParser
   montepy.input_parser.thermal_parser.ThermalParser
   montepy.input_parser.tokens.MCNP_Lexer
   montepy.input_parser.tokens.ParticleLexer
   montepy.input_parser.tokens.CellLexer
   montepy.input_parser.tokens.DataLexer
   montepy.input_parser.tokens.SurfaceLexer




Deprecated Objects
------------------

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst

   montepy.data_inputs.isotope.Isotope
   montepy.data_inputs.material_component.MaterialComponent
