# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import copy
import io
from pathlib import Path

import pytest
import os

import montepy
from montepy.data_inputs import material, volume
from montepy.input_parser.mcnp_input import (
    Input,
    Jump,
    Message,
    Title,
)
from montepy.errors import *
from montepy.particle import Particle
import numpy as np

from tests import constants


@pytest.fixture(scope="module")
def simple_problem():
    return montepy.read_input(os.path.join("tests", "inputs", "test.imcnp"))


@pytest.fixture(scope="module")
def importance_problem():
    return montepy.read_input(os.path.join("tests", "inputs", "test_importance.imcnp"))


@pytest.fixture(scope="module")
def universe_problem():
    return montepy.read_input(os.path.join("tests", "inputs", "test_universe.imcnp"))


@pytest.fixture(scope="module")
def data_universe_problem():
    return montepy.read_input(
        os.path.join("tests", "inputs", "test_universe_data.imcnp")
    )


def test_original_input(simple_problem):
    cell_order = [Message, Title] + [Input] * 29
    for i, input_ob in enumerate(simple_problem.original_inputs):
        assert isinstance(input_ob, cell_order[i])


def test_original_input_dos():
    dos_problem = montepy.read_input(os.path.join("tests", "inputs", "test_dos.imcnp"))
    cell_order = [Message, Title] + [Input] * 16
    for i, input_ob in enumerate(dos_problem.original_inputs):
        assert isinstance(input_ob, cell_order[i])


def test_original_input_tabs():
    problem = montepy.read_input(os.path.join("tests", "inputs", "test_tab.imcnp"))
    cell_order = [Message, Title] + [Input] * 17
    for i, input_ob in enumerate(problem.original_inputs):
        assert isinstance(input_ob, cell_order[i])


# TODO formalize this or see if this is covered by other tests.
def test_lazy_comments_check(simple_problem):
    material2 = simple_problem.materials[2]
    for comment in material2._tree.comments:
        print(repr(comment))
    print(material2._tree.get_trailing_comment())


def test_moving_trail_comments(universe_problem):
    problem = copy.deepcopy(universe_problem)
    mat = problem.materials[2]
    idx = problem.data_inputs.index(mat)
    dat = problem.data_inputs[idx - 1]
    assert len(mat.comments) == 1
    assert len(mat.leading_comments) == 1
    assert len(dat.leading_comments) == 0
    assert len(dat.comments) == 0


def test_material_parsing(simple_problem):
    mat_numbers = [1, 2, 3]
    for i, mat in enumerate(simple_problem.materials):
        assert mat.number == mat_numbers[i]


def test_surface_parsing(simple_problem):
    surf_numbers = [1000, 1005, 1010, 1015, 1020, 1025]
    for i, surf in enumerate(simple_problem.surfaces):
        assert surf.number == surf_numbers[i]


def test_data_card_parsing(simple_problem):
    M = material.Material
    V = volume.Volume
    cards = [
        M,
        M,
        M,
        "FC1 SURFACE CURRENT",
        "F1:N,P",
        "FC2 AVERAGE SURFACE FLUX",
        "F2:P",
        "FC4  2-GROUP FLUX",
        "F4:N",
        "E4",
        "F6:P",
        "F7:N",
        "KSRC",
        "KCODE",
        "PHYS:P",
        "MODE",
        V,
    ]
    for i, card in enumerate(simple_problem.data_inputs):
        if isinstance(cards[i], str):
            assert card.classifier.format().upper().rstrip() == cards[i]
        else:
            assert isinstance(card, cards[i])
        if i == 2:
            assert card.thermal_scattering is not None


def test_cells_parsing_linking(simple_problem):
    cell_numbers = [1, 2, 3, 99, 5]
    mats = simple_problem.materials
    mat_answer = [mats[1], mats[2], mats[3], None, None]
    surfs = simple_problem.surfaces
    surf_answer = [
        {surfs[1000]},
        {surfs[1005], *surfs[1015:1026]},
        set(surfs[1000:1011]),
        {surfs[1010]},
        set(),
    ]
    cells = simple_problem.cells
    complements = [set()] * 4 + [{cells[99]}]
    for i, cell in enumerate(simple_problem.cells):
        print(cell)
        print(surf_answer[i])
        assert cell.number == cell_numbers[i]
        assert cell.material == mat_answer[i]
        surfaces = set(cell.surfaces)
        assert surfaces.union(surf_answer[i]) == surfaces
        assert set(cell.complements).union(complements[i]) == complements[i]


def test_message(simple_problem):
    lines = ["this is a message", "it should show up at the beginning", "foo"]
    for i, line in enumerate(simple_problem.message.lines):
        assert line == lines[i]


def test_title(simple_problem):
    answer = "MCNP Test Model for MOAA"
    assert answer == simple_problem.title.title


def test_read_card_recursion():
    problem = montepy.read_input("tests/inputs/testReadRec1.imcnp")
    assert len(problem.cells) == 1
    assert len(problem.surfaces) == 1
    assert montepy.particle.Particle.PHOTON in problem.mode


