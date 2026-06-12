# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import copy
import numpy as np
import pytest
import montepy
from montepy.data_inputs.transform import Transform
from montepy.exceptions import MalformedInputError, IllegalState
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input


@pytest.mark.parametrize(
    "input_str,should_raise",
    [
        ("M20", True),
        ("TR5", True),
        ("TR1foo 0.0 0.0 0.0", True),
        ("TR1 0.0 0.0 hi", True),
        ("TR1 0.0 0.0 0.0 0.0 0.0 0.0 0.0 hi", True),
        ("TR1 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 2", True),
        ("*TR 0.0 0.0 0.0", True),
        ("TR5:n,p 0.0 0.0 0.0", True),
        ("tr5 1.0 1.0 1.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0", False),
        ("*tr5 1.0 1.0 1.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0", False),
        ("*tr5 de de de", True),
        ("*tr5 1.0 1.0 1.0 foo ", True),
    ],
)
def test_transform_init_cases(input_str, should_raise):
    if should_raise:
        with pytest.raises(MalformedInputError):
            Transform(input_str, jit_parse=False)
    else:
        transform = Transform(input_str, jit_parse=False)
        assert isinstance(transform, Transform)


def test_transform_number_only():
    transform = Transform(number=5)
    assert transform.number == 5


def test_transform_vanilla():
    in_str = "tr5 " + "1.0 " * 3 + "0.0 " * 9
    transform = Transform(in_str)
    assert transform.number == 5
    assert transform.old_number == 5
    assert not transform.is_in_degrees
    assert transform.is_main_to_aux
    assert len(transform.displacement_vector) == 3
    assert len(transform.rotation_matrix) == 9
    assert all(component == 1.0 for component in transform.displacement_vector)
    assert all(component == 0.0 for component in transform.rotation_matrix)


def test_transform_in_degrees():
    in_str = "*tr5 " + "1.0 " * 3 + "0.0 " * 9
    transform = Transform(in_str)
    assert transform.is_in_degrees


def test_transform_blank_init():
    transform = Transform()
    assert transform.number == -1
    assert len(transform.displacement_vector) == 3
    assert len(transform.rotation_matrix) == 0
    assert not transform.is_in_degrees
    assert transform.is_main_to_aux


def test_transform_validate():
    transform = Transform()
    with pytest.raises(IllegalState):
        transform.validate()
    with pytest.raises(IllegalState):
        transform.format_for_mcnp_input((6, 2, 0))


def test_transform_degrees_setter():
    in_str = "*tr5 " + "1.0 " * 3 + "0.0 " * 9 + " -1"
    transform = Transform(in_str)
    transform.is_in_degrees = False
    assert not transform.is_in_degrees
    with pytest.raises(TypeError):
        transform.is_in_degrees = 1


def test_transform_number_setter():
    in_str = "*tr5 " + "1.0 " * 3 + "0.0 " * 9 + " -1"
    transform = Transform(in_str)
    transform.number = 20
    assert transform.number == 20
    with pytest.raises(TypeError):
        transform.number = "hi"
    with pytest.raises(ValueError):
        transform.number = -5


def test_transform_displace_setter():
    in_str = "*tr5 " + "1.0 " * 3 + "0.0 " * 9 + " -1"
    transform = Transform(in_str)
    transform.displacement_vector = np.array([1.0, 1.0, 1.0])
    assert all(component == 1.0 for component in transform.displacement_vector)
    with pytest.raises(TypeError):
        transform.displacement_vector = [1, 2]
    with pytest.raises(ValueError):
        transform.displacement_vector = np.array([1.0])
    with pytest.raises(ValueError):
        transform.displacement_vector = np.array([1.0] * 10)


def test_transform_rotation_setter():
    in_str = "*tr5 " + "1.0 " * 3 + "0.0 " * 9 + " -1"
    transform = Transform(in_str)
    transform.rotation_matrix = np.array([1.0] * 5)
    assert all(component == 1.0 for component in transform.rotation_matrix)
    with pytest.raises(TypeError):
        transform.rotation_matrix = [1, 2]
    with pytest.raises(ValueError):
        transform.rotation_matrix = np.array([1.0])
    with pytest.raises(ValueError):
        transform.displacement_vector = np.array([1.0] * 10)


def test_transform_is_main_aux_setter():
    in_str = "*tr5 " + "1.0 " * 3 + "0.0 " * 9
    transform = Transform(in_str)
    transform.is_main_to_aux = False
    assert not transform.is_main_to_aux
    with pytest.raises(TypeError):
        transform.is_main_to_aux = "hi"


def test_transform_str_repr():
    in_str = "*tr5 " + "0.0 " * 3 + "0.0 " * 9 + " -1"
    transform = Transform(in_str)
    answer = "Transform('*tr5 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0  -1', number=5, jit_parse=True)"
    assert answer == repr(transform)
    assert str(transform) == "Transform: 5"


def test_transform_print_mcnp():
    in_str = "tr5 " + "0.0 " * 3 + "0.0 " * 9 + " -1"
    transform = Transform(in_str)
    output = transform.format_for_mcnp_input((6, 2, 0))
    answers = [in_str.replace("5", "2")]
    assert output[0] == in_str
    transform.number = 2
    output = transform.format_for_mcnp_input((6, 2, 0))
    assert len(output) == len(answers)
    for i, line in enumerate(output):
        assert line == answers[i]
    in_str = "*tr5 " + "0.0 " * 3 + "0.0 " * 9 + " -1"
    answers = [in_str.replace("5", "2")]
    transform = Transform(in_str)
    transform.number = 2
    output = transform.format_for_mcnp_input((6, 2, 0))
    assert output == answers


def test_transform_equivalent():
    in_str = "tr5 " + "0.0 " * 3 + "0.0 " * 9 + " -1"
    base = Transform(in_str)
    assert base.equivalent(base, 1e-6)
    # test different degrees
    in_str = "*tr5 " + "0.0 " * 3 + "0.0 " * 9 + " -1"
    compare = Transform(in_str)
    assert not base.equivalent(compare, 1e-3)
    # test different main_aux
    in_str = "tr5 " + "0.0 " * 3 + "0.0 " * 9
    compare = Transform(in_str)
    assert not base.equivalent(compare, 1e-3)
    # test different displace
    in_str = "tr5 " + "1.0 " * 3 + "0.0 " * 9 + "-1"
    compare = Transform(in_str)
    assert not base.equivalent(compare, 1e-3)
    # test different rotation
    in_str = "tr5 " + "0.0 " * 3 + "1.0 " * 9 + "-1"
    compare = Transform(in_str)
    assert not base.equivalent(compare, 1e-3)
    # test different rotation
    in_str = "tr5 " + "0.0 " * 3
    compare = Transform(in_str)
    compare.is_main_to_aux = False
    assert not base.equivalent(compare, 1e-3)


def test_transform_update_values():
    in_str = "tr5 " + "0.0 " * 3 + "0.0 " * 9 + " -1"
    base = Transform(in_str, jit_parse=False)
    base._update_values()
    assert base._tree["classifier"].modifier.value == ""
    assert len(base.data) == 13
    # test with no rotation matrix start
    in_str = "tr5 " + "0.0 " * 3
    base = Transform(in_str)
    test = copy.deepcopy(base)
    test.rotation_matrix = np.ones(9)
    test._update_values()
    assert len(test.data) == 12
    assert test.data[-1].value == 1.0
    test.is_main_to_aux = False
    test._update_values()
    assert len(test.data) == 13
    assert test.data[-1].is_negative
    # test partial rotation matrix start
