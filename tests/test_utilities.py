# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import pytest
from montepy.utilities import fortran_float

import math


@pytest.mark.parametrize(
    "test_string,expected",
    [
        ("123", 123),
        ("1.23", 1.23),
        ("1.2e+3", 1.2e3),
        ("1.2e-3", 1.2e-3),
    ],
)
def test_normal_float_parse(test_string, expected):
    assert math.isclose(fortran_float(test_string), expected)


@pytest.mark.parametrize(
    "test_string,expected",
    [
        ("1.2+3", 1.2e3),
        ("1.2-3", 1.2e-3),
        ("-2-3", -2.0e-3),
    ],
)
def test_stupid_float_parse(test_string, expected):
    assert math.isclose(fortran_float(test_string), expected)


def test_raise_error():
    with pytest.raises(ValueError):
        fortran_float("Dog")
