from hypothesis import given
import hypothesis.strategies as st
import numpy as np
import pytest
import typing

import montepy._check_value as cv
import montepy


@cv.check_arguments
def simple_args(a: str):
    pass


def var_args(a: str):
    @cv.check_arguments
    def ret(a: str, *args: str):
        pass

    return ret("1", a, a)


def kwargs(a: str):
    @cv.check_arguments
    def ret(**kwargs: str):
        pass

    return ret(foo=a)


@cv.check_arguments
def defaults(a: str, *args: str, b: str = None):
    pass


def kw_only(a: str):
    return defaults("1", "1", "1", b=a)


def defaults_used(a: str):
    return defaults("1")


def kw_defaults(a: str):
    @cv.check_arguments
    def ret(a: str, *args: str, b: str = None, **kwargs: str):
        pass

    return ret("1", foo=a)


@cv.check_arguments
def union_type(a: typing.Union[montepy.Cell, str]):
    pass


@cv.check_arguments
def pipe_union_type(a: montepy.Cell | str):
    pass


@cv.check_arguments
def negative(a: typing.Annotated[int, cv.enforce_less_than(0)]):
    pass


@cv.check_arguments
def list_type(a: list[int]):
    pass


@cv.check_arguments
def dict_type(a: dict[str, int]):
    pass


@cv.check_arguments
def np_array(a: np.ndarray[np.int64]):
    pass


binary = st.binary()
boolean = st.booleans()
chars = st.characters()
dt = st.datetimes()
fl = st.floats()
it = st.integers()
no = st.none()


@given(
    st.one_of(binary, boolean, dt, fl, it, no),
    st.sampled_from(
        [simple_args, var_args, kwargs, kw_defaults, union_type, pipe_union_type]
    ),
)
def test_dummy_bad_type_with_none(val, func):
    with pytest.raises(TypeError):
        func(val)


@given(
    st.one_of(binary, boolean, dt, fl, it),
    st.sampled_from(
        [
            simple_args,
            var_args,
            kwargs,
            kw_only,
            kw_defaults,
        ]
    ),
)
def test_dummy_bad_type_no_none(val, func):
    with pytest.raises(TypeError):
        func(val)


@given(
    st.one_of(chars),
    st.sampled_from(
        [
            simple_args,
            var_args,
            kwargs,
            kw_only,
            kw_defaults,
        ]
    ),
)
def test_dummy_good_type(val, func):
    func(val)


@given(st.one_of(chars, no), st.sampled_from([kw_only]))
def test_none_default(val, func):
    func(val)


@pytest.mark.parametrize("val, raise_error", [(1, True), (-1, False)])
def test_negative(val, raise_error):
    if raise_error:
        with pytest.raises(ValueError):
            negative(val)
    else:
        negative(val)


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
