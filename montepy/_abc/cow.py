# Copyright 2025, Battelle Energy Alliance, LLC All Rights Reserved.
import copy
from typing import Self

"""
Moooooooo
"""


class UdderType(type):

    def __new__(meta, classname, bases, attributes):
        print(meta, classname, bases, attributes)
        UdderType.prepare_getter(attributes, "__getattr__")
        UdderType.prepare_setter(attributes, "__setattr__")
        if "__getitem__" in attributes:
            UdderType.prepare_getter(attributes, "__getitem__")
            UdderType.prepare_setter(attributes, "__setitem__")
        cls = super().__new__(meta, classname, bases, attributes)
        return cls

    @staticmethod
    def prepare_getter(attributes, attr_name):
        attributes[f"_old{attr_name}"] = attributes.get(attr_name, None)

        def wrapped(self, key):
            if "__" in key or key == "_heffer":
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
            self.__dict__.update(copy.deepcopy(self._heffer.__dict__))
            del self._heffer
            old_attr = getattr(self, f"_old{attr_name}")
            if old_attr:
                self.__dict__[attr_name] = getattr(self, f"_old{attr_name}")
            else:
                self.__dict__[attr_name] = getattr(super(), attr_name)
            getattr(self, attr_name)(key, value)

        attributes[attr_name] = wrapper


class Moo(metaclass=UdderType):

    def copy(self) -> Self:
        blank = super().__new__()
        if not hasattr(self, "_heffer"):
            blank._heffer = self
        else:
            blank._heffer = self._heffer
