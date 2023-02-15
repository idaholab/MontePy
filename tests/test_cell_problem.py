from unittest import TestCase

import mcnpy
from mcnpy.cell import Cell
from mcnpy.input_parser.block_type import BlockType
from mcnpy.input_parser.mcnp_input import Input, Comment


class TestCellClass(TestCase):
    def test_bad_init(self):
        with self.assertRaises(TypeError):
            Cell("5")
        card = Input(["foo"], BlockType.CELL)
        with self.assertRaises(TypeError):
            Cell(card, "5")
        with self.assertRaises(TypeError):
            Cell(card, ["5"])

    def test_init(self):
        # test invalid cell number
        in_str = "foo"
        card = Input([in_str], BlockType.CELL)
        with self.assertRaises(mcnpy.errors.MalformedInputError):
            in_str = "foo bar"
            cell = Cell(card, Comment(["c " + in_str]))
        # test like feature unsupported
        in_str = "1 like 2"
        card = Input([in_str], BlockType.CELL)
        with self.assertRaises(mcnpy.errors.UnsupportedFeature):
            in_str = "foo bar"
            cell = Cell(card, Comment(["c " + in_str]))
        # test invalid material number
        in_str = "1 foo"
        card = Input([in_str], BlockType.CELL)
        with self.assertRaises(mcnpy.errors.MalformedInputError):
            cell = Cell(card)
        # test invalid material density
        in_str = "1 1 foo"
        card = Input([in_str], BlockType.CELL)
        with self.assertRaises(mcnpy.errors.MalformedInputError):
            cell = Cell(card)
        # tests void cell
        in_str = "1 0 2"
        card = Input([in_str], BlockType.CELL)
        cell = Cell(card)
        self.assertEqual(cell.old_number, 1)
        self.assertEqual(cell.number, 1)
        self.assertIsNone(cell.material)
        self.assertEqual(cell.old_mat_number, 0)
        self.assertIn(2, cell.old_surface_numbers)

        # test material cell
        for atom_dens, density in [(False, "-0.5"), (True, "0.5")]:
            in_str = f"1 1 {density} 2"
            card = Input([in_str], BlockType.CELL)
            cell = Cell(card)
            self.assertEqual(cell.old_mat_number, 1)
            if atom_dens:
                self.assertAlmostEqual(cell.atom_density, 0.5)
            else:
                self.assertAlmostEqual(cell.mass_density, 0.5)
            self.assertTrue(atom_dens == cell.is_atom_dens)

        # test parameter input
        in_str = "1 0 #2 u= 5 vol=20 trcl=5"
        card = Input([in_str], BlockType.CELL)
        cell = Cell(card)
        self.assertIn(2, cell.old_complement_numbers)
        self.assertEqual(cell.parameters["TRCL"]["data"][0].value, 5.0)

    # TODO test updating cell geometry once done
    def test_cell_validator(self):
        cell = Cell()
        with self.assertRaises(mcnpy.errors.IllegalState):
            cell.validate()
        with self.assertRaises(mcnpy.errors.IllegalState):
            cell.format_for_mcnp_input((6, 2, 0))
        cell.mass_density = 5.0
        with self.assertRaises(mcnpy.errors.IllegalState):
            cell.validate()
        del cell.mass_density

    # TODO test geometry stuff

    def test_number_setter(self):
        in_str = "1 0 2"
        card = Input([in_str], BlockType.CELL)
        cell = Cell(card)
        cell.number = 5
        self.assertEqual(cell.number, 5)
        with self.assertRaises(TypeError):
            cell.number = "5"
        with self.assertRaises(ValueError):
            cell.number = -5

    def test_cell_density_setter(self):
        in_str = "1 1 0.5 2"
        card = Input([in_str], BlockType.CELL)
        cell = Cell(card)
        cell.mass_density = 1.5
        self.assertEqual(cell._density, 1.5)
        self.assertEqual(cell.mass_density, 1.5)
        self.assertFalse(cell.is_atom_dens)
        with self.assertRaises(AttributeError):
            _ = cell.atom_density
        cell.atom_density = 1.6
        self.assertEqual(cell._density, 1.6)
        self.assertEqual(cell.atom_density, 1.6)
        self.assertTrue(cell.is_atom_dens)
        with self.assertRaises(AttributeError):
            _ = cell.mass_density
        with self.assertRaises(TypeError):
            cell.atom_density = (5, True)
        with self.assertRaises(TypeError):
            cell.mass_density = "five"
        with self.assertRaises(ValueError):
            cell.atom_density = -1.5
        with self.assertRaises(ValueError):
            cell.mass_density = -5

    def test_cell_density_deleter(self):
        in_str = "1 1 0.5 2"
        card = Input([in_str], BlockType.CELL)
        cell = Cell(card)
        del cell.mass_density
        self.assertIsNone(cell.mass_density)
        cell.atom_density = 1.0
        del cell.atom_density
        self.assertIsNone(cell.atom_density)

    def test_cell_sorting(self):
        in_str = "1 1 0.5 2"
        card = Input([in_str], BlockType.CELL)
        cell1 = Cell(card)
        in_str = "2 1 0.5 2"
        card = Input([in_str], BlockType.CELL)
        cell2 = Cell(card)
        test_sort = sorted([cell2, cell1])
        answer = [cell1, cell2]
        for i, cell in enumerate(test_sort):
            self.assertEqual(cell, answer[i])

    def test_cell_parameters_setting(self):
        in_str = "1 1 0.5 2"
        card = Input([in_str], BlockType.CELL)
        cell = Cell(card)
        params = {"FILL": "5"}
        cell.parameters = params
        self.assertEqual(params, cell.parameters)
        with self.assertRaises(TypeError):
            cell.parameters = []

    def test_cell_str(self):
        in_str = "1 1 0.5 2"
        card = Input([in_str], BlockType.CELL)
        cell = Cell(card)
        self.assertEqual(str(cell), "CELL: 1, mat: 0, DENS: 0.5 g/cm3")
        self.assertEqual(
            repr(cell), "CELL: 1 \nVoid material \ndensity: 0.5 atom/b-cm\n\n"
        )

    def test_cell_paremeters_no_eq(self):
        in_str = f"1 0 -1 PWT 1.0"
        card = Input([in_str], BlockType.CELL)
        cell = Cell(card)
        self.assertEqual(cell.parameters["PWT"]["data"][0].value, 1.0)
