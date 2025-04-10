# Copyright 2025, Battelle Energy Alliance, LLC All Rights Reserved.
import copy
from typing import Self

"""
Moooooooo
"""


class UdderType(type):

    def __new__(meta, clsname, bases, attributes):
        print(attributes)
        return super().__new__(meta, clsname, bases, attributes)

    @staticmethod
    def __getitem__(self, key):
        if hasattr(self, "_heffer"):
            return self._heffer.__getitem__(key)
        else:
            return super().__getitem__(key)


class Moo:

    def copy(self) -> Self:
        Self = type(self)
        blank = Self.__new__(Self)
        if not hasattr(self, "_heffer"):
            blank._heffer = self
        else:
            blank._heffer = self._heffer
        return blank

    def __getattr__(self, key):
        if "__" in key or key == "_heffer":
            return super().__getattribute__(key)
        if hasattr(self, "_heffer") and self._heffer is not None:
            return getattr(self._heffer, key)
        else:
            return super().__getattribute__(key)

    def __setattr__(self, key, value):
        if key.startswith("_"):
            super().__setattr__(key, value)
        # TODO cowDict
        # if isinstance(self, dict):
        #    MalformedInputError
        if hasattr(self, "_heffer") and self._heffer is not None:
            self.__dict__.update(copy.deepcopy(self._heffer.__dict__))
            del self._heffer
        super().__setattr__(key, value)

    # TODO delattr
