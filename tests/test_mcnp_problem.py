# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import pytest

import montepy
from montepy.mcnp_problem import MCNP_Problem


@pytest.fixture(scope="module")
def problem_path():
    return "tests/inputs/test.imcnp"


@pytest.fixture(scope="module")
def problem(problem_path):
    return MCNP_Problem(problem_path)


def test_problem_init(problem, problem_path):
    assert isinstance(
        problem.input_file, montepy.input_parser.input_file.MCNP_InputFile
    )
    assert problem.input_file.path == problem_path
    assert problem.input_file.name == problem_path
    assert problem.mcnp_version == (6, 3, 0)


def test_problem_str(problem, problem_path):
    assert f"MCNP problem for: {problem_path}" in str(problem)


def test_problem_repr(problem, problem_path):
    assert repr(problem) == "MCNP_Problem('tests/inputs/test.imcnp')"


def test_problem_write_type(problem):
    unwritable = object()
    with pytest.raises(TypeError):
        problem.write_problem(unwritable)


def test_problem_clone(problem):
    problem.parse_input()
    new_problem = problem.clone()
    for collection in {"cells", "surfaces", "materials"}:
        for old_obj, new_obj in zip(
            getattr(problem, collection), getattr(new_problem, collection)
        ):
            assert old_obj is not new_obj
            assert new_obj._problem is new_problem


def test_blank_parse():
    problem = MCNP_Problem()
    problem.parse_input()


def test_surfaces_setter(problem):
    surfs = montepy.Surfaces()
    problem.surfaces = surfs
    assert problem.surfaces is surfs
    assert problem.surfaces._problem is problem
    problem.surfaces = []
    assert len(problem.surfaces) == 0


def test_problem_full_parse():
    problem = montepy.read_input("tests/inputs/test.imcnp", jit_parse=True)
    assert all(not cell.fully_parsed for cell in problem.cells)
    problem.full_parse()
    assert all(cell.fully_parsed for cell in problem.cells)
    assert all(surface.fully_parsed for surface in problem.surfaces)
    assert all(
        getattr(data_input, "fully_parsed", True) for data_input in problem.data_inputs
    )
