# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from hypothesis import given, note, strategies as st
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
            repr(cell), "CELL: 1 \nVoid material \ndensity: 0.5 atom/b-cm\n"
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


@given(
    st.booleans(),
    st.booleans(),
    st.booleans(),
    st.integers(),
    st.integers(),
    st.integers(1),
    st.integers(1),
)
@pytest.mark.filterwarnings("ignore::montepy.errors.LineExpansionWarning")
def test_cell_clone(
    has_mat, clone_region, clone_material, start_num, step, other_start, other_step
):
    if has_mat:
        input = Input(["1 1 -0.5 2"], BlockType.CELL)
    else:
        input = Input(["1 0 2"], BlockType.CELL)
    surf = montepy.surfaces.surface.Surface()
    surf.number = 2
    mat = montepy.data_inputs.material.Material()
    mat.number = 1
    surfs = montepy.surface_collection.Surfaces([surf])
    mats = montepy.materials.Materials([mat])
    if other_start <= 0 or other_step <= 0:
        with pytest.raises(ValueError):
            mats.starting_number = other_start
            mats.step = other_step
    else:
        for collect in (surfs, mats):
            collect.starting_number = other_start
            collect.step = other_step
    cell = Cell(input)
    cell.update_pointers([], mats, surfs)
    problem = montepy.MCNP_Problem("foo")
    problem.surfaces = surfs
    problem.materials = mats
    for prob in {None, problem}:
        cell.link_to_problem(prob)
        if prob is not None:
            prob.cells.append(cell)
        if start_num <= 0 or step <= 0:
            with pytest.raises(ValueError):
                cell.clone(clone_material, clone_region, start_num, step)
            return
        new_cell = cell.clone(clone_material, clone_region, start_num, step)
        verify_internal_links(new_cell)
        verify_clone_format(new_cell)
        assert new_cell is not cell
        assert new_cell.number != 1
        if start_num != 1:
            assert new_cell.number == start_num
        else:
            assert new_cell.number == start_num + step
        # force it to use the step
        if prob is not None:
            new_cell2 = cell.clone(clone_material, clone_region, start_num, step)
            if start_num != 1:
                assert new_cell2.number == start_num + step
            else:
                assert new_cell2.number == start_num + step * 2
        for attr in {"_importance", "_volume", "_fill"}:
            assert getattr(cell, attr) is not getattr(new_cell, attr)
        for attr in {"mass_density"}:
            assert getattr(cell, attr) == getattr(new_cell, attr)
            if attr == "mass_density":
                attr = "density_node"
            assert getattr(cell, f"_{attr}") is not getattr(new_cell, f"_{attr}")
        assert cell.geometry is not new_cell.geometry
        if clone_region:
            assert list(cell.surfaces)[0] is not list(new_cell.surfaces)[0]
            assert list(new_cell.surfaces)[0].number != list(cell.surfaces)[0].number
        else:
            assert list(cell.surfaces)[0] is list(new_cell.surfaces)[0]
        if clone_material:
            if cell.material is None:
                assert new_cell.material is None
            else:
                assert cell.material is not new_cell.material
                assert new_cell.material.number != cell.material.number
        else:
            assert cell.material is new_cell.material


def verify_internal_links(cell):
    # verify _number is linked in tree
    assert cell._number is cell._tree["cell_num"]
    assert cell._old_mat_number is cell._tree["material"]["mat_number"]
    assert cell.geometry.node is cell._tree["geometry"].left
    assert cell.importance._tree is cell._tree["parameters"]["imp:n"]


def verify_clone_format(cell):
    surf = list(cell.surfaces)[0]
    old_num = surf.number
    num = 1000
    surf.number = num
    output = cell.format_for_mcnp_input((6, 3, 0))
    input = montepy.input_parser.mcnp_input.Input(
        output, montepy.input_parser.block_type.BlockType.CELL
    )
    new_cell = montepy.Cell(input)
    if cell.material:
        mats = montepy.materials.Materials([cell.material])
    else:
        mats = []
    new_cell.update_pointers([], mats, montepy.surface_collection.Surfaces([surf]))
    for attr in {"number", "mass_density", "old_mat_number"}:
        assert getattr(cell, attr) == getattr(new_cell, attr)
    new_surf = list(new_cell.surfaces)[0]
    assert new_surf.number == num
    surf.number = old_num


def test_cell_clone_default():
    input = Input(["1 1 -0.5 2"], BlockType.CELL)
    cell = Cell(input)
    problem = montepy.MCNP_Problem("")
    problem.cells.append(cell)
    for prob in {problem, None}:
        cell.link_to_problem(prob)
        new_cell = cell.clone()
        assert new_cell.number != cell.number


@pytest.mark.parametrize(
    "args, error",
    [
        (("a", False, 1, 1), TypeError),
        ((False, "b", 1, 1), TypeError),
        ((False, False, "c", 1), TypeError),
        ((False, False, 1, "d"), TypeError),
        ((False, False, -1, 1), ValueError),
        ((False, False, 0, 1), ValueError),
        ((False, False, 1, 0), ValueError),
        ((False, False, 1, -1), ValueError),
    ],
)
def test_cell_clone_bad(args, error):
    input = Input(["1 0 2"], BlockType.CELL)
    cell = Cell(input)
    surf = montepy.surfaces.surface.Surface()
    surf.number = 2
    surfs = montepy.surface_collection.Surfaces([surf])
    cell.update_pointers([], [], surfs)
    with pytest.raises(error):
        cell.clone(*args)
