# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from unittest import TestCase
import pytest

import montepy
from montepy.cell import Cell
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input


class TestCellClass(TestCase):
    def test_bad_init(self):
        with self.assertRaises(TypeError):
            Cell("5")

    # TODO test updating cell geometry once done
    def test_cell_validator(self):
        cell = Cell()
        with self.assertRaises(montepy.errors.IllegalState):
            cell.validate()
        with self.assertRaises(montepy.errors.IllegalState):
            cell.format_for_mcnp_input((6, 2, 0))
        cell.mass_density = 5.0
        with self.assertRaises(montepy.errors.IllegalState):
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
        self.assertEqual(str(cell), "CELL: 1, mat: 0, DENS: 0.5 atom/b-cm")
        self.assertEqual(
            repr(cell), "CELL: 1 \nVoid material \ndensity: 0.5 atom/b-cm\n\n"
        )

    def test_cell_paremeters_no_eq(self):
        in_str = f"1 0 -1 PWT 1.0"
        card = Input([in_str], BlockType.CELL)
        cell = Cell(card)
        self.assertEqual(cell.parameters["PWT"]["data"][0].value, 1.0)


@pytest.mark.parametrize(
    "line, is_void, mat_number, density, atom_dens, parameters",
    [
        ("1 0 2", True, 0, None, None, None),
        ("1 1 -10 2", False, 1, 10.0, False, None),
        ("1 1 10 2", False, 1, 10.0, True, None),
        (
            "1 0 #2 u= 5 vol=20 trcl=5",
            True,
            0,
            None,
            None,
            {"TRCL": 5.0, "U": 5.0, "VOL": 20.0},
        ),
        (
            "1 1 -1.0 1000 (-3000:-4000:-5000)(-6000:-7000:8000) -2000 -9000",
            False,
            1,
            1,
            False,
            None,
        ),
    ],
)
def test_init(line, is_void, mat_number, density, atom_dens, parameters):
    # test like feature unsupported
    # tests void cell
    input = Input([line], BlockType.CELL)
    cell = Cell(input)
    assert cell.old_number == 1
    assert cell.number == 1
    if is_void:
        assert cell.material is None
    else:
        assert cell.old_mat_number != 0
        if atom_dens:
            assert cell.is_atom_dens
            assert cell.atom_density == pytest.approx(density)
        else:
            assert not cell.is_atom_dens
            assert cell.mass_density == pytest.approx(density)
    assert cell.old_mat_number == mat_number
    if not parameters:
        return
    for parameter, value in parameters.items():
        assert cell.parameters[parameter]["data"][0].value == pytest.approx(value)


@pytest.mark.parametrize("line", ["foo", "foo bar", "1 foo", "1 1 foo"])
def test_malformed_init(line):
    with pytest.raises(montepy.errors.MalformedInputError):
        input = Input([line], BlockType.CELL)
        Cell(input)


@pytest.mark.parametrize("line", ["1 like 2"])
def test_malformed_init(line):
    with pytest.raises(montepy.errors.UnsupportedFeature):
        input = Input([line], BlockType.CELL)
        Cell(input)
