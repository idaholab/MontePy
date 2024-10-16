# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from abc import ABC, abstractmethod
import typing
import weakref

import montepy
from montepy.numbered_mcnp_object import Numbered_MCNP_Object
from montepy.errors import *
from montepy.utilities import *


def _enforce_positive(self, num):
    if num <= 0:
        raise ValueError(f"Value must be greater than 0. {num} given.")


class NumberedObjectCollection(ABC):
    """A collections of MCNP objects.

    It quacks like a dict, it acts like a dict, but it's a list.

    The items in the collection are accessible by their number.
    For instance to get the Cell with a number of 2 you can just say:

    ``problem.cells[2]``

    You can also add delete items like you would in a dictionary normally.

    Unlike dictionaries this collection also supports slices e.g., ``[1:3]``.
    This will return a new :class:`NumberedObjectCollection` with objects
    that have cell numbers that fit that slice. If a number is in a slice that
    is not an actual object it will just be skipped.

    Because MCNP numbered objects start at 1, so do the indices.
    The slices are effectively 1-based and endpoint-inclusive.
    This means rather than the normal behavior of [0:5] excluding the index
    5, 5 would be included.

    :param obj_class: the class of numbered objects being collected
    :type obj_class: type
    :param objects: the list of cells to start with if needed
    :type objects: list
    :param problem: the problem to link this collection to.
    :type problem: MCNP_Problem
    """

    def __init__(self, obj_class, objects=None, problem=None):
        self.__num_cache = {}
        assert issubclass(obj_class, Numbered_MCNP_Object)
        self._obj_class = obj_class
        self._objects = []
        self._start_num = 1
        self._step = 1
        self._problem_ref = None
        if problem is not None:
            self._problem_ref = weakref.ref(problem)
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

    def link_to_problem(self, problem):
        """Links the card to the parent problem for this card.

        This is done so that cards can find links to other objects.

        :param problem: The problem to link this card to.
        :type problem: MCNP_Problem
        """
        if not isinstance(problem, (montepy.mcnp_problem.MCNP_Problem, type(None))):
            raise TypeError("problem must be an MCNP_Problem")
        if problem is None:
            self._problem_ref = None
        else:
            self._problem_ref = weakref.ref(problem)
        for obj in self:
            obj.link_to_problem(problem)

    @property
    def _problem(self):
        if self._problem_ref is not None:
            return self._problem_ref()
        return None

    def __getstate__(self):
        state = self.__dict__.copy()
        weakref_key = "_problem_ref"
        if weakref_key in state:
            del state[weakref_key]
        return state

    def __setstate__(self, crunchy_data):
        crunchy_data["_problem_ref"] = None
        self.__dict__.update(crunchy_data)

    @property
    def numbers(self):
        """
        A generator of the numbers being used.

        :rtype: generator
        """
        for obj in self._objects:
            # update cache every time we go through all objects
            self.__num_cache[obj.number] = obj
            yield obj.number

    def check_number(self, number):
        """Checks if the number is already in use, and if so raises an error.

        :param number: The number to check.
        :type number: int
        :raises NumberConflictError: if this number is in use.
        """
        if not isinstance(number, int):
            raise TypeError("The number must be an int")
        conflict = False
        # only can trust cache if being
        if self._problem:
            if number in self.__num_cache:
                conflict = True
        else:
            if number in self.numbers:
                conflict = True
        if conflict:
            raise NumberConflictError(
                f"Number {number} is already in use for the collection: {type(self)} by {self[number]}"
            )

    def _update_number(self, old_num, new_num, obj):
        """
        Updates the number associated with a specific object in the internal cache.

        :param old_num: the previous number the object had.
        :type old_num: int
        :param new_num: the number that is being set to.
        :type new_num: int
        :param obj: the object being updated.
        :type obj: self._obj_class
        """
        # don't update numbers you don't own
        if self.__num_cache.get(old_num, None) is not obj:
            return
        self.__num_cache.pop(old_num, None)
        self.__num_cache[new_num] = obj

    @property
    def objects(self):
        """
        Returns a shallow copy of the internal objects list.

        The list object is a new instance, but the underlying objects
        are the same.

        :rtype: list
        """
        return self._objects[:]

    def pop(self, pos=-1):
        """
        Pop the final items off of the collection

        :param pos: The index of the element to pop from the internal list.
        :type pos: int
        :return: the final elements
        :rtype: Numbered_MCNP_Object
        """
        if not isinstance(pos, int):
            raise TypeError("The index for popping must be an int")
        obj = self._objects.pop(pos)
        self.__num_cache.pop(obj.number, None)
        return obj

    def clear(self):
        """
        Removes all objects from this collection.
        """
        self._objects.clear()
        self.__num_cache.clear()

    def extend(self, other_list):
        """
        Extends this collection with another list.

        :param other_list: the list of objects to add.
        :type other_list: list
        :raises NumberConflictError: if these items conflict with existing elements.
        """
        if not isinstance(other_list, (list, type(self))):
            raise TypeError("The extending list must be a list")
        if self._problem:
            nums = set(self.__num_cache)
        else:
            nums = set(self.numbers)
        for obj in other_list:
            if not isinstance(obj, self._obj_class):
                raise TypeError(
                    "The object in the list {obj} is not of type: {self._obj_class}"
                )
            if obj.number in nums:
                raise NumberConflictError(
                    (
                        f"When adding to {type(self)} there was a number collision due to "
                        f"adding {obj} which conflicts with {self[obj.number]}"
                    )
                )
            nums.add(obj.number)
        self._objects.extend(other_list)
        self.__num_cache.update({obj.number: obj for obj in other_list})
        if self._problem:
            for obj in other_list:
                obj.link_to_problem(self._problem)

    def remove(self, delete):
        """
        Removes the given object from the collection.

        :param delete: the object to delete
        :type delete: Numbered_MCNP_Object
        """
        self.__num_cache.pop(delete.number, None)
        self._objects.remove(delete)

    def clone(self, starting_number=None, step=None):
        """
        Create a new instance of this collection, with all new independent
        objects with new numbers.

        This relies mostly on ``copy.deepcopy``.

        .. note ::
            If starting_number, or step are not specified :func:`starting_number`,
            and :func:`step` are used as default values.

        .. versionadded:: 0.5.0

        :param starting_number: The starting number to request for a new object numbers.
        :type starting_number: int
        :param step: the step size to use to find a new valid number.
        :type step: int
        :returns: a cloned copy of this object.
        :rtype: type(self)

        """
        if not isinstance(starting_number, (int, type(None))):
            raise TypeError(
                f"Starting_number must be an int. {type(starting_number)} given."
            )
        if not isinstance(step, (int, type(None))):
            raise TypeError(f"step must be an int. {type(step)} given.")
        if starting_number is not None and starting_number <= 0:
            raise ValueError(f"starting_number must be >= 1. {starting_number} given.")
        if step is not None and step <= 0:
            raise ValueError(f"step must be >= 1. {step} given.")
        if starting_number is None:
            starting_number = self.starting_number
        if step is None:
            step = self.step
        objs = []
        for obj in self:
            new_obj = obj.clone(starting_number, step)
            starting_number = new_obj.number
            objs.append(new_obj)
            starting_number = new_obj.number + step
        return type(self)(objs)

    @make_prop_pointer("_start_num", int, validator=_enforce_positive)
    def starting_number(self):
        """
        The starting number to use when an object is cloned.

        :returns: the starting number
        :rtype: int
        """
        pass

    @make_prop_pointer("_step", int, validator=_enforce_positive)
    def step(self):
        """
        The step size to use to find a valid number during cloning.

        :returns: the step size
        :rtype: int
        """
        pass

    def __iter__(self):
        self._iter = self._objects.__iter__()
        return self._iter

    def __str__(self):
        base_class_name = self.__class__.__name__
        numbers = list(self.numbers)
        return f"{base_class_name}: {numbers}"

    def __repr__(self):
        return (
            f"Numbered_object_collection: obj_class: {self._obj_class}, problem: {self._problem}\n"
            f"Objects: {self._objects}\n"
            f"Number cache: {self.__num_cache}"
        )

    def append(self, obj):
        """Appends the given object to the end of this collection.

        :param obj: the object to add.
        :type obj: Numbered_MCNP_Object
        :raises NumberConflictError: if this object has a number that is already in use.
        """
        if not isinstance(obj, self._obj_class):
            raise TypeError(f"object being appended must be of type: {self._obj_class}")
        self.check_number(obj.number)
        self.__num_cache[obj.number] = obj
        self._objects.append(obj)
        if self._problem:
            obj.link_to_problem(self._problem)

    def append_renumber(self, obj, step=1):
        """Appends the object, but will renumber the object if collision occurs.

        This behaves like append, except if there is a number collision the object will
        be renumbered to an available number. The number will be incremented by step
        until an available number is found.

        :param obj: The MCNP object being added to the collection.
        :type obj: Numbered_MCNP_Object
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
        if self._problem:
            obj.link_to_problem(self._problem)
        try:
            self.append(obj)
        except NumberConflictError:
            number = self.request_number(number, step)
            obj.number = number
            self.append(obj)

        return number

    def request_number(self, start_num=None, step=None):
        """Requests a new available number.

        This method does not "reserve" this number. Objects
        should be immediately added to avoid possible collisions
        caused by shifting numbers of other objects in the collection.

        .. note ::
            If starting_number, or step are not specified :func:`starting_number`,
            and :func:`step` are used as default values.

        .. versionchanged:: 0.5.0
            In 0.5.0 the default values were changed to reference :func:`starting_number` and :func:`step`.

        :param start_num: the starting number to check.
        :type start_num: int
        :param step: the increment to jump by to find new numbers.
        :type step: int
        :returns: an available number
        :rtype: int
        """
        if not isinstance(start_num, (int, type(None))):
            raise TypeError("start_num must be an int")
        if not isinstance(step, (int, type(None))):
            raise TypeError("step must be an int")
        if start_num is None:
            start_num = self.starting_number
        if step is None:
            step = self.step
        number = start_num
        while True:
            try:
                self.check_number(number)
                break
            except NumberConflictError:
                number += step
        return number

    def next_number(self, step=1):
        """Get the next available number, based on the maximum number.

        This works by finding the current maximum number, and then adding the
        stepsize to it.

        :param step: how much to increase the last number by
        :type step: int
        """
        if not isinstance(step, int):
            raise TypeError("step must be an int")
        if step <= 0:
            raise ValueError("step must be > 0")
        return max(self.numbers) + step

    def __get_slice(self, i: slice):
        """Get a new NumberedObjectCollection over a slice of numbers

        This method implements usage like:
            >>> NumberedObjectCollection[1:49:12]
            [1, 13, 25, 37, 49]

        Any ``slice`` object may be passed.
        The indices are the object numbers.
        Because MCNP numbered objects start at 1, so do the indices.
        They are effectively 1-based and endpoint-inclusive.

        :rtype: NumberedObjectCollection
        """
        rstep = i.step if i.step is not None else 1
        rstart = i.start
        rstop = i.stop
        if rstep < 0:  # Backwards
            if rstart is None:
                rstart = max(self.numbers)
            if rstop is None:
                rstop = min(self.numbers)
            rstop -= 1
        else:  # Forwards
            if rstart is None:
                rstart = 0
            if rstop is None:
                rstop = max(self.numbers)
            rstop += 1
        numbered_objects = []
        for num in range(rstart, rstop, rstep):
            obj = self.get(num)
            if obj is not None:
                numbered_objects.append(obj)
        # obj_class is always implemented in child classes.
        return type(self)(numbered_objects)

    def __getitem__(self, i):
        if isinstance(i, slice):
            return self.__get_slice(i)
        elif not isinstance(i, int):
            raise TypeError("index must be an int or slice")
        ret = self.get(i)
        if ret is None:
            raise KeyError(f"Object with number {i} not found in {type(self)}")
        return ret

    def __delitem__(self, idx):
        if not isinstance(idx, int):
            raise TypeError("index must be an int")
        obj = self[idx]
        self.__num_cache.pop(obj.number, None)
        self._objects.remove(obj)

    def __setitem__(self, key, newvalue):
        if not isinstance(key, int):
            raise TypeError("index must be an int")
        self.append(newvalue)

    def __len__(self):
        return len(self._objects)

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __contains__(self, other):
        return other in self._objects

    def get(self, i: int, default=None) -> (Numbered_MCNP_Object, None):
        """
        Get ``i`` if possible, or else return ``default``.

        :param i: number of the object to get, not it's location in the internal list
        :type i: int
        :param default: value to return if not found
        :type default: object

        :rtype: Numbered_MCNP_Object
        """
        try:
            ret = self.__num_cache[i]
            if ret.number == i:
                return ret
        except KeyError:
            pass
        for obj in self._objects:
            if obj.number == i:
                self.__num_cache[i] = obj
                return obj
        return default

    def keys(self) -> typing.Generator[int, None, None]:
        """
        Get iterator of the collection's numbers.

        :rtype: int
        """
        for o in self._objects:
            yield o.number

    def values(self) -> typing.Generator[Numbered_MCNP_Object, None, None]:
        """
        Get iterator of the collection's objects.

        :rtype: Numbered_MCNP_Object
        """
        for o in self._objects:
            yield o

    def items(
        self,
    ) -> typing.Generator[typing.Tuple[int, Numbered_MCNP_Object], None, None]:
        """
        Get iterator of the collections (number, object) pairs.

        :rtype: tuple(int, MCNP_Object)
        """
        for o in self._objects:
            yield o.number, o


class NumberedDataObjectCollection(NumberedObjectCollection):
    def __init__(self, obj_class, objects=None, problem=None):
        self._last_index = None
        if problem and objects:
            try:
                self._last_index = problem.data_inputs.index(objects[-1])
            except ValueError:
                pass
        super().__init__(obj_class, objects, problem)

    def append(self, obj, insert_in_data=True):
        """Appends the given object to the end of this collection.

        :param obj: the object to add.
        :type obj: Numbered_MCNP_Object
        :param insert_in_data: Whether to add the object to the linked problem's data_inputs.
        :type insert_in_data: bool
        :raises NumberConflictError: if this object has a number that is already in use.
        """
        super().append(obj)
        if self._problem:
            if self._last_index:
                index = self._last_index
            elif len(self) > 0:
                try:
                    index = self._problem.data_inputs.index(self._objects[-1])
                except ValueError:
                    index = len(self._problem.data_inputs)
            else:
                index = len(self._problem.data_inputs)
            if insert_in_data:
                self._problem.data_inputs.insert(index + 1, obj)
            self._last_index = index + 1

    def __delitem__(self, idx):
        if not isinstance(idx, int):
            raise TypeError("index must be an int")
        obj = self[idx]
        super().__delitem__(idx)
        if self._problem:
            self._problem.data_inputs.remove(obj)

    def remove(self, delete):
        """
        Removes the given object from the collection.

        :param delete: the object to delete
        :type delete: Numbered_MCNP_Object
        """
        super().remove(delete)
        if self._problem:
            self._problem.data_inputs.remove(delete)

    def pop(self, pos=-1):
        """
        Pop the final items off of the collection

        :param pos: The index of the element to pop from the internal list.
        :type pos: int
        :return: the final elements
        :rtype: Numbered_MCNP_Object
        """
        if not isinstance(pos, int):
            raise TypeError("The index for popping must be an int")
        obj = self._objects.pop(pos)
        super().pop(pos)
        if self._problem:
            self._problem.data_inputs.remove(obj)
        return obj

    def clear(self):
        """
        Removes all objects from this collection.
        """
        if self._problem:
            for obj in self._objects:
                self._problem.data_inputs.remove(obj)
        self._last_index = None
        super().clear()
