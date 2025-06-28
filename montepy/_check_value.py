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
from collections.abc import Iterable
import functools
import inspect
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
    if arg_name is None:
        return []
    args_check = args_spec.annotations.get(arg_name, None)
    if isinstance(args_check, str):
        args_check = eval(args_check)
    if args_check is None or not isinstance(args_check, typing._AnnotatedAlias):
        return []
    args_check = args_check.__metadata__
    return (checker(func_name, arg_name) for checker in args_check)


def check_arguments(func):
    """ """

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
    func_name, name, value, expected_type, expected_iter_type=None, *, none_ok=False
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
                    func_name,
                    name,
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
                    f'Unable to set "{name}" to "{value}" since each item '
                    f'must be of type "{expected_iter_type.__name__}"'
                )
                raise TypeError(msg)
            else:
                return

        for item in value:
            if not isinstance(item, expected_iter_type):
                if isinstance(expected_iter_type, Iterable):
                    msg = (
                        'Unable to set "{}" to "{}" since each item must be '
                        'one of the following types: "{}"'.format(
                            name,
                            value,
                            ", ".join([t.__name__ for t in expected_iter_type]),
                        )
                    )
                else:
                    msg = (
                        f'Unable to set "{name}" to "{value}" since each '
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
    """ """
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


def check_iterable_type(name, value, expected_type, min_depth=1, max_depth=1):
    """Ensure that an object is an iterable containing an expected type.

    Parameters
    ----------
    name : str
        Description of value being checked
    value : Iterable
        Iterable, possibly of other iterables, that should ultimately contain
        the expected type
    expected_type : type
        type that the iterable should contain
    min_depth : int
        The minimum number of layers of nested iterables there should be before
        reaching the ultimately contained items
    max_depth : int
        The maximum number of layers of nested iterables there should be before
        reaching the ultimately contained items
    """
    # Initialize the tree at the very first item.
    tree = [value]
    index = [0]

    # Traverse the tree.
    while index[0] != len(tree[0]):
        # If we are done with this level of the tree, go to the next branch on
        # the level above this one.
        if index[-1] == len(tree[-1]):
            del index[-1]
            del tree[-1]
            index[-1] += 1
            continue

        # Get a string representation of the current index in case we raise an
        # exception.
        form = "[" + "{:d}, " * (len(index) - 1) + "{:d}]"
        ind_str = form.format(*index)

        # What is the current item we are looking at?
        current_item = tree[-1][index[-1]]

        # If this item is of the expected type, then we've reached the bottom
        # level of this branch.
        if isinstance(current_item, expected_type):
            # Is this deep enough?
            if len(tree) < min_depth:
                msg = (
                    f'Error setting "{name}": The item at {ind_str} does not '
                    f"meet the minimum depth of {min_depth}"
                )
                raise TypeError(msg)

            # This item is okay.  Move on to the next item.
            index[-1] += 1

        # If this item is not of the expected type, then it's either an error or
        # on a deeper level of the tree.
        else:
            if isinstance(current_item, Iterable):
                # The tree goes deeper here, let's explore it.
                tree.append(current_item)
                index.append(0)

                # But first, have we exceeded the max depth?
                if len(tree) > max_depth:
                    msg = (
                        f"Error setting {name}: Found an iterable at "
                        f"{ind_str}, items in that iterable exceed the "
                        f"maximum depth of {max_depth}"
                    )
                    raise TypeError(msg)

            else:
                # This item is completely unexpected.
                msg = (
                    f"Error setting {name}: Items must be of type "
                    f'"{expected_type.__name__}", but item at {ind_str} is '
                    f'of type "{type(current_item).__name__}"'
                )
                raise TypeError(msg)


def check_length(name, value, length_min, length_max=None):
    """Ensure that a sized object has length within a given range.

    Parameters
    ----------
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
                f'Unable to set "{name}" to "{value}" since it must be at '
                f'least of length "{length_min}"'
            )
            raise ValueError(msg)
    elif not length_min <= len(value) <= length_max:
        if length_min == length_max:
            msg = (
                f'Unable to set "{name}" to "{value}" since it must be of '
                f'length "{length_min}"'
            )
        else:
            msg = (
                f'Unable to set "{name}" to "{value}" since it must have '
                f'length between "{length_min}" and "{length_max}"'
            )
        raise ValueError(msg)


def check_increasing(name: str, value, equality: bool = False):
    """Ensure that a list's elements are strictly or loosely increasing.

    Parameters
    ----------
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
                f'Unable to set "{name}" to "{value}" since its '
                "elements must be increasing."
            )
    elif not equality:
        if not np.all(np.diff(value) > 0.0):
            raise ValueError(
                f'Unable to set "{name}" to "{value}" since its '
                "elements must be strictly increasing."
            )


def check_value(name, value, accepted_values):
    """Ensure that an object's value is contained in a set of acceptable values.

    Parameters
    ----------
    name : str
        Description of value being checked
    value : collections.Iterable
        Object to check
    accepted_values : collections.Container
        Container of acceptable values

    """

    if value not in accepted_values:
        msg = (
            f'Unable to set "{name}" to "{value}" since it is not in '
            f'"{accepted_values}"'
        )
        raise ValueError(msg)


def enforce_less_than(maximum, equality=False):
    def wrapper(func_name, name):
        return lambda x: check_less_than(name, x, maximum, equality, func_name)

    return wrapper


def check_less_than(name, value, maximum, equality=False, func_name=None):
    """Ensure that an object's value is less than a given value.

    Parameters
    ----------
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
                f'Unable to set "{name}" to "{value}" since it is greater '
                f'than "{maximum}"'
            )
            raise ValueError(msg)
    else:
        if value >= maximum:
            msg = (
                f'Unable to set "{name}" to "{value}" since it is greater '
                f'than or equal to "{maximum}"'
            )
            raise ValueError(msg)


def check_greater_than(name, value, minimum, equality=False):
    """Ensure that an object's value is greater than a given value.

    Parameters
    ----------
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
                f'Unable to set "{name}" to "{value}" since it is less than '
                f'"{minimum}"'
            )
            raise ValueError(msg)
    else:
        if value <= minimum:
            msg = (
                f'Unable to set "{name}" to "{value}" since it is less than '
                f'or equal to "{minimum}"'
            )
            raise ValueError(msg)


def check_filetype_version(obj, expected_type, expected_version):
    """Check filetype and version of an HDF5 file.

    Parameters
    ----------
    obj : h5py.File
        HDF5 file to check
    expected_type : str
        Expected file type, e.g. 'statepoint'
    expected_version : int
        Expected major version number.

    """
    try:
        this_filetype = obj.attrs["filetype"].decode()
        this_version = obj.attrs["version"]

        # Check filetype
        if this_filetype != expected_type:
            raise IOError(f"{obj.filename} is not a {expected_type} file.")

        # Check version
        if this_version[0] != expected_version:
            raise IOError(
                "{} file has a version of {} which is not "
                "consistent with the version expected by OpenMC, {}".format(
                    this_filetype,
                    ".".join(str(v) for v in this_version),
                    expected_version,
                )
            )
    except AttributeError:
        raise IOError(
            f"Could not read {obj.filename} file. This most likely "
            "means the file was produced by a different version of "
            "OpenMC than the one you are using."
        )


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
        check_type("CheckedList add operand", other, Iterable, self.expected_type)
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
        check_type(self.name, item, self.expected_type)
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
        check_type(self.name, item, self.expected_type)
        super().insert(index, item)