def test_problem_str(simple_problem):
    output = str(simple_problem)
    assert "MCNP problem for: tests/inputs/test.imcnp" in output


def test_write_to_file(simple_problem):
    out = "foo.imcnp"
    try:
        problem = copy.deepcopy(simple_problem)
        problem.write_to_file(out)
        with open(out, "r") as fh:
            for line in fh:
                print(line.rstrip())
        test_problem = montepy.read_input(out)
        for i, cell in enumerate(simple_problem.cells):
            num = cell.number
            assert num == test_problem.cells[num].number
            for attr in {"universe", "volume"}:
                print(f"testing the attribute: {attr}")
                gold = getattr(simple_problem.cells[num], attr)
                test = getattr(test_problem.cells[num], attr)
                if attr in {"universe"} and gold is not None:
                    gold, test = (gold.number, test.number)
                assert gold == test
        for i, surf in enumerate(simple_problem.surfaces):
            num = surf.number
            assert surf.number == test_problem.surfaces[num].number
        for i, data in enumerate(simple_problem.data_inputs):
            if isinstance(data, material.Material):
                assert data.number == test_problem.data_inputs[i].number
                if data.thermal_scattering is not None:
                    assert test_problem.data_inputs[i].thermal_scattering is not None
            elif isinstance(data, volume.Volume):
                assert str(data) == str(test_problem.data_inputs[i])
            else:
                print("Rewritten data", data.data)
                print("Original input data", test_problem.data_inputs[i].data)
                assert str(data.data) == str(test_problem.data_inputs[i].data)
    finally:
        if os.path.exists(out):
            os.remove(out)


def test_cell_material_setter(simple_problem):
    cell = copy.deepcopy(simple_problem.cells[1])
    mat = simple_problem.materials[2]
    cell.material = mat
    assert cell.material == mat
    cell.material = None
    assert cell.material is None
    with pytest.raises(TypeError):
        cell.material = 5


def test_problem_cells_setter(simple_problem):
    problem = copy.deepcopy(simple_problem)
    cells = copy.deepcopy(simple_problem.cells)
    cells.remove(cells[1])
    with pytest.raises(TypeError):
        problem.cells = 5
    with pytest.raises(TypeError):
        problem.cells = [5]
    with pytest.raises(TypeError):
        problem.cells.append(5)
    problem.cells = cells
    assert problem.cells.objects == cells.objects
    problem.cells = list(cells)
    assert problem.cells[2] == cells[2]
    # test that cell modifiers are still there
    problem.cells._importance.format_for_mcnp_input((6, 2, 0))


def test_problem_test_setter(simple_problem):
    problem = copy.deepcopy(simple_problem)
    sample_title = "This is a title"
    problem.title = sample_title
    assert problem.title.title == sample_title
    with pytest.raises(TypeError):
        problem.title = 5


def test_problem_children_adder(simple_problem):
    problem = copy.deepcopy(simple_problem)
    BT = montepy.input_parser.block_type.BlockType
    in_str = "5 SO 5.0"
    card = montepy.input_parser.mcnp_input.Input([in_str], BT.SURFACE)
    surf = montepy.surfaces.surface_builder.surface_builder(card)
    in_str = "M5 6000.70c 1.0"
    card = montepy.input_parser.mcnp_input.Input([in_str], BT.SURFACE)
    mat = montepy.data_inputs.material.Material(card)
    in_str = "TR1 0 0 1"
    input = montepy.input_parser.mcnp_input.Input([in_str], BT.DATA)
    transform = montepy.data_inputs.transform.Transform(input)
    surf.transform = transform
    cell_num = 1000
    cell = montepy.Cell()
    cell.material = mat
    cell.geometry = -surf
    cell.mass_density = 1.0
    cell.number = cell_num
    cell.universe = problem.universes[350]
    problem.cells.append(cell)
    problem.add_cell_children_to_problem()
    assert surf in problem.surfaces
    assert mat in problem.materials
    assert mat in problem.data_inputs
    assert transform in problem.transforms
    assert transform in problem.data_inputs
    for cell_num in [1, cell_num]:
        print(cell_num)
        if cell_num == 1000:
            with pytest.warns(LineExpansionWarning):
                output = problem.cells[cell_num].format_for_mcnp_input((6, 2, 0))
        else:
            output = problem.cells[cell_num].format_for_mcnp_input((6, 2, 0))
        print(output)
        assert "U=350" in "\n".join(output).upper()


def test_problem_mcnp_version_setter(simple_problem):
    problem = copy.deepcopy(simple_problem)
    with pytest.raises(ValueError):
        problem.mcnp_version = (4, 5, 3)
    problem.mcnp_version = (6, 2, 5)
    assert problem.mcnp_version == (6, 2, 5)


