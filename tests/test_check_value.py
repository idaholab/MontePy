from collections.abc import Iterable
from hypothesis import assume, given, example
import hypothesis.strategies as st
import numpy as np
import pytest
import typing

import montepy._check_value as cv
import montepy.types as ty
import montepy


class Tester:

    @property
    def prop_test(self):
        pass

    @prop_test.setter
    @cv.args_checked
    def prop_test(self, value: str):
        pass

    @property
    def prop_value_test(self):
        pass

    @prop_value_test.setter
    @cv.args_checked
    def prop_value_test(self, value: ty.PositiveReal):
        pass


@cv.args_checked
def simple_args(a: str):
    pass


def var_args(a: str):
    @cv.args_checked
    def ret(a: str, *args: str):
        pass

    return ret("1", a, a)


def kwargs(a: str):
    @cv.args_checked
    def ret(**kwargs: str):
        pass

    return ret(foo=a)


@cv.args_checked
def defaults(a: str, *args: str, b: str = None):
    pass


def kw_only(a: str):
    return defaults("1", "1", "1", b=a)


def defaults_used(a: str):
    return defaults("1")


def kw_defaults(a: str):
    @cv.args_checked
    def ret(a: str, *args: str, b: str = None, **kwargs: str):
        pass

    return ret("1", foo=a)


@cv.args_checked
def union_type(a: typing.Union[montepy.Cell, str]):
    pass


@cv.args_checked
def pipe_union_type(a: montepy.Cell | str):
    pass


@cv.args_checked
def union_generic_alias(a: Iterable[montepy.Cell] | str):
    pass


@cv.args_checked
def negative_hard(a: typing.Annotated[int, cv.less_than(0)]):
    pass


@cv.args_checked
def positive_hard(a: typing.Annotated[int, cv.greater_than(0)]):
    pass


@cv.args_checked
def negative(a: typing.Annotated[int, montepy.types.negative]):
    pass


@cv.args_checked
def positive(a: typing.Annotated[int, montepy.types.positive]):
    pass


@cv.args_checked
def non_negative(a: typing.Annotated[int, montepy.types.non_negative]):
    pass


@cv.args_checked
def non_positive(a: typing.Annotated[int, montepy.types.non_positive]):
    pass


@cv.args_checked
def list_type(a: list[int]):
    pass


@cv.args_checked
def dict_type(a: dict[str, int]):
    pass


@cv.args_checked
def tuple_type(a: tuple[int, str]):
    pass


@cv.args_checked
def iterable_tuple_type(a: Iterable[tuple[str, str]]):
    pass


@cv.args_checked
def dict_tuple_type(a: dict[int, tuple[str, str]]):
    pass


@cv.args_checked
def np_array(a: np.ndarray[np.int64]):
    pass


@cv.args_checked
def np_array_union(a: np.ndarray[montepy.Cell | int]):
    pass


@cv.args_checked
def pos_int(a: ty.PositiveInt):
    pass


@cv.args_checked
def neg_int(a: ty.NegativeInt):
    pass


@cv.args_checked
def pos_real(a: ty.PositiveReal):
    pass


@cv.args_checked
def neg_real(a: ty.NegativeReal):
    pass


binary = st.binary()
boolean = st.booleans()
chars = st.characters()
dt = st.datetimes()
fl = st.floats()
it = st.integers()
no = st.none()


@example(5, union_generic_alias)
@given(
    st.one_of(binary, boolean, dt, fl, it, no),
    st.sampled_from(
        [
            simple_args,
            var_args,
            kwargs,
            kw_defaults,
            union_type,
            pipe_union_type,
            union_generic_alias,
        ]
    ),
)
def test_dummy_bad_type_with_none(val, func):
    assume(not (isinstance(val, Iterable) and len(val) == 0))
    func("hi")
    with pytest.raises(TypeError, match="Unable to set.+"):
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
    with pytest.raises(TypeError, match="Unable to set.+"):
        func(val)


def test_property():
    test = Tester()
    test.prop_test = "hi"
    test.prop_value_test = 5
    with pytest.raises(TypeError, match="Unable to set.+"):
        test.prop_test = 5
    with pytest.raises(TypeError, match="Unable to set.+"):
        test.prop_value_test = "hi"
    with pytest.raises(ValueError):
        test.prop_value_test = -1


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


@pytest.mark.parametrize(
    "func, val, raise_error",
    [
        (negative_hard, 1, True),
        (negative_hard, -1, False),
        (negative, 1, True),
        (negative, -1, False),
        (non_negative, 0, False),
        (non_negative, -1, True),
        (positive, 1, False),
        (positive, -1, True),
        (positive_hard, 1, False),
        (positive_hard, -1, True),
        (non_positive, 1, True),
        (non_positive, 0, False),
    ],
)
def test_pos_neg(func, val, raise_error):
    if raise_error:
        with pytest.raises(ValueError):
            func(val)
    else:
        func(val)


@pytest.mark.parametrize(
    "func, good, bads",
    [
        (list_type, [1, 2, 3], ["a", 1, [1, "a"]]),
        (dict_type, {"a": 1, "b": 2}, ["a", 1, [1, "a"], {1: "a"}, {"a": "a"}]),
        (np_array, np.array([1, 2]), ["a", 1, [1, 2], np.array(["a", "b"])]),
        (
            np_array_union,
            np.array([1, 2]),
            ["a", 1, [1, 2], np.array([montepy.Cell(), montepy.Cell()])],
        ),
        (tuple_type, (1, "hi"), [[1], ("hi", 1), {1: "hi"}]),
        (iterable_tuple_type, [("hi", "foo"), ("a", "b")], ["a", [1, 2], [(1, 5)]]),
        (
            dict_tuple_type,
            {1: ("hi", "foo"), 2: ("a", "b")},
            ["a", [1, 2], [(1, 5)], {"a": "c"}, {1: ("a" "b")}],
        ),
        (pos_int, 5, [1.0, "hi", 0, -1]),
        (neg_int, -3, [1.0, "hi", 0, 2]),
        (pos_real, 1.5, ["hi", 0, -2]),
        (neg_real, -1.5, ["hi", 0, 2.0]),
    ],
)
def test_iterable_types(func, good, bads):
    func(good)
    for bad in bads:
        with pytest.raises(TypeError, match="Unable to set.+"):
            func(bad)


