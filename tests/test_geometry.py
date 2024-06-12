# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from unittest import TestCase

import montepy
from montepy.geometry_operators import Operator
from montepy.input_parser import syntax_node
from montepy.surfaces.half_space import HalfSpace, UnitHalfSpace


class TestHalfSpaceUnit(TestCase):
    def test_init(self):
        surface = montepy.surfaces.CylinderOnAxis()
        node = montepy.input_parser.syntax_node.GeometryTree("hi", {}, "*", " ", " ")
        half_space = HalfSpace(+surface, Operator.UNION, -surface, node)
        self.assertIs(half_space.operator, Operator.UNION)
        self.assertEqual(half_space.left, +surface)
        self.assertEqual(half_space.right, -surface)
        self.assertIs(half_space.node, node)
        with self.assertRaises(TypeError):
            HalfSpace(surface, Operator.UNION)
        with self.assertRaises(TypeError):
            HalfSpace(+surface, "hi")
        with self.assertRaises(TypeError):
            HalfSpace(+surface, Operator.UNION, surface)
        with self.assertRaises(TypeError):
            HalfSpace(+surface, Operator.UNION, -surface, "hi")
        with self.assertRaises(ValueError):
            HalfSpace(+surface, Operator.UNION)
        with self.assertRaises(ValueError):
            HalfSpace(+surface, Operator.INTERSECTION)

    def test_get_leaves(self):
        surface = montepy.surfaces.CylinderOnAxis()
        cell = montepy.Cell()
        half_space = -surface & ~cell
        cells, surfaces = half_space._get_leaf_objects()
        self.assertEqual(cells, {cell})
        self.assertEqual(surfaces, {surface})

    def test_len(self):
        surface = montepy.surfaces.CylinderOnAxis()
        cell = montepy.Cell()
        half_space = -surface & ~cell
        self.assertEqual(len(half_space), 2)

    def test_eq(self):
        cell1 = montepy.Cell()
        cell2 = montepy.Cell()
        half1 = ~cell1 & ~cell2
        self.assertTrue(half1 == half1)
        half2 = ~cell1 | ~cell2
        self.assertTrue(half1 != half2)
        half2 = ~cell1 & ~cell1
        self.assertTrue(half1 != half2)
        half2 = ~cell2 & ~cell2
        self.assertTrue(half1 != half2)
        half2 = ~half1
        half2._operator = Operator.INTERSECTION
        self.assertTrue(half1 != half2)
        with self.assertRaises(TypeError):
            half1 == "hi"

    def test_str(self):
        cell1 = montepy.Cell()
        cell1.number = 1
        cell2 = montepy.Cell()
        cell2.number = 2
        half_space = ~cell1 | ~cell2
        self.assertEqual(str(half_space), "(#1:#2)")
        half_space = ~cell1 & ~cell2
        self.assertEqual(str(half_space), "(#1*#2)")
        half_space = ~(~cell1 & ~cell2)
        self.assertEqual(str(half_space), "#(#1*#2)")
        # test that no errors occur
        repr(half_space)


class TestUnitHalfSpaceUnit(TestCase):
    def test_init(self):
        node = montepy.input_parser.syntax_node.ValueNode("123", float)
        half_space = UnitHalfSpace(123, True, False, node)
        self.assertEqual(half_space.divider, 123)
        self.assertTrue(half_space.side)
        self.assertTrue(not half_space.is_cell)
        self.assertIs(half_space.node, node)
        with self.assertRaises(TypeError):
            UnitHalfSpace("hi", True, False)
        with self.assertRaises(TypeError):
            half_space = UnitHalfSpace(123, "hi", False)
        with self.assertRaises(TypeError):
            half_space = UnitHalfSpace(123, True, "hi")
        with self.assertRaises(TypeError):
            half_space = UnitHalfSpace(123, True, False, "hi")

    def test_eq(self):
        half1 = UnitHalfSpace(1, True, False)
        self.assertTrue(half1 == half1)
        half2 = UnitHalfSpace(2, True, False)
        self.assertTrue(half1 != half2)
        half2 = UnitHalfSpace(1, False, False)
        self.assertTrue(half1 != half2)
        half2 = UnitHalfSpace(1, True, True)
        self.assertTrue(half1 != half2)
        with self.assertRaises(TypeError):
            half1 == "hi"

    def test_str(self):
        half_space = UnitHalfSpace(1, True, False)
        self.assertEqual(str(half_space), "+1")
        half_space.side = False
        self.assertEqual(str(half_space), "-1")
        half_space.is_cell = True
        self.assertEqual(str(half_space), "1")
        cell = montepy.Cell()
        cell.number = 1
        half_space.divider = cell
        self.assertEqual(str(half_space), "1")


