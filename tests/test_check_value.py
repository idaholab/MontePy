from hypothesis import given
import hypothesis.strategies as st
import pytest

import montepy._check_value as cv


@cv.check_arguments
def dummy_func(a: str):
    pass


binary = st.binary()
boolean = st.booleans()
chars = st.characters()
dt = st.datetimes()
fl = st.floats()
it = st.integers()
no = st.none()


@given(st.one_of(binary, boolean, dt, fl, it, no))
def test_dummy_bad_type(val):
    with pytest.raises(TypeError):
        dummy_func(val)


@given(st.text())
def test_dummy_good_type(val):
    dummy_func(val)