@pytest.mark.parametrize(
    "func, good, bads",
    [
        (
            pos_int,
            5,
            [(1.0, TypeError), ("hi", TypeError), (0, ValueError), (-1, ValueError)],
        ),
        (
            neg_int,
            -3,
            [(1.0, TypeError), ("hi", TypeError), (0, ValueError), (2, ValueError)],
        ),
        (pos_real, 1.5, [("hi", TypeError), (0, ValueError), (-2, ValueError)]),
        (neg_real, -1.5, [("hi", TypeError), (0, ValueError), (2.0, ValueError)]),
    ],
)
def test_iterable_types(func, good, bads):
    func(good)
    for bad, exc in bads:
        with pytest.raises(exc):
            func(bad)


@pytest.mark.parametrize(
    "func, fail, args",
    [
        # check_type
        (cv.check_type, True, ("hi", int)),
        (cv.check_type, False, (1, int)),
        (cv.check_type, True, ("hi", (int, bool))),
        (cv.check_type, False, (1, (int, bool))),
        # check_type with iterable arg
        (cv.check_type, True, ("hi", list, int)),
        (cv.check_type, False, ([1], list, int)),
        (cv.check_type, True, (["hi"], list, int)),
        (cv.check_type, True, (1, list, int)),
        (cv.check_type, True, (["hi"], list, (int, bool))),
        (cv.check_type, True, (1, list, (int, bool))),
        # check_type_iterable
        (cv.check_type_iterable, True, ("hi", list[int])),
        (cv.check_type_iterable, False, ([1], list[int])),
        (cv.check_type_iterable, True, ("hi", dict[int, str])),
        (cv.check_type_iterable, True, ({"hi": 1}, dict[int, str])),
        (cv.check_type_iterable, True, ({1: 1}, dict[int, str])),
        (cv.check_type_iterable, False, ({1: "hi"}, dict[int, str])),
    ],
)
def test_other_type_checks(func, fail, args):
    if fail:
        with pytest.raises(TypeError, match="Unable to set.+"):
            func("foo", "bar", *args)
    else:
        func("foo", "bar", *args)


@pytest.mark.parametrize(
    "func, fail, args",
    [
        # check_less_than
        (cv.check_less_than, True, (0, -1)),
        (cv.check_less_than, True, (0, -1, True)),
        (cv.check_less_than, True, (0, 0)),
        (cv.check_less_than, False, (0, 0, True)),
        (cv.check_less_than, False, (0, 1)),
        # check_greater_than
        (cv.check_greater_than, False, (0, -1)),
        (cv.check_greater_than, True, (-1, 0, True)),
        (cv.check_greater_than, True, (0, 0)),
        (cv.check_greater_than, False, (0, 0, True)),
        (cv.check_greater_than, True, (0, 1)),
        # check_length
        (cv.check_length, False, ([1], 1)),
        (cv.check_length, True, ([], 1)),
        (cv.check_length, False, ([1], 1, 5)),
        (cv.check_length, True, ([1] * 6, 1, 5)),
        (cv.check_length, False, ([1], 1, 1)),
        (cv.check_length, True, ([], 1, 1)),
        # check_increasing
        (cv.check_increasing, False, (range(5),)),
        (cv.check_increasing, False, (range(5), True)),
        (cv.check_increasing, True, (range(5, 1, -1),)),
        (cv.check_increasing, True, (range(5, 1, -1), True)),
        (cv.check_increasing, False, ([1] * 5, True)),
        (cv.check_increasing, True, ([1] * 5,)),
        # check_value
        (cv.check_value, False, (1, range(5))),
        (cv.check_value, True, (10, range(5))),
        (cv.check_value, False, ("a", set("abc"))),
        (cv.check_value, True, ("A", set("abc"))),
    ],
)
def test_other_value_checks(func, fail, args):
    if fail:
        with pytest.raises(ValueError):
            func("foo", "bar", *args)
    else:
        func("foo", "bar", *args)


def test_checked_list_bad():
    check_list = cv.CheckedList(int, "snake")
    with pytest.raises(TypeError, match="Unable to set.+"):
        check_list.append("hi")
    with pytest.raises(TypeError, match="Unable to set.+"):
        check_list + ["a"]
    with pytest.raises(TypeError, match="Unable to set.+"):
        ["a"] + check_list
    with pytest.raises(TypeError, match="Unable to set.+"):
        check_list += ["a"]
    with pytest.raises(TypeError, match="Unable to set.+"):
        check_list.insert(1, "hi")
    with pytest.raises(TypeError, match="Unable to set.+"):
        check_list = cv.CheckedList(int, "snake", ["hi"])


def test_checked_list_good():
    check_list = cv.CheckedList(int, "snake", [1, 2, 3])
    check_list.append(7)
    assert len(check_list) == 4
    assert 7 in check_list
    assert len(check_list + [8]) == 5
    assert len([8] + check_list) == 5
    check_list += [8]
    assert len(check_list) == 5
    check_list.insert(0, 5)
    assert check_list[0] == 5
    assert len(check_list) == 6
