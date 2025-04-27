from __future__ import annotations
from hypothesis import given
import hypothesis.strategies as st
import pytest

import montepy._check_value as cv


# TODO check annotations with namespaces


@cv.check_arguments
def str_annotations(a: str):
    pass


@cv.check_arguments
def str_annote_default(a: str = None):
    pass


binary = st.binary()
boolean = st.booleans()
chars = st.characters()
dt = st.datetimes()
fl = st.floats()
it = st.integers()
no = st.none()
funcs = st.sampled_from(
    [
        str_annotations,
    ]
)


@given(st.one_of(binary, boolean, dt, fl, it, no), funcs)
def test_dummy_bad_type(val, func):
    with pytest.raises(TypeError):
        func(val)


@given(st.one_of(chars), funcs)
def test_dummy_good_type(val, func):
    func(val)


@given(st.one_of(chars, no), st.sampled_from([str_annote_default]))
def test_none_default(val, func):
    func(val)