def test_problem_duplicate_surface_remover():
    problem = montepy.read_input("tests/inputs/test_redundant_surf.imcnp")
    nums = list(problem.surfaces.numbers)
    survivors = (
        nums[0:3] + nums[5:8] + [nums[9]] + nums[11:13] + [nums[13]] + [nums[-2]]
    )
    problem.remove_duplicate_surfaces(1e-4)
    assert list(problem.surfaces.numbers) == survivors
    cell_surf_answer = "-1 3 -6"
    assert cell_surf_answer in problem.cells[2].format_for_mcnp_input((6, 2, 0))[1]


def test_surface_periodic():
    problem = montepy.read_input("tests/inputs/test_surfaces.imcnp")
    surf = problem.surfaces[1]
    periodic = problem.surfaces[2]
    assert surf.periodic_surface == periodic
    assert "1 -2 SO" in surf.format_for_mcnp_input((6, 2, 0))[0]
    surf.periodic_surface = problem.surfaces[3]
    assert surf.periodic_surface == problem.surfaces[3]
    del surf.periodic_surface
    assert surf.periodic_surface is None
    with pytest.raises(TypeError):
        surf.periodic_surface = 5


def test_surface_transform():
    problem = montepy.read_input("tests/inputs/test_surfaces.imcnp")
    surf = problem.surfaces[1]
    transform = problem.data_inputs[0]
    del surf.periodic_surface
    surf.transform = transform
    assert surf.transform == transform
    assert "1 1 SO" in surf.format_for_mcnp_input((6, 2, 0))[0]
    del surf.transform
    assert surf.transform is None
    assert "1 SO" in surf.format_for_mcnp_input((6, 2, 0))[0]
    with pytest.raises(TypeError):
        surf.transform = 5


def test_materials_setter(simple_problem):
    problem = copy.deepcopy(simple_problem)
    with pytest.raises(TypeError):
        problem.materials = 5
    with pytest.raises(TypeError):
        problem.materials = [5]
    size = len(problem.materials)
    problem.materials = list(problem.materials)
    assert len(problem.materials) == size
    problem.materials = problem.materials
    assert len(problem.materials) == size


def test_reverse_pointers(simple_problem):
    problem = simple_problem
    complements = list(problem.cells[99].cells_complementing_this)
    assert problem.cells[5] in complements
    assert len(complements) == 1
    cells = list(problem.materials[1].cells)
    assert problem.cells[1] in cells
    assert len(cells) == 1
    cells = list(problem.surfaces[1005].cells)
    assert problem.cells[2] in problem.surfaces[1005].cells
    assert len(cells) == 2


def test_surface_card_pass_through():
    problem = montepy.read_input("tests/inputs/test_surfaces.imcnp")
    surf = problem.surfaces[1]
    # Test input pass through
    answer = ["1 -2 SO -5"]
    assert surf.format_for_mcnp_input((6, 2, 0)) == answer
    # Test changing periodic surface
    new_prob = copy.deepcopy(problem)
    surf = new_prob.surfaces[1]
    new_prob.surfaces[2].number = 5
    assert int(surf.format_for_mcnp_input((6, 2, 0))[0].split()[1]) == -5
    # Test changing transform
    new_prob = copy.deepcopy(problem)
    surf = new_prob.surfaces[4]
    surf.transform.number = 5
    assert int(surf.format_for_mcnp_input((6, 2, 0))[0].split()[1]) == 5
    # test changing surface constants
    new_prob = copy.deepcopy(problem)
    surf = new_prob.surfaces[4]
    surf.location = 2.5
    assert float(surf.format_for_mcnp_input((6, 2, 0))[0].split()[-1]) == 2.5


def test_surface_broken_link():
    with pytest.raises(montepy.errors.MalformedInputError):
        montepy.read_input("tests/inputs/test_broken_surf_link.imcnp")
    with pytest.raises(montepy.errors.MalformedInputError):
        montepy.read_input("tests/inputs/test_broken_transform_link.imcnp")


def test_material_broken_link():
    with pytest.raises(montepy.errors.BrokenObjectLinkError):
        problem = montepy.read_input("tests/inputs/test_broken_mat_link.imcnp")


def test_cell_surf_broken_link():
    with pytest.raises(montepy.errors.BrokenObjectLinkError):
        problem = montepy.read_input("tests/inputs/test_broken_cell_surf_link.imcnp")


def test_cell_complement_broken_link():
    with pytest.raises(montepy.errors.BrokenObjectLinkError):
        problem = montepy.read_input("tests/inputs/test_broken_complement.imcnp")


def test_cell_card_pass_through(simple_problem):
    problem = copy.deepcopy(simple_problem)
    cell = problem.cells[1]
    # test input pass-through
    answer = [
        "C cells",
        "c # hidden vertical Do not touch",
        "c",
        "1 1 20",
        "         -1000  $ dollar comment",
        "        imp:n,p=1 U=350 trcl=5 ",
    ]
    assert cell.format_for_mcnp_input((6, 2, 0)) == answer
    # test surface change
    new_prob = copy.deepcopy(problem)
    new_prob.surfaces[1000].number = 5
    cell = new_prob.cells[1]
    output = cell.format_for_mcnp_input((6, 2, 0))
    print(output)
    assert int(output[4].split("$")[0]) == -5
    # test mass density printer
    cell.mass_density = 10.0
    with pytest.warns(LineExpansionWarning):
        output = cell.format_for_mcnp_input((6, 2, 0))
    print(output)
    assert pytest.approx(float(output[3].split()[2])) == -10
    # ensure that surface number updated
    # Test material number change
    new_prob = copy.deepcopy(problem)
    new_prob.materials[1].number = 5
    cell = new_prob.cells[1]
    output = cell.format_for_mcnp_input((6, 2, 0))
    assert int(output[3].split()[1]) == 5


