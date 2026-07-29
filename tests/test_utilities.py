# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import pytest
from montepy.utilities import (
    fortran_float,
    make_prop_pointer,
    make_prop_val_node,
    prop_pointer_collect_from_problem,
)

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


class _FakeProblem:
    """A minimal stand-in for MCNP_Problem, exposing one numbered collection."""

    def __init__(self, items):
        self.items = items


class _CollectHolder:
    """A minimal stand-in for an MCNP_Object with a collection pulled from a problem."""

    def __init__(self, ids, problem=None):
        self._ids = ids
        self._problem = problem

    @prop_pointer_collect_from_problem("_pulled", "_ids", "items", list)
    def pulled(self):
        pass


def test_prop_pointer_collect_from_problem_pulls_objects():
    prob = _FakeProblem({1: "a", 2: "b"})
    holder = _CollectHolder([1, 2], prob)
    assert holder.pulled == ["a", "b"]


def test_prop_pointer_collect_from_problem_no_problem():
    holder = _CollectHolder([1, 2], None)
    assert holder.pulled == []


def test_prop_pointer_collect_from_problem_no_ids():
    prob = _FakeProblem({1: "a"})
    holder = _CollectHolder(None, prob)
    assert holder.pulled == []


def test_prop_pointer_collect_from_problem_already_populated():
    prob = _FakeProblem({1: "a"})
    holder = _CollectHolder([1], prob)
    holder._pulled = ["preset"]
    assert holder.pulled == ["preset"]


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


class _FakeNode:
    def __init__(self):
        self.value = None


def test_make_prop_val_node_self_referential_type():
    class _SelfTyped:
        def __init__(self):
            self._val = _FakeNode()

        @make_prop_val_node("_val", types=())
        def val(self):
            pass

    holder = _SelfTyped()
    other = _SelfTyped()
    holder.val = other
    assert holder._val.value is other
    with pytest.raises(TypeError):
        holder.val = "not a _SelfTyped"
