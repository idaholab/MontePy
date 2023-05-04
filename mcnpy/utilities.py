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


def make_prop_val_node(
    hidden_param, types=None, base_type=None, validator=None, deletable=False
):
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
