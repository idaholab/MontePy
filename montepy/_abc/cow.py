# Copyright 2025, Battelle Energy Alliance, LLC All Rights Reserved.
import copy
from typing import Self

"""
Moooooooo
"""


class UdderType:

    def __new__(meta, classname, bases, attributes):
        UdderType.prepare_getter(attributes, "__getattr__")
        UdderType.prepare_getter(attributes, "__setattr__")
        if "__getitem__" in attributes:
            UdderType.prepare_getter(attributes, "__getitem__")
            UdderType.prepare_setter(attributes, "__setitem__")
        cls = super().__new__(meta, classname, bases, attributes)
        return cls

    @staticmethod
    def prepare_getter(attributes, attr_name):
        attributes[f"_old{attr_name}"] = attributes[attr_name]

        def wrapped(self, key):
            if "__" in key:
                return super().__getattr__(key)
            return getattr(self._heffer, old_func.__name__)(key)

        attributes[attr_name] = wrapped

    @staticmethod
    def prepare_setter(attributes, attr_name):
        def wrapper(self, key, value):
            if key.startswith("_"):
                getattr(self, attr_name)(key, value)
            # TODO cowDict
            # if isinstance(self, dict):
            #    MalformedInputError
            self.__dict__.extend(copy.deepcopy(self._heffer.__dict__))
            del self._heffer
            self.__dict__[attr_name] = getattr(self, f"_old{attr_name}")
            getattr(self, attr_name)(key, value)


class Moo(metaclass=UdderType):

    def copy(self) -> Self:
        blank = super().__new__()
        if not hasattr(self, "_heffer"):
            blank._heffer = self
        else:
            blank._heffer = self._heffer