def test_thermal_scattering_pass_through(simple_problem):
    problem = copy.deepcopy(simple_problem)
    mat = problem.materials[3]
    therm = mat.thermal_scattering
    mat.number = 5
    assert therm.format_for_mcnp_input((6, 2, 0)) == ["MT5 lwtr.23t h-zr.20t h/zr.28t"]


def test_cutting_comments_parse():
    problem = montepy.read_input("tests/inputs/breaking_comments.imcnp")
    comments = problem.cells[1].comments
    assert len(comments) == 3
    assert "this is a cutting comment" in list(comments)[2].contents
    comments = problem.materials[2].comments
    assert len(comments) == 2


def test_cutting_comments_print_no_mutate():
    problem = montepy.read_input("tests/inputs/breaking_comments.imcnp")
    cell = problem.cells[1]
    output = cell.format_for_mcnp_input((6, 2, 0))
    assert len(output) == 5
    assert "c this is a cutting comment" == output[3]
    material2 = problem.materials[2]
    output = material2.format_for_mcnp_input((6, 2, 0))
    assert len(output) == 5
    assert "c          26057.80c        2.12" == output[3]


def test_cutting_comments_print_mutate():
    problem = montepy.read_input("tests/inputs/breaking_comments.imcnp")
    cell = problem.cells[1]
    cell.number = 8
    output = cell.format_for_mcnp_input((6, 2, 0))
    print(output)
    assert len(output) == 5
    assert "c this is a cutting comment" == output[3]
    material2 = problem.materials[2]
    material2.number = 5
    output = material2.format_for_mcnp_input((6, 2, 0))
    print(output)
    assert len(output) == 5
    assert "c          26057.80c        2.12" == output[3]


def test_comments_setter(simple_problem):
    cell = copy.deepcopy(simple_problem.cells[1])
    comment = simple_problem.surfaces[1000].comments[0]
    cell.leading_comments = [comment]
    assert cell.comments[0] == comment
    cell.leading_comments = comment
    assert cell.comments[0] == comment
    with pytest.raises(TypeError):
        cell.leading_comments = [5]
    with pytest.raises(TypeError):
        cell.leading_comments = 5


def test_problem_linker():
    cell = montepy.Cell()
    with pytest.raises(TypeError):
        cell.link_to_problem(5)


def test_importance_parsing(importance_problem, simple_problem):
    cell = importance_problem.cells[1]
    assert cell.importance.neutron == 1.0
    assert cell.importance.photon == 1.0
    assert cell.importance.electron == 0.0
    cell = simple_problem.cells[1]
    assert cell.importance.neutron == 1.0
    assert cell.importance.photon == 1.0


def test_importance_format_unmutated(importance_problem):
    imp = importance_problem.cells._importance
    output = imp.format_for_mcnp_input((6, 2, 0))
    print(output)
    assert len(output) == 4
    assert "imp:n,p 1 1 1 0 3" == output[1]
    assert "imp:e   0 2r 1 r" == output[3]


def test_importance_format_mutated(importance_problem):
    problem = copy.deepcopy(importance_problem)
    imp = problem.cells._importance
    problem.cells[1].importance.neutron = 0.5
    with pytest.warns(LineExpansionWarning):
        output = imp.format_for_mcnp_input((6, 2, 0))
    print(output)
    assert len(output) == 6
    assert "imp:n 0.5 1 1 0 3" in output
    assert "c special comment related to #520" == output[2]


def test_importance_write_unmutated(importance_problem):
    fh = io.StringIO()
    importance_problem.write_problem(fh)
    found_np = False
    found_e = False
    fh.seek(0)
    for line in fh.readlines():
        print(line.rstrip())
        if "imp:n,p 1" in line:
            found_np = True
        elif "imp:e" in line:
            found_e = True
    assert found_np
    assert found_e
    fh.close()


def test_importance_write_mutated(importance_problem):
    fh = io.StringIO()
    problem = copy.deepcopy(importance_problem)
    problem.cells[1].importance.neutron = 0.5
    with pytest.warns(LineExpansionWarning):
        problem.write_problem(fh)
    found_n = False
    found_e = False
    fh.seek(0)
    for line in fh.readlines():
        print(line.rstrip())
        if "imp:n 0.5" in line:
            found_n = True
        elif "imp:e" in line:
            found_e = True
    assert found_n
    assert found_e
    fh.close()


