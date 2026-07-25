# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import pytest
from montepy.utilities import fortran_float, make_prop_pointer

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


def test_make_prop_pointer_triggers_full_parse_when_jit():
    class _JitStub:
        def __init__(self):
            self._not_parsed = True

        def full_parse(self):
            del self._not_parsed
            self._value = "parsed"

        @make_prop_pointer("_value")
        def value(self):
            pass

    stub = _JitStub()
    assert stub.value == "parsed"
    assert not hasattr(stub, "_not_parsed")
