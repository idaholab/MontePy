from __future__ import annotations
from hypothesis import given
import hypothesis.strategies as st
import numpy as np
import pytest

import montepy
import montepy._check_value as cv


@cv.args_checked
def str_annotations(a: str):
    pass


@cv.args_checked
def str_annote_default(a: str = None):
    pass


@cv.args_checked
def str_pipe_union(a: str | montepy.Cell):
    pass


@cv.args_checked
def list_type(a: list[int]):
    pass


@cv.args_checked
def dict_type(a: dict[str, int]):
    pass


@cv.args_checked
def np_array(a: np.ndarray[np.int64]):
    pass


@cv.args_checked
def cell_stuff(a: montepy.Cell):
    pass


@cv.args_checked
def negative(a: typing.Annotated[int, less_than(0)]):
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
        str_pipe_union,
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


@pytest.mark.parametrize(
    "func, good, bads",
    [
        (list_type, [1, 2, 3], ["a", 1, [1, "a"]]),
        (dict_type, {"a": 1, "b": 2}, ["a", 1, [1, "a"], {1: "a"}, {"a": "a"}]),
        (np_array, np.array([1, 2]), ["a", 1, [1, 2], np.array(["a", "b"])]),
    ],
)
def test_iterable_types(func, good, bads):
    func(good)
    for bad in bads:
        with pytest.raises(TypeError):
            func(bad)


def test_mp_namespace():
    cell_stuff(montepy.Cell())
    with pytest.raises(TypeError):
        cell_stuff("a")


@pytest.mark.parametrize("val, raise_error", [(1, True), (-1, False)])
def test_negative(val, raise_error):
    if raise_error:
        with pytest.raises(ValueError):
            negative(val)
    else:
        negative(val)