def test_importance_write_cell(importance_problem):
    for state in ["no change", "new unmutated cell", "new mutated cell"]:
        fh = io.StringIO()
        problem = copy.deepcopy(importance_problem)
        if "new" in state:
            cell = copy.deepcopy(problem.cells[5])
            cell.number = 999
            problem.cells.append(cell)
        problem.print_in_data_block["imp"] = False
        if "new" in state:
            with pytest.warns(LineExpansionWarning):
                problem.write_problem(fh)
        else:
            problem.write_problem(fh)
        found_np = False
        found_e = False
        found_data_np = False
        fh.seek(0)
        for line in fh.readlines():
            print(line.rstrip())
            if "imp:n,p=1" in line:
                found_np = True
            elif "imp:e=1" in line:
                found_e = True
            elif "imp:e 1" in line.lower():
                found_data_np = True
        assert found_np
        assert found_e
        assert not found_data_np
        fh.close()


def test_importance_write_data(simple_problem):
    fh = io.StringIO()
    problem = copy.deepcopy(simple_problem)
    problem.print_in_data_block["imp"] = True
    problem.write_problem(fh)
    found_n = False
    found_p = False
    fh.seek(0)
    for line in fh:
        print(line.rstrip())
        if "imp:n 1" in line:
            found_n = True
        if "imp:p 1 0.5" in line:
            found_p = True
    assert found_n
    assert found_p
    fh.close()


def test_avoid_blank_cell_modifier_write(simple_problem):
    fh = io.StringIO()
    problem = copy.deepcopy(simple_problem)
    problem.print_in_data_block["U"] = True
    problem.print_in_data_block["FILL"] = True
    problem.print_in_data_block["LAT"] = True
    problem.cells[5].fill.transform = None
    problem.cells[5].fill.universe = None
    problem.cells[1].universe = problem.universes[0]
    for cell in problem.cells:
        del cell.volume
    problem.cells.allow_mcnp_volume_calc = True
    problem.write_problem(fh)
    found_universe = False
    found_lattice = False
    found_vol = False
    found_fill = False
    fh.seek(0)
    for line in fh.readlines():
        print(line.rstrip())
        if "U " in line:
            found_universe = True
        if "LAT " in line:
            found_lattice = True
        if "FILL " in line:
            found_fill = True
        if "VOL " in line:
            found_vol = True
    assert not found_universe
    assert not found_lattice
    assert not found_vol
    assert not found_fill
    fh.close()


def test_set_mode(importance_problem):
    problem = copy.deepcopy(importance_problem)
    problem.set_mode("e p")
    particles = {Particle.ELECTRON, Particle.PHOTON}
    assert len(problem.mode) == 2
    for part in particles:
        assert part in problem.mode


def test_set_equal_importance(importance_problem):
    problem = copy.deepcopy(importance_problem)
    problem.cells.set_equal_importance(0.5, [5])
    for cell in problem.cells:
        for particle in problem.mode:
            if cell.number != 5:
                print(cell.number, particle)
                assert cell.importance[particle] == 0.5
    for particle in problem.mode:
        print(5, particle)
        assert problem.cells[5].importance[particle] == 0.0
    problem.cells.set_equal_importance(0.75, [problem.cells[99]])
    for cell in problem.cells:
        for particle in problem.mode:
            if cell.number != 99:
                print(cell.number, particle)
                assert cell.importance[particle] == 0.75
    for particle in problem.mode:
        print(99, particle)
        assert problem.cells[99].importance[particle] == 0.0
    with pytest.raises(TypeError):
        problem.cells.set_equal_importance("5", [5])
    with pytest.raises(ValueError):
        problem.cells.set_equal_importance(-0.5, [5])
    with pytest.raises(TypeError):
        problem.cells.set_equal_importance(5, "a")
    with pytest.raises(TypeError):
        problem.cells.set_equal_importance(5, ["a"])


def test_check_volume_calculated(simple_problem):
    assert not simple_problem.cells[1].volume_mcnp_calc


def test_redundant_volume():
    with pytest.raises(montepy.errors.MalformedInputError):
        montepy.read_input(os.path.join("tests", "inputs", "test_vol_redundant.imcnp"))


def test_delete_vol(simple_problem):
    problem = copy.deepcopy(simple_problem)
    del problem.cells[1].volume
    assert not problem.cells[1].volume_is_set


def test_enable_mcnp_vol_calc(simple_problem):
    problem = copy.deepcopy(simple_problem)
    problem.cells.allow_mcnp_volume_calc = True
    assert problem.cells.allow_mcnp_volume_calc
    assert "NO" not in str(problem.cells._volume)
    problem.cells.allow_mcnp_volume_calc = False
    assert "NO" in str(problem.cells._volume)
    with pytest.raises(TypeError):
        problem.cells.allow_mcnp_volume_calc = 5


def test_cell_multi_volume():
    in_str = "1 0 -1 VOL=1 VOL 5"
    with pytest.raises(ValueError):
        montepy.Cell(Input([in_str], montepy.input_parser.block_type.BlockType.CELL))


def test_universe_cell_parsing(simple_problem):
    answers = [350] + [0] * 4
    for cell, answer in zip(simple_problem.cells, answers):
        print(cell, answer)
        assert cell.universe.number == answer


