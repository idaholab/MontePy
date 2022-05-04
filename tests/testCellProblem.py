from unittest import TestCase

import mcnpy
from mcnpy.cell import Cell
from mcnpy.input_parser.block_type import BlockType
from mcnpy.input_parser.mcnp_input import Card, Comment


class TestCellClass(TestCase):
    def test_init(self):
        # test invalid cell number
        in_str = "foo"
        card = Card([in_str], BlockType.CELL)
        with self.assertRaises(mcnpy.errors.MalformedInputError):
            in_str = "foo bar"
            cell = Cell(card, Comment([in_str], in_str.split()))
        # test like feature unsupported
        in_str = "1 like 2"
        card = Card([in_str], BlockType.CELL)
        with self.assertRaises(mcnpy.errors.UnsupportedFeature):
            in_str = "foo bar"
            cell = Cell(card, Comment([in_str], in_str.split()))
        # test invalid material number
        in_str = "1 foo"
        card = Card([in_str], BlockType.CELL)
        with self.assertRaises(mcnpy.errors.MalformedInputError):
            cell = Cell(card)
        # test invalid material density
        in_str = "1 1 foo"
        card = Card([in_str], BlockType.CELL)
        with self.assertRaises(mcnpy.errors.MalformedInputError):
            cell = Cell(card)
        # tests void cell
        in_str = "1 0 2"
        card = Card([in_str], BlockType.CELL)
        cell = Cell(card)
        self.assertEqual(cell.old_cell_number, 1)
        self.assertEqual(cell.cell_number, 1)
        self.assertIsNone(cell.material)
        self.assertEqual(cell.old_mat_number, 0)
        self.assertIn(2, cell.old_surface_numbers)

        # test material cell
        for atom_dens, density in [(False, "-0.5"), (True, "0.5")]:
            in_str = f"1 1 {density} 2"
            card = Card([in_str], BlockType.CELL)
            cell = Cell(card)
            self.assertEqual(cell.old_mat_number, 1)
            self.assertAlmostEqual(cell.density, 0.5)
            self.assertTrue(atom_dens == cell.is_atom_dens)

        # test parameter input
        in_str = "1 0 #2 imp:n=1 u= 5 vol=20"
        card = Card([in_str], BlockType.CELL)
        cell = Cell(card)
        self.assertIn(2, cell.old_complement_numbers)
        self.assertEqual(cell.parameters["IMP:N"], "1")
        self.assertEqual(cell.parameters["U"], "5")
        self.assertEqual(cell.parameters["VOL"], "20")

    def test_geometry_logic_string_setter(self):
        in_str = "1 0 2"
        card = Card([in_str], BlockType.CELL)
        cell = Cell(card)
        cell.geometry_logic_string = "1 2"
        self.assertEqual(cell.geometry_logic_string, "1 2")
        with self.assertRaises(AssertionError):
            cell.geometry_logic_string = 1

    def test_cell_number_setter(self):
        in_str = "1 0 2"
        card = Card([in_str], BlockType.CELL)
        cell = Cell(card)
        cell.cell_number = 5
        self.assertEqual(cell.cell_number, 5)
        with self.assertRaises(AssertionError):
            cell.cell_number = "5"

    def test_cell_density_setter(self):
        in_str = "1 1 0.5 2"
        card = Card([in_str], BlockType.CELL)
        cell = Cell(card)
        cell.density = (1.5, False)
        self.assertEqual(cell.density, 1.5)
        self.assertFalse(cell.is_atom_dens)
        cell.density = (1.5, True)
        self.assertEqual(cell.density, 1.5)
        self.assertTrue(cell.is_atom_dens)

    def test_cell_sorting(self):
        in_str = "1 1 0.5 2"
        card = Card([in_str], BlockType.CELL)
        cell1 = Cell(card)
        in_str = "2 1 0.5 2"
        card = Card([in_str], BlockType.CELL)
        cell2 = Cell(card)
        test_sort = sorted([cell2, cell1])
        answer = [cell1, cell2]
        for i, cell in enumerate(test_sort):
            self.assertEqual(cell, answer[i])
