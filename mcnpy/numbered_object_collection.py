from abc import ABC, abstractmethod
import typing
from mcnpy.mcnp_card import MCNP_Card
from mcnpy.errors import *


class NumberedObjectCollection(ABC):
    """A collections of MCNP objects.

    It quicks like a dict, it acts like a dict, but is a list.
    """

    def __init__(self, obj_class, objects=None):
        """
        :param obj_class: the class of numbered objects being collected
        :type obj_class: type
        :param objects: the list of cells to start with if needed
        :type objects: list
        """
        self.__num_cache = {}
        self._obj_class = obj_class
        if objects:
            if not isinstance(objects, list):
                raise TypeError("NumberedObjectCollection must be built from a list")
            for obj in objects:
                if not isinstance(obj, obj_class):
                    raise TypeError(
                        f"The object: {obj} being added to a NumberedObjectCollection is not of type {obj_class}"
                    )
                if obj.number in self.__num_cache:
                    raise NumberConflictError(
                        (
                            f"When building {self} there was a numbering conflict between: "
                            f"{obj} and {self[obj.number]}"
                        )
                    )
                self.__num_cache[obj.number] = obj
            self._objects = objects
        else:
            self._objects = []

    @property
    def numbers(self):
        """
        A generator of the numbers being used.
        """
        self.__num_cache
        for obj in self._objects:
            # update cache every time we go through all objects
            self.__num_cache[obj.number] = obj
            yield obj.number

    def check_number(self, number):
        """Checks if the number is already in use, and if so raises an error.

        :param number: The number to check.
        :type number: int
        :raises: NumberConflictError : if this number is in use.
        """
        if not isinstance(number, int):
            raise TypeError("The number must be an int")
        if number in self.numbers:
            raise NumberConflictError(
                f"Number {number} is already in use for the collection: {type(self)} by {self[number]}"
            )

    @property
    def objects(self):
        """
        Returns a shallow copy of the internal objects list.

        The list object is a new instance, but the underlying objects
        are the same.
        """
        return self._objects[:]

    def pop(self, pos=-1):
        """
        Pop the final items off of the collection

        :param pos: The index of the element to pop from the internal list.
        :type pos: int
        :return: the final elements
        """
        if not isinstance(pos, int):
            raise TypeError("The index for popping must be an int")
        obj = self._objects.pop(pos)
        self.__num_cache.pop(obj.number, None)
        return obj

    def extend(self, other_list):
        """
        Extends this collection with another list.

        :param other_list: the list of objects to add.
        :type other_list: list
        :raises: NumberConflictError if these items conflict with existing elements.
        """
        if not isinstance(other_list, list):
            raise TypeError("The extending list must be a list")
        for obj in other_list:
            if not isinstance(obj, self._obj_class):
                raise TypeError(
                    "The object in the list {obj} is not of type: {self._obj_class}"
                )
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
        """Appends the given object to the end of this collection.

        :param obj: the object to add.
        :type obj: MCNP_Card
        :raises: NumberConflictError: if this object has a number that is already in use.
        """
        if not isinstance(obj, self._obj_class):
            raise TypeError(f"object being appended must be of type: {self._obj_class}")
        if obj.number in self.numbers:
            raise NumberConflictError(
                (
                    "There was a numbering conflict when attempting to add "
                    f"{obj} to {type(self)}. Conflict was with {self[obj.number]}"
                )
            )
        else:
            self.__num_cache[obj.number] = obj
        self._objects.append(obj)

    def append_renumber(self, obj, step=1):
        """Appends the object, but will renumber the object if collision occurs.

        This behaves like append, except if there is a number collision the object will
        be renumbered to an available number. The number will be incremented by step
        until an available number is found.

        :param obj: The MCNP object being added to the collection.
        :type obj: MCNP_Card
        :param step: the incrementing step to use to find a new number.
        :type step: int
        :return: the number for the object.
        :rtype: int
        """
        if not isinstance(obj, self._obj_class):
            raise TypeError(f"object being appended must be of type: {self._obj_class}")
        if not isinstance(step, int):
            raise TypeError("The step number must be an int")
        number = obj.number
        try:
            self.append(obj)
        except NumberConflictError:
            number = self.request_number(number, step)
            obj.number = number
            self.append(obj)

        return number

    def request_number(self, start_num=1, step=1):
        """Requests a new available number.

        This method does not "reserve" this number. Objects
        should be immediately added to avoid possible collisions
        caused by shifting numbers of other objects in the collection.

        :param start_num: the starting number to check.
        :type start_num: int
        :param step: the increment to jump by to find new numbers.
        :type step: int
        :returns: an available number
        :rtype: int
        """
        if not isinstance(start_num, int):
            raise TypeError("start_num must be an int")
        if not isinstance(step, int):
            raise TypeError("step must be an int")
        number = start_num
        while number in self.numbers:
            number += step
        return number

    def next_number(self, step=1):
        """Get the next available number, based on the maximum number.

        This works by finding the current maximum number, and then adding the
        stepsize to it.
        """
        if not isinstance(step, int):
            raise TypeError("step must be an int")
        if step <= 0:
            raise ValueError("step must be > 0")
        return max(self.numbers) + step

    def __getitem__(self, i):
        if not isinstance(i, int):
            raise TypeError("index must be an int")
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
        if not isinstance(idx, int):
            raise TypeError("index must be an int")
        obj = self[idx]
        self.__num_cache.pop(obj.number, None)
        idx = self._objects.index(obj)
        del self._objects[idx]

    def __setitem__(self, key, newvalue):
        if not isinstance(key, int):
            raise TypeError("index must be an int")
        self.append(newvalue)

    def __len__(self):
        return len(self._objects)

    def __iadd__(self, other):
        if not isinstance(other, (type(self), list)):
            raise TypeError(f"Appended item must be a list or of type {type(self)}")
        for obj in other:
            if not isinstance(obj, self._obj_class):
                raise TypeError(
                    f"Appended object {obj} must be of type: {self._obj_class}"
                )
        if isinstance(other, type(self)):
            other_list = other.objects
        else:
            other_list = other
        for obj in other_list:
            if obj.number in self.numbers:
                raise NumberConflictError(
                    (
                        "There was a numbering conflict when attempting to add "
                        f"{obj} to {type(self)}. Conflict was with {self[obj.number]}"
                    )
                )
            else:
                self.__num_cache[obj.number] = obj
        self._objects += other_list
        return self

    def __contains__(self, other):
        return other in self._objects

    def keys(self) -> typing.Generator[int, None, None]:
        """
        Get iterator of the collection's numbers.

        :rtype: int
        """
        for o in self._objects:
            yield o.number

    def values(self) -> typing.Generator[MCNP_Card, None, None]:
        """
        Get iterator of the collection's objects.

        :rtype: MCNP_Card
        """
        for o in self._objects:
            yield o

    def items(self) -> typing.Generator[typing.Tuple[int, MCNP_Card], None, None]:
        """
        Get iterator of the collections (number, object) pairs.

        :rtype: tuple(int, MCNP_Card)
        """
        for o in self._objects:
            yield o.number, o