def test_universe_fill_data_parsing(data_universe_problem):
    answers = [350, 0, 0, 1]
    for cell, answer in zip(data_universe_problem.cells, answers):
        print(cell, answer)
        assert cell.universe.number == answer
    for cell in data_universe_problem.cells:
        print(cell)
        if cell.number != 99:
            assert not cell.not_truncated
        else:
            assert cell.not_truncated
    assert data_universe_problem.cells[99].not_truncated
    answers = [None, None, 350, None, None]
    for cell, answer in zip(data_universe_problem.cells, answers):
        print(cell.number, cell.fill.universe, answer)
        if answer is None:
            assert cell.fill.universe is None
        else:
            assert cell.fill.universe.number == answer


def test_universe_cells1(data_universe_problem):
    answers = {350: [1], 0: [2, 3, 5], 1: [99]}
    for uni_number, cell_answers in answers.items():
        for cell, answer in zip(
            data_universe_problem.universes[uni_number].cells, cell_answers
        ):
            assert cell.number == answer


def test_cell_not_truncate_setter(simple_problem):
    problem = copy.deepcopy(simple_problem)
    cell = problem.cells[1]
    cell.not_truncated = True
    assert cell.not_truncated
    with pytest.raises(ValueError):
        cell = problem.cells[2]
        cell.not_truncated = True


def test_universe_setter(simple_problem):
    problem = copy.deepcopy(simple_problem)
    universe = problem.universes[350]
    cell = problem.cells[3]
    cell.universe = universe
    assert cell.universe == universe
    assert cell.universe.number == 350
    with pytest.raises(TypeError):
        cell.universe = 5


def test_universe_cell_formatter(simple_problem):
    problem = copy.deepcopy(simple_problem)
    universe = problem.universes[350]
    cell = problem.cells[3]
    cell.universe = universe
    cell.not_truncated = True
    with pytest.warns(LineExpansionWarning):
        output = cell.format_for_mcnp_input((6, 2, 0))
    assert "U=-350" in " ".join(output)


def test_universe_data_formatter(data_universe_problem):
    problem = copy.deepcopy(data_universe_problem)
    # test unmutated
    output = problem.cells._universe.format_for_mcnp_input((6, 2, 0))
    print(output)
    assert "u 350 2J -1" in output
    universe = problem.universes[350]
    # test mutated
    cell = problem.cells[3]
    cell.universe = universe
    cell.not_truncated = True
    with pytest.warns(LineExpansionWarning):
        output = problem.cells._universe.format_for_mcnp_input((6, 2, 0))
    print(output)
    assert "u 350 J -350 -1" in output
    # test appending a new mutated cell
    new_cell = copy.deepcopy(cell)
    new_cell.number = 1000
    new_cell.universe = universe
    new_cell.not_truncated = False
    problem.cells.append(new_cell)
    with pytest.warns(LineExpansionWarning):
        output = problem.cells._universe.format_for_mcnp_input((6, 2, 0))
    print(output)
    assert "u 350 J -350 -1 J 350 " in output
    # test appending a new UNmutated cell
    problem = copy.deepcopy(data_universe_problem)
    cell = problem.cells[3]
    new_cell = copy.deepcopy(cell)
    new_cell.number = 1000
    new_cell.universe = universe
    new_cell.not_truncated = False
    # lazily implement pulling cell in from other model
    new_cell._mutated = False
    new_cell._universe._mutated = False
    problem.cells.append(new_cell)
    with pytest.warns(LineExpansionWarning):
        output = problem.cells._universe.format_for_mcnp_input((6, 2, 0))
    print(output)
    assert "u 350 2J -1 J 350 " in output


def test_universe_number_collision():
    problem = montepy.read_input(
        os.path.join("tests", "inputs", "test_universe_data.imcnp")
    )
    with pytest.raises(montepy.errors.NumberConflictError):
        problem.universes[0].number = 350

    with pytest.raises(montepy.errors.NumberConflictError):
        problem.universes[350].number = 0


def test_universe_repr(simple_problem):
    uni = simple_problem.universes[0]
    output = repr(uni)
    assert "Number: 0" in output
    assert "Problem: set" in output
    assert "Cells: [2" in output


def test_lattice_format_data(simple_problem):
    problem = copy.deepcopy(simple_problem)
    cells = problem.cells
    cells[1].lattice = 1
    cells[99].lattice = 2
    answer = "LAT 1 2J 2"
    output = cells._lattice.format_for_mcnp_input((6, 2, 0))
    assert answer in output[0]


def test_lattice_push_to_cells(simple_problem):
    problem = copy.deepcopy(simple_problem)
    lattices = [1, 2, Jump(), Jump()]
    card = Input(
        ["Lat " + " ".join(list(map(str, lattices)))],
        montepy.input_parser.block_type.BlockType.DATA,
    )
    lattice = montepy.data_inputs.lattice_input.LatticeInput(card)
    lattice.link_to_problem(problem)
    lattice.push_to_cells()
    for cell, answer in zip(problem.cells, lattices):
        print(cell.number, answer)
        if isinstance(answer, int):
            assert cell.lattice.value == answer
        else:
            assert cell.lattice is None


