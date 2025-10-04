import functools
from abc import ABC, ABCMeta, abstractmethod

from montepy.exceptions import *


class _ExceptionContextAdder(ABCMeta):
    """A metaclass for wrapping all class properties and methods in :func:`~montepy.errors.add_line_number_to_exception`."""

    @staticmethod
    def _wrap_attr_call(func):
        """Wraps the function, and returns the modified function."""

        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            from montepy.mcnp_object import MCNP_Object

            try:
                return func(*args, **kwargs)
            except Exception as e:
                if len(args) > 0 and isinstance(args[0], MCNP_Object):
                    self = args[0]
                    if hasattr(self, "_handling_exception"):
                        raise e
                    self._handling_exception = True
                    try:
                        add_line_number_to_exception(e, self)
                    finally:
                        del self._handling_exception
                else:
                    raise e

        if isinstance(func, staticmethod):
            return staticmethod(wrapped)
        if isinstance(func, classmethod):
            return classmethod(wrapped)
        return wrapped

    def __new__(meta, classname, bases, attributes):
        """This will replace all properties and callable attributes with
        wrapped versions.
        """
        new_attrs = {}
        for key, value in attributes.items():
            if key.startswith("_"):
                new_attrs[key] = value
            if callable(value):
                new_attrs[key] = _ExceptionContextAdder._wrap_attr_call(value)
            elif isinstance(value, property):
                new_props = {}
                for attr_name in {"fget", "fset", "fdel", "doc"}:
                    try:
                        assert getattr(value, attr_name)
                        new_props[attr_name] = _ExceptionContextAdder._wrap_attr_call(
                            getattr(value, attr_name)
                        )
                    except (AttributeError, AssertionError):
                        new_props[attr_name] = None

                new_attrs[key] = property(**new_props)
            else:
                new_attrs[key] = value
        cls = super().__new__(meta, classname, bases, new_attrs)
        return cls
