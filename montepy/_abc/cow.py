# Copyright 2025, Battelle Energy Alliance, LLC All Rights Reserved.
import copy
from typing import Self

"""
Moooooooo
"""


class Moo:
    def copy_cow(self) -> Self:
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
            return
        if hasattr(self, "_heffer") and self._heffer is not None:
            self.__dict__.update(copy.deepcopy(self._heffer.__dict__))
            del self._heffer
        super().__setattr__(key, value)

    def __delattr__(self, key):
        if key.startswith("_"):
            super().__delattr__(key)
            return
        if hasattr(self, "_heffer") and self._heffer is not None:
            self.__dict__.update(copy.deepcopy(self._heffer.__dict__))
            del self._heffer
        super().__delattr__(key)


class LibraryOfCowgress(dict, Moo):

    def __getitem__(self, key):
        if hasattr(self, "_heffer") and self._heffer is not None:
            return self._heffer[key]
        else:
            return super().__getitem__(key)

    def __setitem__(self, key, value):
        if hasattr(self, "_heffer") and self._heffer is not None:
            for key, value in self._heffer.items():
                super().__setitem__(key, value)
            del self._heffer
        super().__setitem__(key, value)

    def __delitem__(self, key):
        if hasattr(self, "_heffer") and self._heffer is not None:
            for key, value in self._heffer.items():
                super().__setitem__(key, value)
            del self._heffer
        super().__delitem__(key)