def test_universe_problem_parsing(universe_problem):
    for cell in universe_problem.cells:
        if cell.number == 1:
            assert cell.universe.number == 1
        else:
            assert cell.universe.number == 0


def test_importance_end_repeat(universe_problem):
    problem = copy.deepcopy(universe_problem)
    for cell in problem.cells:
        if cell.number in {99, 5}:
            cell.importance.photon = 1.0
        else:
            cell.importance.photon = 0.0
    problem.print_in_data_block["IMP"] = True
    output = problem.cells._importance.format_for_mcnp_input((6, 2, 0))
    # OG value was 0.5 so 0.0 is correct.
    assert "imp:p 0 0.0" in output


def test_fill_parsing(universe_problem):
    answers = [None, np.array([[[1], [0]], [[0], [1]]]), None, 1, 1]
    for cell, answer in zip(universe_problem.cells, answers):
        if answer is None:
            assert cell.fill.universe is None
        elif isinstance(answer, np.ndarray):
            assert cell.fill.multiple_universes
            assert (cell.fill.min_index == np.array([0.0, 0.0, 0.0])).all()
            assert (cell.fill.max_index == np.array([1.0, 1.0, 0.0])).all()
            assert cell.fill.universes[0][0][0].number == answer[0][0][0]
            assert cell.fill.universes[1][1][0].number == answer[1][1][0]
            assert cell.fill.transform == universe_problem.transforms[5]
        else:
            assert cell.fill.universe.number == answer


def test_fill_transform_setter(universe_problem):
    problem = copy.deepcopy(universe_problem)
    transform = problem.transforms[5]
    cell = problem.cells[5]
    cell.fill.transform = transform
    assert cell.fill.transform == transform
    assert not cell.fill.hidden_transform
    cell.fill.transform = None
    assert cell.fill.transform is None
    with pytest.raises(TypeError):
        cell.fill.transform = "hi"
    cell.fill.transform = transform
    del cell.fill.transform
    assert cell.fill.transform is None


def test_fill_cell_format(simple_problem, universe_problem):
    problem = copy.deepcopy(universe_problem)
    fill = problem.cells[5].fill
    output = fill.format_for_mcnp_input((6, 2, 0))
    answer = "fill=1 (1 0.0 0.0)"
    assert output[0] == answer
    # test *fill
    fill.transform.is_in_degrees = True
    output = fill.format_for_mcnp_input((6, 2, 0))
    answer = "*fill=1 (1 0.0 0.0)"
    assert output[0] == answer
    # test changing the transform
    fill.transform.displacement_vector[0] = 2.0
    output = fill.format_for_mcnp_input((6, 2, 0))
    assert output[0] == "*fill=1 (2 0.0 0.0)"
    # test without transform
    fill.transform = None
    answer = "fill=1 "
    output = fill.format_for_mcnp_input((6, 2, 0))
    assert output[0] == answer
    # test with no fill
    fill.universe = None
    output = fill.format_for_mcnp_input((6, 2, 0))
    assert len(output) == 0
    # test with complex universe lattice fill
    fill = problem.cells[2].fill
    output = fill.format_for_mcnp_input((6, 2, 0))
    answers = ["fill= 0:1 0:1 0:0 1 0 R 1 (5)"]
    assert output == answers
    problem.print_in_data_block["FILL"] = True
    # test that complex fill is not printed in data block
    with pytest.raises(ValueError):
        problem.cells._fill.format_for_mcnp_input((6, 2, 0))
    problem = copy.deepcopy(simple_problem)
    problem.cells[5].fill.transform = None
    problem.print_in_data_block["FILL"] = True
    output = problem.cells._fill.format_for_mcnp_input((6, 2, 0))
    assert output == ["FILL 4J 350 "]


def test_universe_cells_claim(universe_problem):
    problem = copy.deepcopy(universe_problem)
    universe = problem.universes[1]
    universe.claim(problem.cells[2])
    assert problem.cells[2].universe == universe
    universe = montepy.Universe(5)
    problem.universes.append(universe)
    universe.claim(problem.cells)
    for cell in problem.cells:
        assert cell.universe == universe
    with pytest.raises(TypeError):
        universe.claim("hi")
    with pytest.raises(TypeError):
        universe.claim(["hi"])


def test_universe_cells2(universe_problem):
    answers = [1]
    universe = universe_problem.universes[1]
    assert len(answers) == len(list(universe.cells))
    for cell, answer in zip(universe.cells, answers):
        assert cell.number == answer


def test_data_print_control_str(simple_problem):
    assert (
        str(simple_problem.print_in_data_block)
        == "Print data in data block: {'imp': False, 'u': False, 'fill': False, 'vol': True}"
    )


