from unittest import TestCase

import mcnpy
from mcnpy.geometry_operators import Operator
from mcnpy.surfaces.half_space import HalfSpace, UnitHalfSpace


class TestHalfSpaceUnit(TestCase):
    def test_init(self):
        surface = mcnpy.surfaces.CylinderOnAxis()
        node = mcnpy.input_parser.syntax_node.GeometryTree("hi", [], "*", " ", " ")
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
        surface = mcnpy.surfaces.CylinderOnAxis()
        cell = mcnpy.Cell()
        half_space = -surface & ~cell
        cells, surfaces = half_space._get_leaf_objects()
        self.assertEqual(cells, {cell})
        self.assertEqual(surfaces, {surface})

    def test_len(self):
        surface = mcnpy.surfaces.CylinderOnAxis()
        cell = mcnpy.Cell()
        half_space = -surface & ~cell
        self.assertEqual(len(half_space), 2)

    def test_eq(self):
        cell1 = mcnpy.Cell()
        cell2 = mcnpy.Cell()
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
        cell1 = mcnpy.Cell()
        cell1.number = 1
        cell2 = mcnpy.Cell()
        cell2.number = 2
        half_space = ~cell1 | ~cell2
        self.assertEqual(str(half_space), "(#1:#2)")
        half_space = ~cell1 & ~cell2
        self.assertEqual(str(half_space), "(#1*#2)")
        half_space = ~(~cell1 & ~cell2)
        self.assertEqual(str(half_space), "#(#1*#2)")


class TestUnitHalfSpaceUnit(TestCase):
    def test_init(self):
        node = mcnpy.input_parser.syntax_node.ValueNode("123", float)
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
        self.assertEqual(str(half_space), "#1")
        cell = mcnpy.Cell()
        cell.number = 1
        half_space.divider = cell
        self.assertEqual(str(half_space), "#1")


class TestGeometryIntegration(TestCase):
    def test_surface_half_space(self):
        surface = mcnpy.surfaces.cylinder_on_axis.CylinderOnAxis()
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
        cell = mcnpy.Cell()
        half_space = ~cell
        self.assertIsInstance(half_space, HalfSpace)
        self.assertIsInstance(half_space, UnitHalfSpace)
        self.assertIs(half_space.divider, cell)
        self.assertTrue(half_space.side)
        with self.assertRaises(TypeError):
            half_space = cell & cell
        with self.assertRaises(TypeError):
            half_space = cell | cell
        with self.assertRaises(TypeError):
            half_space = +cell
        with self.assertRaises(TypeError):
            half_space = -cell

    def test_intersect_half_space(self):
        cell1 = ~mcnpy.Cell()
        cell2 = ~mcnpy.Cell()
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
        cell1 = ~mcnpy.Cell()
        cell2 = ~mcnpy.Cell()
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
        cell1 = ~mcnpy.Cell()
        cell2 = ~mcnpy.Cell()
        half_space1 = cell1 | cell2
        half_space = ~half_space1
        self.assertIsInstance(half_space, HalfSpace)
        self.assertIs(half_space.operator, Operator.COMPLEMENT)
        self.assertIs(half_space.left, half_space1)
        self.assertIsNone(half_space.right)

    def test_iand_recursion(self):
        cell1 = mcnpy.Cell()
        cell2 = mcnpy.Cell()
        cell3 = mcnpy.Cell()
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
        # test with complement
        half_space1 = ~(~cell1 & ~cell2)
        half_space1 &= ~cell2
        self.assertEqual(half_space1.left, ~(~cell1 & ~cell2))
        self.assertEqual(half_space1.right, ~cell2)

    def test_ior_recursion(self):
        cell1 = ~mcnpy.Cell()
        cell2 = ~mcnpy.Cell()
        half_space = cell1 | cell2
        half_space |= cell1
        self.assertIs(half_space.left, cell1)
        self.assertNotIsInstance(half_space.right, UnitHalfSpace)
        self.assertIs(half_space.right.left, cell2)
        self.assertIs(half_space.right.right, cell1)
        self.assertEqual(half_space.operator, Operator.UNION)
        self.assertEqual(len(half_space), 3)
        for i in range(1, 100):
            half_space |= cell1
            self.assertEqual(len(half_space), i + 3)
        with self.assertRaises(TypeError):
            half_space |= "hi"
        # test with complement
        half_space1 = ~(~cell1 | ~cell2)
        half_space1 |= ~cell2
        self.assertEqual(half_space1.left, ~(~cell1 | ~cell2))
        self.assertEqual(half_space1.right, ~cell2)
