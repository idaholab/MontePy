from unittest import TestCase

import mcnpy
from mcnpy.cell import Cell
from mcnpy.input_parser.block_type import BlockType
from mcnpy.input_parser.mcnp_input import Card, Comment


class TestCellClass(TestCase):
    def test_init(self):
        # test invalid cell number
        card = Card(BlockType.CELL, ["foo"])
        with self.assertRaises(mcnpy.errors.MalformedInputError):
            cell = Cell(card, Comment(["foo", "bar"]))
        # test like feature unsupported
        card = Card(BlockType.CELL, ["1", "like", "2"])
        with self.assertRaises(mcnpy.errors.UnsupportedFeature):
            cell = Cell(card, Comment(["foo", "bar"]))
        # test invalid material number
        card = Card(BlockType.CELL, ["1", "foo"])
        with self.assertRaises(mcnpy.errors.MalformedInputError):
            cell = Cell(card)
        # test invalid material density
        card = Card(BlockType.CELL, ["1", "1", "foo"])
        with self.assertRaises(mcnpy.errors.MalformedInputError):
            cell = Cell(card)
        # tests void cell
        card = Card(BlockType.CELL, ["1", "0", "2"])
        cell = Cell(card)
        self.assertEqual(cell.old_cell_number, 1)
        self.assertEqual(cell.cell_number, 1)
        # self.assertIsNone(cell.material)
        self.assertEqual(cell.old_mat_number, 0)
        self.assertIn(2, cell.old_surface_numbers)

        # test material cell
        for atom_dens, density in [(False, "-0.5"), (True, "0.5")]:
            card = Card(BlockType.CELL, ["1", "1", density, "2"])
            cell = Cell(card)
            self.assertEqual(cell.old_mat_number, 1)
            self.assertAlmostEqual(cell.density, 0.5)
            self.assertTrue(atom_dens == cell.is_atom_dens)

        # test parameter input
        card = Card(BlockType.CELL, ["1", "0", "#2", "imp:n=1", "U=", "5", "VOL=20"])
        cell = Cell(card)
        self.assertIn(2, cell.old_complement_numbers)
        self.assertEqual(cell.parameters["IMP:N"], "1")
        self.assertEqual(cell.parameters["U"], "5")
        self.assertEqual(cell.parameters["VOL"], "20")

    def test_geometry_logic_string_setter(self):
        card = Card(BlockType.CELL, ["1", "0", "2"])
        cell = Cell(card)
        cell.geometry_logic_string = "1 2"
        self.assertEqual(cell.geometry_logic_string, "1 2")
        with self.assertRaises(AssertionError):
            cell.geometry_logic_string = 1

    def test_cell_number_setter(self):
        card = Card(BlockType.CELL, ["1", "0", "2"])
        cell = Cell(card)
        cell.cell_number = 5
        self.assertEqual(cell.cell_number, 5)
        with self.assertRaises(AssertionError):
            cell.cell_number = "5"

    def test_cell_density_setter(self):
        card = Card(BlockType.CELL, ["1", "1", "0.5" "2"])
        cell = Cell(card)
        cell.density = (1.5, False)
        self.assertEqual(cell.density, 1.5)
        self.assertFalse(cell.is_atom_dens)
        cell.density = (1.5, True)
        self.assertEqual(cell.density, 1.5)
        self.assertTrue(cell.is_atom_dens)
