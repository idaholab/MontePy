"""
Utilities for checking values

.. note::
    Some of this software was taken from OpenMC.
    See the :download:`LICENSE` file for the specific licenses.
"""

"""
Copyright (c) 2014-2025 Massachusetts Institute of Technology, UChicago Argonne
LLC, Battelle Energy Alliance, and OpenMC contributors

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import copy
import os
from collections.abc import Callable, Iterable
import functools
import inspect
from numbers import Real, Integral
import numpy as np
import typing

import montepy

# Type for arguments that accept file paths
PathLike = str | os.PathLike


def _argtype_default_gen(argspec, attr):
    if attr == "args":
        args = argspec.args
        if argspec.defaults:
            delta_len = len(args) - len(argspec.defaults)
            def_iter = (True,) * delta_len + argspec.defaults
        else:
            def_iter = (True,) * len(args)
        for arg, default in zip(args, def_iter):
            yield arg, default
    else:
        for arg_name in argspec.kwonlyargs:
            default = argspec.kwonlydefaults.get(arg_name, True)
            yield arg_name, default


def _prepare_type_checker(func_name, arg_name, args_spec, none_ok):
    arg_type = args_spec.annotations.get(arg_name, None)
    if arg_type:
        # if annotations are used
        if isinstance(arg_type, str):
            arg_type = eval(arg_type)
        # if annotated
        if isinstance(arg_type, typing._AnnotatedAlias):
            arg_type = arg_type.__args__
        return lambda x: check_type(func_name, arg_name, x, arg_type, none_ok=none_ok)


def _prepare_args_check(func_name, arg_name, args_spec):
    """TODO: simplify with Signature"""
    if arg_name is None:
        return []
    args_check = args_spec.annotations.get(arg_name, None)
    if isinstance(args_check, str):
        args_check = eval(args_check)
    if args_check is None or not isinstance(args_check, typing._AnnotatedAlias):
        return []
    args_check = args_check.__metadata__
    return (checker(func_name, arg_name) for checker in args_check)


def args_checked(func: Callable):
    """
    A function decorator that enforces type annotations for the function when ran.

    This will read the type annotations for all arguments and enforce that the argument is of
    that type at run-time.
    Value restrictions can also be applied as well with ``typing.Annotated``.

    Examples
    ^^^^^^^^

    This will ensure that all arguments have to be an integer,

    .. doctest::

        >>> from montepy.utilities import *
        >>> @args_checked
        ... def foo(a: int) -> int:
        ...    return a
        >>> print(foo(1))
        1
        >>> print(foo("a"))
        Traceback (most recent call last):
        ...
        TypeError: Unable to set "a" for "foo" to "a" which is not of type "int"

    Values can be checked as by using ``typing.Annotated`` to add an annotation of the values that are allowed
    (via a special value checking function),

    .. doctest::

        >>> import typing
        >>> @args_checked
        ... def bar(a: typing.Annotated[int, positive]) -> int:
        ...     return a
        >>> print(bar(1))
        1
        >>> print(bar(0))
        Traceback (most recent call last):
        ...
        ValueError: Unable to set "a" for "bar" to "0" since it is less than or equal to "0"



    Parameters
    ----------
    func: collections.abc.Callable
        The function to decorate

    Returns
    -------
    A decorated function that will do type and value checking at run time based on the annotation.

    Raises
    ------
    TypeError
        If an argument of the wrong type is provided
    ValueError
        If an argument of the right type, but wrong value is given.
    """

    def decorator(func):
        args_spec = inspect.getfullargspec(func)
        arg_checkers = {}
        for attr in ["args", "kwonlyargs"]:
            if attr == "args":
                arg_checkers[attr] = []
            else:
                arg_checkers[attr] = {}
            for arg_name, default in _argtype_default_gen(args_spec, attr):
                none_ok = default is None
                checkers = []
                # build
                type_checker = _prepare_type_checker(
                    func.__qualname__, arg_name, args_spec, none_ok
                )
                if type_checker:
                    checkers.append(type_checker)
                checkers.extend(
                    _prepare_args_check(func.__qualname__, arg_name, args_spec)
                )
                if attr == "args":
                    arg_checkers[attr].append(checkers)
                else:
                    arg_checkers[attr][arg_name] = checkers

        special_checks = {}
        for attr in ("varargs", "varkw"):
            checkers = []
            arg_name = getattr(args_spec, attr, None)
            if arg_name:
                checkers = [
                    _prepare_type_checker(func.__qualname__, arg_name, args_spec, False)
                ]
            checkers.extend(_prepare_args_check(func.__qualname__, arg_name, args_spec))
            special_checks[attr] = checkers

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            args_iter = iter(args)
            for checkers, arg in zip(arg_checkers["args"], args_iter):
                for checker in checkers:
                    checker(arg)
            # iterate over var args
            for arg in args_iter:
                for checker in special_checks["varargs"]:
                    checker(arg)

            for arg_name, arg in kwargs.items():
                if arg_name in arg_checkers["kwonlyargs"]:
                    checkers = arg_checkers["kwonlyargs"][arg_name]
                else:
                    checkers = special_checks["varkw"]
                for checker in checkers:
                    checker(arg)
            return func(*args, **kwargs)

        return wrapper

    return decorator(func)


def check_type(
    func_name: str,
    name: str,
    value: typing.Any,
    expected_type: typing.GenericAlias,
    expected_iter_type: typing.GenericAlias = None,
    *,
    none_ok: bool = False,
):
    """Ensure that an object is of an expected type. Optionally, if the object is
    iterable, check that each element is of a particular type.

    Parameters
    ----------
    func_name : str
        The name of the function this was called from
    name : str
        Description of value being checked
    value : object
        Object to check type of
    expected_type : type or Iterable of type
        type to check object against
    expected_iter_type : type or Iterable of type or None, optional
        Expected type of each element in value, assuming it is iterable. If
        None, no check will be performed.
    none_ok : bool, optional
        Whether None is allowed as a value

    """
    if none_ok and value is None:
        return

    if isinstance(expected_type, typing.GenericAlias):
        return check_type_iterable(
            func_name, name, value, expected_type, none_ok=none_ok
        )
    if not isinstance(value, expected_type):
        if isinstance(expected_type, Iterable):
            msg = (
                'Unable to set "{}" for "{}" to "{}" which is not one of the '
                'following types: "{}"'.format(
                    name,
                    func_name,
                    value,
                    ", ".join([t.__name__ for t in expected_type]),
                )
            )
        elif isinstance(expected_type, type):
            msg = (
                f'Unable to set "{name}" for "{func_name}" to "{value}" which is not of type "'
                f'{expected_type.__name__}"'
            )
        else:
            msg = (
                f'Unable to set "{name}" for "{func_name}" to "{value}" which is not of type "'
                f'{expected_type}"'
            )
        raise TypeError(msg)
    if expected_iter_type:
        if isinstance(value, np.ndarray):
            if not issubclass(value.dtype.type, expected_iter_type):
                msg = (
                    f'Unable to set "{name}" for "{func_name}" to "{value}" since each item '
                    f'must be of type "{expected_iter_type.__name__}"'
                )
                raise TypeError(msg)
            else:
                return

        for item in value:
            if not isinstance(item, expected_iter_type):
                if isinstance(expected_iter_type, Iterable):
                    msg = (
                        'Unable to set "{}" for "{}" to "{}" since each item must be '
                        'one of the following types: "{}"'.format(
                            name,
                            func_name,
                            value,
                            ", ".join([t.__name__ for t in expected_iter_type]),
                        )
                    )
                else:
                    msg = (
                        f'Unable to set "{name}" for "{func_name}" to "{value}" since each '
                        f'item must be of type "{expected_iter_type.__name__}"'
                    )
                raise TypeError(msg)


def check_type_iterable(
    func_name: str,
    name: str,
    value: typing.Any,
    expected_type: typing.GenericAlias,
    *,
    none_ok: bool = False,
):
    """TODO: refactor"""
    base_cls = expected_type.__origin__
    args = expected_type.__args__
    check_type(func_name, name, value, base_cls, none_ok=none_ok)
    if base_cls == dict:
        assert len(args) == 2, "Dict type requires two typing annotations"
        check_type(func_name, name, list(value.keys()), list, args[0], none_ok=none_ok)
        check_type(
            func_name, name, list(value.values()), list, args[1], none_ok=none_ok
        )
    elif issubclass(base_cls, Iterable):
        check_type(func_name, name, value, base_cls, args[0], none_ok=none_ok)


def check_length(func_name, name, value, length_min, length_max=None):
    """Ensure that a sized object has length within a given range.

    Parameters
    ----------
    func_name : str
        The name of the function this was called from
    name : str
        Description of value being checked
    value : collections.Sized
        Object to check length of
    length_min : int
        Minimum length of object
    length_max : int or None, optional
        Maximum length of object. If None, it is assumed object must be of
        length length_min.

    """

    if length_max is None:
        if len(value) < length_min:
            msg = (
                f'Unable to set "{name}" for "{func_name}" to "{value}" since it must be at '
                f'least of length "{length_min}"'
            )
            raise ValueError(msg)
    elif not length_min <= len(value) <= length_max:
        if length_min == length_max:
            msg = (
                f'Unable to set "{name}" for "{func_name}" to "{value}" since it must be of '
                f'length "{length_min}"'
            )
        else:
            msg = (
                f'Unable to set "{name}" for "{func_name}" to "{value}" since it must have '
                f'length between "{length_min}" and "{length_max}"'
            )
        raise ValueError(msg)


def check_increasing(func_name: str, name: str, value, equality: bool = False):
    """Ensure that a list's elements are strictly or loosely increasing.

    Parameters
    ----------
    func_name : str
        The name of the function this was called from
    name : str
        Description of value being checked
    value : iterable
        Object to check if increasing
    equality : bool, optional
        Whether equality is allowed. Defaults to False.

    """
    if equality:
        if not np.all(np.diff(value) >= 0.0):
            raise ValueError(
                f'Unable to set "{name}"  for "{func_name}" to "{value}" since its '
                "elements must be increasing."
            )
    elif not equality:
        if not np.all(np.diff(value) > 0.0):
            raise ValueError(
                f'Unable to set "{name}" for "{func_name}" to "{value}" since its '
                "elements must be strictly increasing."
            )


def check_value(
    func_name: str, name: str, value: typing.GenericAlias, accepted_values: typing.Any
):
    """Ensure that an object's value is contained in a set of acceptable values.

    Parameters
    ----------
    func_name : str
        The name of the function this was called from
    name : str
        Description of value being checked
    value : collections.Iterable
        Object to check
    accepted_values : collections.Container
        Container of acceptable values

    """

    if value not in accepted_values:
        msg = (
            f'Unable to set "{name}" for "{func_name}" to "{value}" since it is not in '
            f'"{accepted_values}"'
        )
        raise ValueError(msg)


def less_than(maximum: Real, equality=False):
    r"""
    A higher-order function for use with ``args_checked`` to enforce a value being less than a value.


    Examples
    ^^^^^^^^
    This can be used to annotate a value

    .. testcode::

        import numbers
        import typing

        @args_checked
        def foo(a: typing.Annotated[numbers.Real, less_than(5)]):
            pass

    Parameters
    ----------
    maximum: Real
        The maximum value to be tested against.
    equality: bool
        if true test for :math:`x\leq m` rather than :math:`x\lt m`
    """

    def wrapper(func_name, name):
        return lambda x: check_less_than(func_name, name, x, maximum, equality)

    return wrapper


def greater_than(minimum: Real, equality: bool = False):
    r"""
    A higher-order function for use with ``args_checked`` to enforce a value being greater than a value.


    Examples
    ^^^^^^^^
    This can be used to annotate a value

    .. testcode::

        import numbers
        import typing

        @args_checked
        def foo(a: typing.Annotated[numbers.Real, greater_than(5)]):
            pass

    Parameters
    ----------
    minimum: Real
        The minimum value to be tested against.
    equality: bool
        if true test for :math:`x\geq m` rather than :math:`x\gt m`
    """

    def wrapper(func_name, name):
        return lambda x: check_greater_than(func_name, name, x, minimum, equality)

    return wrapper


def positive(func_name, name):
    r"""
    A higher-order function to be used with ``args_checked`` to ensure a value is positive,
    i.e., :math:`x\gt 0`.

    Example
    ^^^^^^^

    .. testcode::

        from numbers import Real
        from typing import Annotated

        def foo(a: Annotated[Real, positive]):
            pass

    """
    return lambda x: check_greater_than(func_name, name, x, 0)


def negative(func_name, name):
    r"""
    A higher-order function to be used with ``args_checked`` to ensure a value is negative,
    i.e., :math:`x\lt 0`.

    Example
    ^^^^^^^

    .. testcode::

        from numbers import Real
        from typing import Annotated

        def foo(a: Annotated[Real, negative]):
            pass

    """
    return lambda x: check_less_than(func_name, name, x, 0)


def non_positive(func_name, name):
    r"""
    A higher-order function to be used with ``args_checked`` to ensure a value is non-positive,
    i.e., :math:`x\leq 0`.

    Example
    ^^^^^^^

    .. testcode::

        from numbers import Real
        from typing import Annotated

        def foo(a: Annotated[Real, non_positive]):
            pass

    """
    return lambda x: check_less_than(func_name, name, x, 0, True)


def non_negative(func_name, name):
    r"""
    A higher-order function to be used with ``args_checked`` to ensure a value is non-negative,
    i.e., :math:`x\geq 0`.

    Example
    ^^^^^^^

    .. testcode::

        from numbers import Real
        from typing import Annotated

        def foo(a: Annotated[Real, non_negative]):
            pass

    """
    return lambda x: check_greater_than(func_name, name, x, 0, True)


def check_less_than(func_name: str, name: str, value, maximum, equality=False):
    """Ensure that an object's value is less than a given value.

    Parameters
    ----------
    func_name : str
        The name of the function this was called from
    name : str
        Description of the value being checked
    value : object
        Object to check
    maximum : object
        Maximum value to check against
    equality : bool, optional
        Whether equality is allowed. Defaults to False.

    """

    if equality:
        if value > maximum:
            msg = (
                f'Unable to set "{name}" for "{func_name}" to "{value}" since it is greater '
                f'than "{maximum}"'
            )
            raise ValueError(msg)
    else:
        if value >= maximum:
            msg = (
                f'Unable to set "{name}" for "{func_name}" to "{value}" since it is greater '
                f'than or equal to "{maximum}"'
            )
            raise ValueError(msg)


def check_greater_than(func_name, name, value, minimum, equality=False):
    """Ensure that an object's value is greater than a given value.

    Parameters
    ----------
    func_name : str
        The name of the function this was called from
    name : str
        Description of the value being checked
    value : object
        Object to check
    minimum : object
        Minimum value to check against
    equality : bool, optional
        Whether equality is allowed. Defaults to False.

    """

    if equality:
        if value < minimum:
            msg = (
                f'Unable to set "{name}" for "{func_name}" to "{value}" since it is less than '
                f'"{minimum}"'
            )
            raise ValueError(msg)
    else:
        if value <= minimum:
            msg = (
                f'Unable to set "{name}" for "{func_name}" to "{value}" since it is less than '
                f'or equal to "{minimum}"'
            )
            raise ValueError(msg)


class CheckedList(list):
    """A list for which each element is type-checked as it's added

    Parameters
    ----------
    expected_type : type or Iterable of type
        Type(s) which each element should be
    name : str
        Name of data being checked
    items : Iterable, optional
        Items to initialize the list with

    """

    def __init__(self, expected_type, name, items=None):
        super().__init__()
        self.expected_type = expected_type
        self.name = name
        if items is not None:
            for item in items:
                self.append(item)

    def __add__(self, other):
        new_instance = copy.copy(self)
        new_instance += other
        return new_instance

    def __radd__(self, other):
        return self + other

    def __iadd__(self, other):
        check_type(
            "CheckedList add operand", self.name, other, Iterable, self.expected_type
        )
        for item in other:
            self.append(item)
        return self

    def append(self, item):
        """Append item to list

        Parameters
        ----------
        item : object
            Item to append

        """
        check_type("CheckedList.append", self.name, item, self.expected_type)
        super().append(item)

    def insert(self, index, item):
        """Insert item before index

        Parameters
        ----------
        index : int
            Index in list
        item : object
            Item to insert

        """
        check_type("CheckedList.insert", self.name, item, self.expected_type)
        super().insert(index, item)
