# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.constants import BLANK_SPACE_CONTINUE
import functools
import re

"""
A package for helper universal utility functions
"""


def fortran_float(number_string):
    """
    Attempts to convert a FORTRAN formatted float string to a float.

    FORTRAN allows silly things for scientific notation like ``6.02+23``
    to represent Avogadro's Number.

    :param number_string: the string that will be converted to a float
    :type number_string: str
    :raises ValueError: If the string can not be parsed as a float.
    :return: the parsed float of the this string
    :rtype: float
    """
    try:
        return float(number_string)

    except ValueError as e:
        update_number = re.sub(r"(\d)([-+])", r"\1E\2", number_string)
        try:
            return float(update_number)
        except ValueError:
            raise ValueError(f"Value Not parsable as float: {number_string}") from e


def is_comment(line):
    """
    Determines if the line is a ``C comment`` style comment.

    :param line: the line to analyze
    :type line: str
    :returns: True if the line is a comment
    :rtype: bool
    """
    upper_start = line[0 : BLANK_SPACE_CONTINUE + 1].upper()
    non_blank_comment = upper_start and line.lstrip().upper().startswith("C ")
    if non_blank_comment:
        return True
    blank_comment = ("C" == upper_start.strip() and "\n" in line) or (
        "C" == upper_start and "\n" not in line
    )
    return blank_comment


def make_prop_val_node(
    hidden_param, types=None, base_type=None, validator=None, deletable=False
):
    """
    A decorator function for making a property from a ValueNode.

    This decorator is meant to handle all boiler plate. It will get and
    set the value property of the underlying ValueNode.
    By default the property is not settable unless types is set.

    :param hidden_param: The string representing the parameter name of the internally stored ValueNode.
    :type hidden_param: str
    :param types: the acceptable types for the settable, which is passed to isinstance. If an empty tuple will be
                type(self).
    :type types: Class, tuple
    :param validator: A validator function to run on values before setting. Must accept func(self, value).
    :type validator: function
    :param deletable: If true make this property deletable. When deleted the value will be set to None.
    :type deletable: bool
    """

    def decorator(func):
        @property
        @functools.wraps(func)
        def getter(self):
            result = func(self)
            if result:
                return result
            else:
                val = getattr(self, hidden_param)
                if val is None:
                    return None
                return val.value

        if types is not None:

            def setter(self, value):
                nonlocal types
                if isinstance(types, tuple) and len(types) == 0:
                    types = type(self)
                if not isinstance(value, types):
                    raise TypeError(
                        f"{func.__name__} must be of type: {types}. {value} given."
                    )
                if (
                    base_type is not None
                    and value is not None
                    and not isinstance(value, base_type)
                ):
                    value = base_type(value)
                if validator:
                    validator(self, value)
                node = getattr(self, hidden_param)
                node.value = value

            getter = getter.setter(setter)

        if deletable:

            def deleter(self):
                setattr(self, hidden_param, None)

            getter = getter.deleter(deleter)
        return getter

    return decorator


def make_prop_pointer(
    hidden_param, types=None, base_type=None, validator=None, deletable=False
):
    """
    A decorator function that makes a property based off of a pointer to another object.

    Note this can also be used for almost any circumstance as everything in python is a pointer.

    :param hidden_param: The string representing the parameter name of the internally stored ValueNode.
    :type hidden_param: str
    :param types: the acceptable types for the settable, which is passed to isinstance, if an empty tuple is provided the type will be self.
    :type types: Class, tuple
    :param validator: A validator function to run on values before setting. Must accept func(self, value).
    :type validator: function
    :param deletable: If true make this property deletable. When deleted the value will be set to None.
    :type deletable: bool
    """

    def decorator(func):
        @property
        @functools.wraps(func)
        def getter(self):
            result = func(self)
            if result:
                return result
            return getattr(self, hidden_param)

        if types is not None:

            def setter(self, value):
                nonlocal types
                if isinstance(types, tuple) and len(types) == 0:
                    types = type(self)
                if not isinstance(value, types):
                    raise TypeError(f"{func.__name__} must be of type: {types}")
                if base_type is not None and not isinstance(value, base_type):
                    value = base_type(value)
                if validator:
                    validator(self, value)
                setattr(self, hidden_param, value)

            getter = getter.setter(setter)
        if deletable:

            def deleter(self):
                setattr(self, hidden_param, None)

            getter = getter.deleter(deleter)
        return getter

    return decorator
