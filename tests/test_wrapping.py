import functools
import types

import pytest

import montepy
from montepy import _wrapping
from montepy._check_value import args_checked


def _count_calls(func):
    calls = []

    @_wrapping.wraps(func)
    def wrapper(*args, **kwargs):
        calls.append(args)
        return func(*args, **kwargs)

    wrapper.calls = calls
    return wrapper


def test_wrapper_globals_name_the_wrapped_module():
    # Regression test: a wrapper ran in the globals of the module defining the
    # decorator, so sphinx_autodoc_typehints evaluated the wrapped function's
    # annotations there and couldn't resolve names like PaddingNode.
    getter = montepy.Cell.trailing_comment.fget
    assert getter.__globals__["__name__"] == "montepy.mcnp_object"
    groups = montepy.CellFluxTally.groups.fget
    assert groups.__globals__["__name__"] == "montepy.data_inputs.tally"


def test_wrapped_annotation_resolves_in_wrapped_module():
    module = types.ModuleType("_wrapping_test_module")
    exec(
        "from __future__ import annotations\n"
        "class Local: pass\n"
        "def func(x) -> Local:\n"
        "    return x\n",
        module.__dict__,
    )
    wrapped = _count_calls(module.func)
    namespace = {**vars(module), **wrapped.__globals__}
    assert eval(wrapped.__annotations__["return"], namespace) is module.Local
    assert wrapped.__globals__["__name__"] == "_wrapping_test_module"


def test_rebuilt_wrapper_behaves_the_same():
    def add(a, b=2, *, c=3):
        return a + b + c

    wrapped = _count_calls(add)
    assert wrapped(1) == 6
    assert wrapped(1, 1, c=1) == 3
    assert wrapped.calls == [(1,), (1, 1)]
    assert wrapped.__wrapped__ is add
    assert wrapped.__name__ == "add"


def test_function_without_module_is_left_alone():
    namespace = {"args_checked": args_checked}
    exec("@args_checked\ndef foo(a: int) -> int:\n    return a\n", namespace)
    assert namespace["foo"](1) == 1
    with pytest.raises(TypeError):
        namespace["foo"]("a")


def test_staticmethod():
    def double(x):
        return 2 * x

    wrapped = _wrapping.in_module_of(
        functools.wraps(double)(lambda x: double(x)), staticmethod(double)
    )
    assert wrapped(2) == 4


def test_mcnp_object_errors_still_get_context():
    cell = montepy.Cell("1 0 -1")
    with pytest.raises(ValueError):
        cell.number = -5
