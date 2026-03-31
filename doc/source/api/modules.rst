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

.. suppresses error with toctree 

.. toctree::
   :hidden:

   api/generated/montepy.surface_collection.Surfaces

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
   montepy.UnitHalfSpace


Cylinders
^^^^^^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst

   montepy.XCylinder
   montepy.YCylinder
   montepy.ZCylinder
   montepy.CylinderOnAxis
   montepy.XCylinderParAxis
   montepy.YCylinderParAxis
   montepy.ZCylinderParAxis
   montepy.CylinderParAxis

Planes
^^^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst

   montepy.XPlane
   montepy.YPlane
   montepy.ZPlane
   montepy.AxisPlane
   montepy.GeneralPlane


Spheres
^^^^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst

   montepy.SphereAtOrigin
   montepy.XSphere
   montepy.YSphere
   montepy.ZSphere
   montepy.SphereOnAxis
   montepy.GeneralSphere


Cones
^^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst

   montepy.XCone
   montepy.YCone
   montepy.ZCone
   montepy.ConeOnAxis
   montepy.XConeParAxis
   montepy.YConeParAxis
   montepy.ZConeParAxis
   montepy.ConeParAxis


Quadrics
^^^^^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst

   montepy.AxisAlignedQuadric
   montepy.GeneralQuadric


Tori
^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst

   montepy.XTorus
   montepy.YTorus
   montepy.ZTorus
   montepy.Torus


Macrobodies
^^^^^^^^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst

   montepy.Box
   montepy.RectangularParallelepiped
   montepy.SphereMacrobody
   montepy.RightCircularCylinder
   montepy.RightHexagonalPrism
   montepy.RightEllipticalCylinder
   montepy.TruncatedRightCone
   montepy.Ellipsoid
   montepy.Wedge
   montepy.ArbitraryPolyhedron


Data Inputs
-----------

Materials
^^^^^^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: myclass.rst
   
   montepy.Element
   montepy.Library
   montepy.Material
   montepy.Nucleus
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

   montepy.data_inputs.DataInput
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
   montepy._singleton.SingletonGroup
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
   montepy.LibraryType
   montepy.particle.Particle
   montepy.SurfaceType
   montepy.input_parser.shortcuts.Shortcuts
   montepy.input_parser.block_type.BlockType

Universal Utilities and constants
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   montepy.constants
   montepy.exceptions
   montepy.utilities


   
Object Builders
^^^^^^^^^^^^^^^

.. autosummary::
   :toctree: generated
   :nosignatures:

   montepy.data_inputs.data_parser.parse_data
   montepy.input_parser.input_syntax_reader.read_input_syntax
   montepy.input_parser.input_syntax_reader.read_data
   montepy.input_parser.input_syntax_reader.read_front_matters
   montepy.surfaces.surface_builder.parse_surface


Type Aliases
^^^^^^^^^^^^

.. autodata:: montepy.mcnp_object.InitInput
   :no-value:

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