class TestGeometryIntegration(TestCase):
    def test_surface_half_space(self):
        surface = montepy.surfaces.cylinder_on_axis.CylinderOnAxis()
        half_space = +surface
        self.assertIsInstance(half_space, HalfSpace)
        self.assertIsInstance(half_space, UnitHalfSpace)
        self.assertIs(half_space.divider, surface)
        self.assertTrue(half_space.side)
        half_space = -surface
        self.assertIsInstance(half_space, HalfSpace)
        self.assertIsInstance(half_space, UnitHalfSpace)
        self.assertIs(half_space.divider, surface)
        self.assertTrue(not half_space.side)
        with self.assertRaises(TypeError):
            half_space = surface & surface
        with self.assertRaises(TypeError):
            half_space = surface | surface
        with self.assertRaises(TypeError):
            half_space = ~surface

    def test_cell_half_space(self):
        cell = montepy.Cell()
        half_space = ~cell
        self.assertIsInstance(half_space, HalfSpace)
        self.assertIs(half_space.left.divider, cell)
        self.assertTrue(half_space.left.side)
        with self.assertRaises(TypeError):
            half_space = cell & cell
        with self.assertRaises(TypeError):
            half_space = cell | cell
        with self.assertRaises(TypeError):
            half_space = +cell
        with self.assertRaises(TypeError):
            half_space = -cell

    def test_intersect_half_space(self):
        cell1 = ~montepy.Cell()
        cell2 = ~montepy.Cell()
        half_space = cell1 & cell2
        self.assertIsInstance(half_space, HalfSpace)
        self.assertIs(half_space.operator, Operator.INTERSECTION)
        self.assertIs(half_space.left, cell1)
        self.assertIs(half_space.right, cell2)
        with self.assertRaises(TypeError):
            cell1 & "hi"
        with self.assertRaises(TypeError):
            "hi" & cell1
        with self.assertRaises(TypeError):
            cell2 + cell1
        with self.assertRaises(TypeError):
            cell2 - cell1

    def test_union_half_space(self):
        cell1 = ~montepy.Cell()
        cell2 = ~montepy.Cell()
        half_space = cell1 | cell2
        self.assertIsInstance(half_space, HalfSpace)
        self.assertIs(half_space.operator, Operator.UNION)
        self.assertIs(half_space.left, cell1)
        self.assertIs(half_space.right, cell2)
        with self.assertRaises(TypeError):
            cell1 | "hi"
        with self.assertRaises(TypeError):
            "hi" | cell1

    def test_invert_half_space(self):
        cell1 = ~montepy.Cell()
        cell2 = ~montepy.Cell()
        half_space1 = cell1 | cell2
        half_space = ~half_space1
        self.assertIsInstance(half_space, HalfSpace)
        self.assertIs(half_space.operator, Operator.COMPLEMENT)
        self.assertIs(half_space.left, half_space1)
        self.assertIsNone(half_space.right)

    def test_iand_recursion(self):
        cell1 = montepy.Cell()
        cell2 = montepy.Cell()
        cell3 = montepy.Cell()
        half_space = ~cell1 & ~cell2
        cell1.number = 1
        cell2.number = 2
        cell3.number = 3
        cell3.geometry = half_space
        half_space &= ~cell1
        self.assertEqual(half_space.left, ~cell1)
        self.assertNotIsInstance(half_space.right, UnitHalfSpace)
        self.assertEqual(half_space.right.left, ~cell2)
        self.assertEqual(half_space.right.right, ~cell1)
        self.assertEqual(half_space.operator, Operator.INTERSECTION)
        self.assertEqual(len(half_space), 3)
        for i in range(1, 100):
            half_space &= ~cell1
            self.assertEqual(len(half_space), i + 3)
        with self.assertRaises(TypeError):
            half_space &= "hi"
        # test with unit halfspaces
        surf = montepy.surfaces.CylinderParAxis()
        # test going from leaf to tree
        half_space = -surf
        half_space &= +surf
        self.assertEqual(len(half_space), 2)
        # test with actual tree
        half_space = -surf | +surf
        half_space &= +surf
        self.assertEqual(len(half_space), 3)

    def test_ior_recursion(self):
        cell1 = ~montepy.Cell()
        cell2 = ~montepy.Cell()
        half_space = cell1 | cell2
        half_space |= cell1
        self.assertIs(half_space.left, cell1)
        self.assertNotIsInstance(half_space.right, UnitHalfSpace)
        self.assertEqual(half_space.right.left, cell2)
        self.assertEqual(half_space.right.right, cell1)
        self.assertEqual(half_space.operator, Operator.UNION)
        self.assertEqual(len(half_space), 3)
        for i in range(1, 100):
            half_space |= cell1
            self.assertEqual(len(half_space), i + 3)
        with self.assertRaises(TypeError):
            half_space |= "hi"
        # test with unit halfspaces
        surf = montepy.surfaces.CylinderParAxis()
        half_space = -surf
        half_space |= +surf
        self.assertEqual(len(half_space), 2)
        half_space = -surf | +surf
        half_space |= +surf
        self.assertEqual(len(half_space), 3)

    def test_parse_input_tree(self):
        # simplest intersection
        input = montepy.input_parser.mcnp_input.Input(
            ["1 0 1 -2"], montepy.input_parser.block_type.BlockType.CELL
        )
        parser = montepy.input_parser.cell_parser.CellParser()
        tree = parser.parse(input.tokenize())
        geometry = tree["geometry"]
        half_space = HalfSpace.parse_input_node(geometry)
        self.assertEqual(half_space.operator, Operator.INTERSECTION)
        self.assertEqual(half_space.left.divider, 1)
        self.assertTrue(half_space.left.side)
        self.assertTrue(not half_space.left.is_cell)
        self.assertEqual(half_space.right.divider, 2)
        self.assertTrue(not half_space.right.side)
        self.assertTrue(not half_space.right.is_cell)
        # Test type checking
        with self.assertRaises(TypeError):
            HalfSpace.parse_input_node("hi")
        # test assymetric
        input = montepy.input_parser.mcnp_input.Input(
            ["1 0 #2"], montepy.input_parser.block_type.BlockType.CELL
        )
        parser = montepy.input_parser.cell_parser.CellParser()
        tree = parser.parse(input.tokenize())
        geometry = tree["geometry"]
        half_space = HalfSpace.parse_input_node(geometry)
        self.assertEqual(half_space.operator, Operator.COMPLEMENT)
        self.assertEqual(half_space.left.divider, 2)
        self.assertTrue(half_space.left.side)
        self.assertTrue(half_space.left.is_cell)
        self.assertIsNone(half_space.right)
        # Test nested trees
        input = montepy.input_parser.mcnp_input.Input(
            ["1 0 1 -2 : 3"], montepy.input_parser.block_type.BlockType.CELL
        )
        parser = montepy.input_parser.cell_parser.CellParser()
        tree = parser.parse(input.tokenize())
        geometry = tree["geometry"]
        half_space = HalfSpace.parse_input_node(geometry)
        self.assertEqual(half_space.operator, Operator.UNION)
        self.assertNotIsInstance(half_space.left, UnitHalfSpace)
        self.assertIsInstance(half_space.right, UnitHalfSpace)
        self.assertEqual(half_space.left.operator, Operator.INTERSECTION)
        self.assertEqual(half_space.right.divider, 3)
        self.assertEqual(half_space.left.left.divider, 1)
        self.assertEqual(half_space.left.right.divider, 2)
        # test shift
        input = montepy.input_parser.mcnp_input.Input(
            ["1 0 #(1 2 3)"], montepy.input_parser.block_type.BlockType.CELL
        )
        parser = montepy.input_parser.cell_parser.CellParser()
        tree = parser.parse(input.tokenize())
        geometry = tree["geometry"]
        half_space = HalfSpace.parse_input_node(geometry)
        self.assertEqual(half_space.operator, Operator.COMPLEMENT)
        self.assertIsNone(half_space.right)
        self.assertEqual(half_space.left.operator, Operator.INTERSECTION)

    def test_update_tree_with_comment(self):
        input = montepy.input_parser.mcnp_input.Input(
            ["1 0 -1 $hi there", "      2"],
            montepy.input_parser.block_type.BlockType.CELL,
        )
        cell = montepy.Cell(input)
        geometry = cell.geometry
        geometry._update_values()

    def test_parse_input_value_node(self):
        node = montepy.input_parser.syntax_node.ValueNode("-1", float)
        half_space = UnitHalfSpace.parse_input_node(node)
        self.assertTrue(not half_space.is_cell)
        self.assertTrue(not half_space.side)
        self.assertEqual(half_space.divider, 1)
        half_space = UnitHalfSpace.parse_input_node(node, True)
        self.assertTrue(half_space.is_cell)
        self.assertTrue(half_space.side)
        self.assertEqual(half_space.divider, 1)
        node = montepy.input_parser.syntax_node.ValueNode("+1", float)
        half_space = UnitHalfSpace.parse_input_node(node, False)
        self.assertTrue(not half_space.is_cell)
        self.assertTrue(half_space.side)
        self.assertEqual(half_space.divider, 1)
        with self.assertRaises(TypeError):
            UnitHalfSpace.parse_input_node("hi", False)
        with self.assertRaises(TypeError):
            UnitHalfSpace.parse_input_node(node, "hi")

    def test_unit_divider_setter(self):
        cell = montepy.Cell()
        cell.number = 1
        parent = montepy.Cell()
        parent.number = 2
        node = montepy.input_parser.syntax_node.ValueNode("1", float)
        half_space = UnitHalfSpace.parse_input_node(node, True)
        cells = montepy.cells.Cells()
        cells.append(cell)
        half_space.update_pointers(cells, [], parent)
        self.assertIs(half_space.divider, cell)
        cell2 = montepy.Cell()
        # #madLads
        cell2.number = 4
        half_space.divider = cell2
        self.assertIs(half_space.divider, cell2)
        self.assertIn(cell2, parent.complements)
        # test with surface
        surf = montepy.surfaces.CylinderParAxis()
        surf.number = 5
        with self.assertRaises(TypeError):
            half_space.divider = surf
        half_space.is_cell = False
        half_space.divider = surf
        self.assertIs(half_space.divider, surf)
        self.assertIn(surf, parent.surfaces)
        with self.assertRaises(TypeError):
            half_space.divider = "hi"

    def test_unit_create_default_node(self):
        surf = montepy.surfaces.CylinderParAxis()
        surf.number = 1
        half_space = UnitHalfSpace(surf, True, False)
        half_space._ensure_has_nodes()
        node = half_space.node
        self.assertIsInstance(node, syntax_node.ValueNode)
        self.assertEqual(node.value, 1)
        self.assertEqual(node.format(), "1")
        # test with negative side
        half_space = UnitHalfSpace(surf, False, False)
        half_space._ensure_has_nodes()
        node = half_space.node
        self.assertEqual(node.format(), "-1")
        # test with int and not an object
        half_space = UnitHalfSpace(1, True, False)
        half_space._ensure_has_nodes()
        node = half_space.node
        self.assertIsInstance(node, syntax_node.ValueNode)
        self.assertEqual(node.value, 1)

    def test_tree_create_default_node(self):
        surf = montepy.surfaces.CylinderParAxis()
        surf.number = 1
        half_space = -surf | +surf
        half_space._ensure_has_nodes()
        node = half_space.node
        self.assertIsInstance(node, syntax_node.GeometryTree)
        self.assertEqual(node.operator, Operator.UNION)
        self.assertEqual(node.format(), "-1 : 1")
        # Test intersection
        half_space = -surf & +surf
        half_space._ensure_has_nodes()
        node = half_space.node
        self.assertEqual(node.operator, Operator.INTERSECTION)
        # Test complement
        half_space = ~(-surf | +surf)
        half_space._ensure_has_nodes()
        node = half_space.node
        self.assertEqual(node.operator, Operator.COMPLEMENT)
        self.assertEqual(node.format(), " #(-1 : 1)")
        # test cell complement
        cell = montepy.Cell()
        cell.number = 1
        half_space = ~cell
        half_space._ensure_has_nodes()
        node = half_space.node
        self.assertEqual(node.operator, Operator.COMPLEMENT)
        self.assertEqual(node.format(), " #1")

    def test_update_operators_in_node(self):
        surf = montepy.surfaces.CylinderParAxis()
        surf.number = 1
        half_space = -surf | +surf
        half_space._ensure_has_nodes()
        half_space.operator = Operator.INTERSECTION
        half_space._update_values()
        self.assertEqual(half_space.node.format(), "-1   1")
        del half_space.right
        half_space.operator = Operator.COMPLEMENT
        cell = montepy.Cell()
        cell.number = 1
        half_space.left = UnitHalfSpace(cell, True, True)
        half_space._update_values()
        self.assertEqual(half_space.node.format(), "  #1")
        # test with blank tree
        half_space = -surf & +surf
        half_space._update_values()
        self.assertEqual(half_space.node.format(), "-1 1")
        # test move to union
        # test centering
        half_space.node.nodes["operator"].append("  ")
        half_space.operator = Operator.UNION
        half_space._update_values()
        self.assertEqual(half_space.node.format(), "-1 : 1")
