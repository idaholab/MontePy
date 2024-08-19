# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import pytest

import montepy
from montepy.mcnp_problem import MCNP_Problem


@pytest.fixture
def problem_path():
    return "tests/inputs/test.imcnp"

@pytest.fixture
def problem(problem_path):
    return MCNP_Problem(problem_path)

def test_problem_init(problem, problem_path):
    assert isinstance(
        problem.input_file, montepy.input_parser.input_file.MCNP_InputFile
    )
    assert problem.input_file.path == problem_path
    assert problem.input_file.name == problem_path
    assert problem.mcnp_version == (6, 2, 0)

def test_problem_str(problem, problem_path):
    assert f"MCNP problem for: {problem_path}" in str(problem)
