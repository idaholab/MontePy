from abc import ABC, abstractmethod
from mcnpy.errors import *


class NumberedObjectCollection(ABC):
    """A collections of cells."""

    def __init__(self, obj_class, objects=None):
        """
        :param cells: the list of cells to start with if needed
        :type cells: list
        """
        self.__num_cache = {}
        self._obj_class = obj_class
        if objects:
            assert isinstance(objects, list)
            for obj in objects:
                assert isinstance(obj, obj_class)
                self.__num_cache[obj.number] = obj
            self._objects = objects
        else:
            self._objects = []

    @property
    def numbers(self):
        """
        A generator of the numbers being used.
        """
        for obj in self._objects:
            yield obj.number

    def check_redundant_numbers(self):
        """
        Checks if there are any redundant  numbers.
        :returns: true if there are collisions of numbers
        :rtype: bool
        """
        return len(self._objects) != len(set(self.numbers))

    @property
    def objects(self):
        """
        Returns a shallow copy of the internal objects list.

        The list object is a new instance, but the underlying objects
        are the same.
        """
        return self._objects[:]

    def pop(self, pos=1):
        """
        Pop the final items off of the collection

        :param pos: The distance from the end of the list to remove.
        :type pos: int
        :return: the final element(s_
        """
        assert isinstance(pos, int)
        assert pos > 0
        obj = self._objects.pop(pos)
        self.__num_cache.pop(obj.number, None)
        return obj

    def extend(self, other_list):
        assert isinstance(other_list, list)
        for obj in other_list:
            assert isinstance(obj, self._obj_class)
            if obj.number in self.__num_cache:
                if obj.number in self.numbers:
                    raise NumberConflictError(
                        (
                            f"When adding to {type(self)} there was a number collision due to "
                            f"adding {obj} which conflicts with {self[obj.number]}"
                        )
                    )
                # if this number is a ghost; remove it.
                else:
                    self.__num_cache.pop(obj.number, None)
        self._objects.extend(other_list)

    def remove(self, delete):
        self.__num_cache.pop(delete.number, None)
        self._objects.remove(delete)

    def __iter__(self):
        self._iter = self._objects.__iter__()
        return self._iter

    def __next__(self):
        return self._iter.__next__()

    def append(self, obj):
        assert isinstance(obj, self._obj_class)
        if obj.number in self.__num_cache and obj.number in self.numbers:
            raise NumberConflictError(
                (
                    "There was a numbering conflict when attempting to add "
                    f"{obj} to {type(self)}. Conflict was with {self[obj.number]}"
                )
            )
        else:
            self.__num_cache[obj.number] = obj
        self._objects.append(obj)

    def __getitem__(self, i):
        assert isinstance(i, int)
        find_manually = False
        try:
            ret = self.__num_cache[i]
            if ret.number != i:
                ret = None
                find_manually = True
        except KeyError:
            find_manually = True
        if find_manually:
            ret = None
            for obj in self._objects:
                if obj.number == i:
                    ret = obj
                    self.__num_cache[i] = obj
                    break
            if ret is None:
                raise KeyError(f"Object with number {i} not found in {type(self)}")
        return ret

    def __delitem__(self, idx):
        assert isinstance(idx, int)
        obj = self[idx]
        self.__num_cache.pop(obj.number, None)
        idx = self._objects[obj]
        del self._objects[idx]

    def __setitem__(self, key, newvalue):
        assert isinstance(key, int)
        self.append(newvalue)

    def __len__(self):
        return len(self._objects)

    def __iadd__(self, other):
        assert isinstance(other, (type(self), list))
        for obj in other:
            assert isinstance(cell, self._obj_class)
        if isinstance(other, type(self)):
            other_list = other.objects
        else:
            other_list = other
        for obj in other_list:
            if obj.number in self.__num_cache and obj.number in self.numbers:
                raise NumberConflictError(
                    (
                        "There was a numbering conflict when attempting to add "
                        f"{obj} to {type(self)}. Conflict was with {self[obj.number]}"
                    )
                )
            else:
                self.__num_cache[obj.number] = obj
        self.objects += other_list
        return self

    def __contains__(self, element):
        return any(x is element for x in self._objects)