def test_cell_validator(simple_problem):
    problem = copy.deepcopy(simple_problem)
    cell = problem.cells[1]
    del cell.mass_density
    with pytest.raises(montepy.errors.IllegalState):
        cell.validate()
    cell = montepy.Cell()
    # test no geometry at all
    with pytest.raises(montepy.errors.IllegalState):
        cell.validate()
    surf = problem.surfaces[1000]
    cell.surfaces.append(surf)
    # test surface added but geomtry not defined
    with pytest.raises(montepy.errors.IllegalState):
        cell.validate()


def test_importance_rewrite(simple_problem):
    out_file = "test_import_data_1"
    problem = copy.deepcopy(simple_problem)
    problem.print_in_data_block["imp"] = True
    try:
        problem.write_problem(out_file)
        problem = montepy.read_input(out_file)
        os.remove(out_file)
        problem.print_in_data_block["imp"] = False
        problem.write_problem(out_file)
        found_n = False
        found_p = False
        found_vol = False
        with open(out_file, "r") as fh:
            for line in fh:
                print(line.rstrip())
                if "IMP:N 1 2R" in line:
                    found_n = True
                if "IMP:P 1 0.5" in line:
                    found_p = True
                if "vol NO 2J 1 1.5 J" in line:
                    found_vol = True
        assert not found_n
        assert not found_p
        assert found_vol
    finally:
        try:
            os.remove(out_file)
        except FileNotFoundError:
            pass


def test_parsing_error():
    in_file = os.path.join("tests", "inputs", "test_bad_syntax.imcnp")
    with pytest.raises(montepy.errors.ParsingError):
        problem = montepy.read_input(in_file)


def test_leading_comments(simple_problem):
    cell = copy.deepcopy(simple_problem.cells[1])
    leading_comments = cell.leading_comments
    assert "cells" in leading_comments[0].contents
    del cell.leading_comments
    assert not cell.leading_comments
    cell.leading_comments = leading_comments[0:1]
    assert "cells" in cell.leading_comments[0].contents
    assert len(cell.leading_comments) == 1


def test_wrap_warning(simple_problem):
    cell = copy.deepcopy(simple_problem.cells[1])
    with pytest.warns(montepy.errors.LineExpansionWarning):
        output = cell.wrap_string_for_mcnp("h" * 130, (6, 2, 0), True)
        assert len(output) == 2
    output = cell.wrap_string_for_mcnp("h" * 127, (6, 2, 0), True)
    assert len(output) == 1


def test_expansion_warning_crash(simple_problem):
    problem = copy.deepcopy(simple_problem)
    cell = problem.cells[99]
    cell.material = problem.materials[1]
    cell.mass_density = 10.0
    problem.materials[1].number = 987654321
    problem.surfaces[1010].number = 123456789
    with io.StringIO() as fh:
        with pytest.warns(montepy.errors.LineExpansionWarning):
            problem.write_problem(fh)


def test_alternate_encoding():
    with pytest.raises(UnicodeDecodeError):
        montepy.read_input(
            os.path.join("tests", "inputs", "bad_encoding.imcnp"), replace=False
        )
    montepy.read_input(
        os.path.join("tests", "inputs", "bad_encoding.imcnp"), replace=True
    )


_SKIP_LINES = {
    # skip lines of added implied importances
    "tests/inputs/test_universe_data.imcnp": {5: True, 14: True, 15: True},
}


@pytest.mark.parametrize(
    "file",
    set((Path("tests") / "inputs").iterdir())
    - {
        Path("tests")
        / "inputs"
        / p  #                           Skip complexity of read
        for p in constants.BAD_INPUTS
        | constants.IGNORE_FILES
        | {"testRead.imcnp", "readEdgeCase.imcnp"}
    },
)
def test_read_write_cycle(file):
    print(f"Testing against {file} *********************")
    problem = montepy.read_input(file)
    SKIPPERS = _SKIP_LINES.get(str(file), {})
    fh = io.StringIO()
    # make string unclosable to keep open after reading.
    fh.close = lambda: None
    problem.write_problem(fh)
    fh.seek(0)
    # test valid syntax
    new_problem = montepy.read_input(fh)
    # verify lines are similar
    fh.seek(0)
    lines = [line.rstrip() for line in fh]
    [print(line) for line in lines]
    with open(file, "r") as gold_fh:
        gold_fh_iter = iter(gold_fh)
        lines_iter = iter(lines)
        for i, (gold_line, new_line) in enumerate(zip(gold_fh_iter, lines_iter)):
            if i in SKIPPERS:
                # True means skip new file line
                if SKIPPERS[i]:
                    new_line = next(lines_iter)
                else:
                    gold_line = next(gold_fh_iter)
            # edge case override for not fixing #527.
            if str(file) == "tests/inputs/test_interp_edge.imcnp" and i == 1:
                assert new_line == "10214   0    (1  2I 4 )"
                continue
            try:
                assert new_line == gold_line.rstrip().expandtabs(8)
            except AssertionError as e:
                # handle case of making importance explicit
                if "IMP:n=0.0" in new_line:
                    assert (
                        new_line.replace("IMP:n=0.0", "").rstrip() == gold_line.rstrip()
                    )
                else:
                    raise e
