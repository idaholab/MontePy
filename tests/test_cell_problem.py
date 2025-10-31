# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
from hypothesis import given, note, strategies as st
import pytest

import montepy
from montepy.cell import Cell
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input


def test_bad_init():
    with pytest.raises(TypeError):
        Cell(5)


def test_cell_validator():
    cell = Cell()
    with pytest.raises(montepy.exceptions.IllegalState):
        cell.validate()
    with pytest.raises(montepy.exceptions.IllegalState):
        cell.format_for_mcnp_input((6, 2, 0))
    cell.mass_density = 5.0
    with pytest.raises(montepy.exceptions.IllegalState):
        cell.validate()
    del cell.mass_density


def test_number_setter():
    cell = Cell("1 0 2")
    cell.number = 5
    assert cell.number == 5
    with pytest.raises(TypeError):
        cell.number = "5"
    with pytest.raises(ValueError):
        cell.number = -5


def test_cell_density_setter():
    in_str = "1 1 0.5 2"
    cell = Cell(in_str)
    cell.mass_density = 1.5
    assert cell._density == 1.5
    assert cell.mass_density == 1.5
    assert not cell.is_atom_dens
    with pytest.raises(AttributeError):
        _ = cell.atom_density
    cell.atom_density = 1.6
    assert cell._density == 1.6
    assert cell.atom_density == 1.6
    assert cell.is_atom_dens
    with pytest.raises(AttributeError):
        _ = cell.mass_density
    with pytest.raises(TypeError):
        cell.atom_density = (5, True)
    with pytest.raises(TypeError):
        cell.mass_density = "five"
    with pytest.raises(ValueError):
        cell.atom_density = -1.5
    with pytest.raises(ValueError):
        cell.mass_density = -5


def test_cell_str(self):
    in_str = "1 1 0.5 2"
    card = Input([in_str], BlockType.CELL)
    cell = Cell(card)
    self.assertEqual(str(cell), "CELL: 1, mat: 0, DENS: 0.5 atom/b-cm")
    self.assertEqual(repr(cell), "CELL: 1 \nVoid material \ndensity: 0.5 atom/b-cm\n")
    in_str = "1 0 -2 imp:n=1 "
    cell = montepy.Cell(in_str)
    # change line length
    old_version = montepy.MCNP_VERSION
    montepy.MCNP_VERSION = (5, 1, 60)
    assert cell.mcnp_str() == in_str
    montepy.MCNP_VERSION = old_version


def test_cell_density_deleter():
    in_str = "1 1 0.5 2"
    cell = Cell(in_str)
    del cell.mass_density
    assert cell.mass_density is None
    cell.atom_density = 1.0
    del cell.atom_density
    assert cell.atom_density is None


def test_cell_sorting():
    in_str = "1 1 0.5 2"
    cell1 = Cell(in_str)
    in_str = "2 1 0.5 2"
    cell2 = Cell(in_str)
    test_sort = sorted([cell2, cell1])
    answer = [cell1, cell2]
    for i, cell in enumerate(test_sort):
        assert cell == answer[i]


def test_cell_parameters_setting():
    in_str = "1 1 0.5 2"
    cell = Cell(in_str)
    params = {"FILL": "5"}
    cell.parameters = params
    assert params == cell.parameters
    with pytest.raises(TypeError):
        cell.parameters = []


def test_cell_str():
    in_str = "1 1 0.5 2"
    cell = Cell(in_str)
    assert str(cell) == "CELL: 1, mat: 0, DENS: 0.5 atom/b-cm"
    assert repr(cell) == "CELL: 1 \nVoid material \ndensity: 0.5 atom/b-cm\n"
    in_str = "1 0 -2 imp:n=1 "
    cell = montepy.Cell(in_str)
    # change line length
    old_version = montepy.MCNP_VERSION
    montepy.MCNP_VERSION = (5, 1, 60)
    assert cell.mcnp_str() == in_str
    montepy.MCNP_VERSION = old_version


