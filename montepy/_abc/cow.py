# Copyright 2025, Battelle Energy Alliance, LLC All Rights Reserved.
import copy
from typing import Self

"""
Moooooooo
"""


class Moo:

    def copy(self) -> Self:
        Self = type(self)
        blank = Self.__new__(Self)
        if not hasattr(self, "_heffer"):
            blank._heffer = self
        else:
            blank._heffer = self._heffer
        # blank._make_cow()
        return blank

    def _make_cow(self):
        self.prepare_getter("__getattr__")
        # self.prepare_setter("__setattr__")
        if hasattr(self, "__getitem__"):
            self.prepare_getter("__getitem__")
            # self.prepare_setter("__setitem__")

    def __getattr__(self, key):
        if "__" in key or key == "_heffer":
            return super().__getattribute__(key)
        if hasattr(self, "_heffer") and self._heffer is not None:
            return getattr(self._heffer, key)
        else:
            return super().__getattribute__(key)

    def prepare_setter(self, attr_name):
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