def test_cell_paremeters_no_eq():
    in_str = f"1 0 -1 PWT 1.0"
    cell = Cell(in_str)
    assert cell.parameters["PWT"]["data"][0].value == 1.0


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
    input_obj = Input([line], BlockType.CELL)
    cell = Cell(input_obj)
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


def test_blank_num_init():
    cell = Cell(number=5)
    assert cell.number == 5
    with pytest.raises(TypeError):
        Cell(number="hi")
    with pytest.raises(ValueError):
        Cell(number=-1)


@pytest.mark.parametrize("line", ["foo", "foo bar", "1 foo", "1 1 foo"])
def test_malformed_init(line):
    with pytest.raises(montepy.exceptions.MalformedInputError):
        input_obj = Input([line], BlockType.CELL)
        Cell(input_obj)


@pytest.mark.parametrize("line", ["1 like 2"])
def test_malformed_init(line):
    with pytest.raises(montepy.exceptions.UnsupportedFeature):
        input = Input([line], BlockType.CELL)
        Cell(input, jit_parse=False)


@given(
    st.booleans(),
    st.booleans(),
    st.booleans(),
    st.integers(),
    st.integers(),
    st.integers(1),
    st.integers(1),
)
@pytest.mark.filterwarnings("ignore::montepy.exceptions.LineExpansionWarning")
def test_cell_clone(
    has_mat, clone_region, clone_material, start_num, step, other_start, other_step
):
    if has_mat:
        cell = Cell("1 1 -0.5 2")
    else:
        cell = Cell("1 0 2")
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
    # cell already created above
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
    note(output)
    input = montepy.input_parser.mcnp_input.Input(
        output, montepy.input_parser.block_type.BlockType.CELL
    )
    new_cell = montepy.Cell(input)
    if cell.material is not None:
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
    cell = Cell("1 1 -0.5 2")
    problem = montepy.MCNP_Problem("")
    surf = montepy.Surface("2 SO 5")
    problem.surfaces.append(surf)
    mat = montepy.Material(number=1)
    problem.materials.append(mat)
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
    cell = Cell("1 0 2")
    surf = montepy.surfaces.surface.Surface()
    surf.number = 2
    surfs = montepy.surface_collection.Surfaces([surf])
    cell.update_pointers([], [], surfs)
    with pytest.raises(error):
        cell.clone(*args)


def test_bad_setattr():
    cell = montepy.Cell()
    with pytest.raises(AttributeError):
        cell.nuber = 5
    cell._nuber = 5
    assert cell._nuber == 5


def verify_export(cell):
    output = cell.format_for_mcnp_input((6, 3, 0))
    print("cell output", output)
    assert "\n".join(output) == cell.mcnp_str((6, 3, 0))
    new_cell = montepy.Cell("\n".join(output))
    for attr in {
        "number",
        "old_mat_number",
        "old_universe_number",
        "lattice_type",
        "mass_density",
        "atom_density",
        "is_atom_dens",
    }:
        try:
            old_attr = getattr(cell, attr)
            new_attr = getattr(new_cell, attr)
            # jank override
            if attr == "old_universe_number" and cell.universe:
                old_attr = cell.universe.number
        except AttributeError as e:
            if "density" not in attr:
                raise e
            else:
                continue
        print(f"attr: {attr}, old: {old_attr}, new: {new_attr}")
        if old_attr is not None:
            if isinstance(old_attr, float):
                assert old_attr == pytest.approx(new_attr)
            else:
                assert old_attr == new_attr
        else:
            assert new_attr is None
    for attr in {
        "hidden_transform",
        "multiple_universes",
        "old_universe_number",
        "old_universe_numbers",
        "transform",
    }:
        old_attr = getattr(cell.fill, attr)
        new_attr = getattr(new_cell.fill, attr)
        # jank override
        if attr == "old_universe_number" and cell.fill.universe:
            old_attr = cell.fill.universe.number
        print(f"fill attr: {attr}, old: {old_attr}, new: {new_attr}")
        if old_attr is not None:
            if isinstance(old_attr, float):
                assert old_attr == pytest.approx(new_attr)
            else:
                assert old_attr == new_attr
        else:
            assert new_attr is None
