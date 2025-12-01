# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
from abc import ABC
import itertools as it
import typing
import weakref

import montepy
from montepy.utilities import *
from montepy.numbered_mcnp_object import Numbered_MCNP_Object
from montepy.exceptions import *
from montepy.utilities import *
import montepy.types as ty


class NumberedObjectCollection(ABC):
    """A collections of MCNP objects.


    .. _collect ex:

    Examples
    ________

    Accessing Objects
    ^^^^^^^^^^^^^^^^^

    It quacks like a dict, it acts like a dict, but it's a list.

    The items in the collection are accessible by their number.
    For instance to get the Cell with a number of 2 you can just say:

    .. doctest:: python

        >>> import montepy
        >>> problem = montepy.read_input("tests/inputs/test.imcnp")
        >>> cell = problem.cells[2]
        >>> print(cell)
        CELL: 2, mat: 2, DENS: 8.0 atom/b-cm

    You can also add, and delete items like you would in a dictionary normally.
    Though :func:`append` and :func:`add` are the preferred way of adding items.
    When adding items by key the key given is actually ignored.

    .. testcode::

        import montepy
        problem = montepy.read_input("tests/inputs/test.imcnp")
        cell = montepy.Cell()
        cell.number = 25
        # this will actually append ignoring the key given
        problem.cells[3] = cell
        print(problem.cells[3] is cell)
        del problem.cells[25]
        print(cell not in problem.cells)

    This shows:

    .. testoutput::

        False
        True

    Slicing a Collection
    ^^^^^^^^^^^^^^^^^^^^

    Unlike dictionaries this collection also supports slices e.g., ``[1:3]``.
    This will return a new :class:`NumberedObjectCollection` with objects
    that have numbers that fit that slice.

    .. testcode::

        for cell in problem.cells[1:3]:
            print(cell.number)

    Which shows

    .. testoutput::

        1
        2
        3

    Because MCNP numbered objects start at 1, so do the indices.
    The slices are effectively 1-based and endpoint-inclusive.
    This means rather than the normal behavior of [0:5] excluding the index
    5, 5 would be included.

    Set-Like Operations
    ^^^^^^^^^^^^^^^^^^^

    .. versionchanged:: 1.0.0

         Introduced set-like behavior.

    These collections act like `sets <https://docs.python.org/3/library/stdtypes.html#set>`_.
    The supported operators are: ``&``, ``|``, ``-``, ``^``, ``<``, ``<=``, ``>``, ``>=``, ``==``.
    See the set documentation for how these operators function.
    The set operations are applied to the object numbers.
    The corresponding objects are then taken to form a new instance of this collection.
    The if both collections have objects with the same number but different objects,
    the left-hand-side's object is taken.

    .. testcode::

        cells1 = montepy.Cells()

        for i in range(5, 10):
            cell = montepy.Cell()
            cell.number = i
            cells1.add(cell)

        cells2 = montepy.Cells()

        for i in range(8, 15):
            cell = montepy.Cell()
            cell.number = i
            cells2.add(cell)

        overlap = cells1 & cells2

        # The only overlapping numbers are 8, 9, 10

        print({8, 9} == set(overlap.keys()))

    This would print:

    .. testoutput::

        True

    Other set-like functions are: :func:`difference`, :func:`difference_update`,
    :func:`intersection`, :func:`isdisjoint`, :func:`issubset`, :func:`issuperset`,
    :func:`symmetric_difference`, :func:`symmetric_difference_update`, :func:`union`, :func:`discard`, and :func:`update`.

    Parameters
    ----------
    obj_class : type
        the class of numbered objects being collected
    objects : list
        the list of cells to start with if needed
    problem : MCNP_Problem
        the problem to link this collection to.
    """

    @args_checked
    def __init__(
        self,
        obj_class: type,
        objects: ty.Iterable[montepy.numbered_mcnp_object.Numbered_MCNP_Object] = None,
        problem: montepy.MCNP_Problem = None,
    ):
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
            for obj in objects:
                if obj.number in self.__num_cache:
                    raise NumberConflictError(
                        (
                            f"When building {self} there was a numbering conflict between: "
                            f"{obj} and {self[obj.number]}"
                        )
                    )
                self.__num_cache[obj.number] = obj
            self._objects = objects

    @args_checked
    def link_to_problem(self, problem: montepy.MCNP_Problem = None):
        """Links the card to the parent problem for this card.

        This is done so that cards can find links to other objects.

        Parameters
        ----------
        problem : MCNP_Problem
            The problem to link this card to.
        """
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
        """A generator of the numbers being used.

        Returns
        -------
        generator
        """
        for obj in self._objects:
            # update cache every time we go through all objects
            self.__num_cache[obj.number] = obj
            yield obj.number

    @args_checked
    def check_number(self, number: ty.NonNegativeInt):
        """Checks if the number is already in use, and if so raises an error.

        Parameters
        ----------
        number : int
            The number to check.

        Raises
        ------
        NumberConflictError
            if this number is in use.
        """
        conflict = False
        # only can trust cache if being updated
        if self._problem:
            if number in self.__num_cache:
                conflict = True
        else:
            if number in self.numbers:
                conflict = True
        if conflict:
            raise NumberConflictError(
                f"Number {number} is already in use for the collection: {type(self).__name__} by {self[number]}"
            )

    def search_parent_objs_by_child(self, child, parent_prop, prop_container=False):
        """ """
        search_str = str(child.number)
        for obj in self:
            # possible candidate without full parsing
            # treat no input as a negative find since it will already be parsed
            if obj.search(search_str):
                # trigger full parse
                if isinstance(parent_prop, tuple):
                    parent_obj = obj
                    for prop in parent_prop:
                        # go through multiple levels of getattr
                        parent_obj = getattr(parent_obj, prop)
                else:
                    parent_obj = getattr(obj, parent_prop)
                if prop_container:
                    if child in parent_obj:
                        # already parsed and linked by this point, nothing further to do.
                        pass
                else:
                    if child is parent_obj:
                        pass

    def _get_leading_comment(self, obj):
        """
        TODO
        """
        try:
            assert obj in self
        except AssertionError:
            raise KeyError(
                f"obj: {obj} is not in this collection: {type(self).__name__}"
            )
        idx = self._objects.index(obj)
        if idx <= 0:
            return None
        comment = self._objects[idx - 1].trailing_comment
        self._objects[idx - 1]._delete_trailing_comment()
        return comment

    def _update_number(self, old_num, new_num, obj):
        """Updates the number associated with a specific object in the internal cache.

        Parameters
        ----------
        old_num : int
            the previous number the object had.
        new_num : int
            the number that is being set to.
        obj : self._obj_class
            the object being updated.
        """
        # don't update numbers you don't own
        if self.__num_cache.get(old_num, None) is not obj:
            return
        self.__num_cache.pop(old_num, None)
        self.__num_cache[new_num] = obj

    @property
    def objects(self):
        """Returns a shallow copy of the internal objects list.

        The list object is a new instance, but the underlying objects
        are the same.

        Returns
        -------
        list
        """
        return self._objects[:]

    @args_checked
    def pop(self, pos: ty.Integral = -1):
        """Pop the final items off of the collection

        Parameters
        ----------
        pos : int
            The index of the element to pop from the internal list.

        Returns
        -------
        Numbered_MCNP_Object
            the final elements
        """
        obj = self._objects[pos]
        self.__internal_delete(obj)
        return obj

    def clear(self):
        """Removes all objects from this collection."""
        self._objects.clear()
        self.__num_cache.clear()

    @args_checked
    def extend(
        self, other_list: ty.Iterable[montepy.numbered_mcnp_object.Numbered_MCNP_Object]
    ):
        """Extends this collection with another list.

        Parameters
        ----------
        other_list : list
            the list of objects to add.

        Raises
        ------
        NumberConflictError
            if these items conflict with existing elements.
        """
        # this is the optimized version to get all numbers
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
                        f"When adding to {type(self).__name__} there was a number collision due to "
                        f"adding {obj} which conflicts with {self[obj.number]}"
                    )
                )
            nums.add(obj.number)
        for obj in other_list:
            self.__internal_append(obj)

    def remove(self, delete: montepy.numbered_mcnp_object.Numbered_MCNP_Object):
        """Removes the given object from the collection.

        Parameters
        ----------
        delete : Numbered_MCNP_Object
            the object to delete
        """
        if not isinstance(delete, self._obj_class):
            raise TypeError(
                f"Expected {self._obj_class.__name__}. {delete} of type: {type(delete).__name__} given."
            )
        candidate = self[delete.number]
        if delete is candidate:
            del self[delete.number]
        else:
            raise KeyError(f"This object is not in this collection")

    @args_checked
    def clone(
        self, starting_number: ty.PositiveInt = None, step: ty.PositiveInt = None
    ):
        """Create a new instance of this collection, with all new independent
        objects with new numbers.

        This relies mostly on ``copy.deepcopy``.

        Notes
        -----
        If starting_number, or step are not specified :func:`starting_number`,
        and :func:`step` are used as default values.


        .. versionadded:: 0.5.0

        Parameters
        ----------
        starting_number : int
            The starting number to request for a new object numbers.
        step : int
            the step size to use to find a new valid number.

        Returns
        -------
        type(self)
            a cloned copy of this object.
        """
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

    @make_prop_pointer(
        "_start_num",
        ty.Integral,
        validator=lambda _, x: ty.positive("starting_number", "starting_number", x),
    )
    def starting_number(self):
        """The starting number to use when an object is cloned.

        Returns
        -------
        int
            the starting number
        """
        pass

    @make_prop_pointer(
        "_step", ty.Integral, validator=lambda _, x: ty.positive("step", "step", x)
    )
    def step(self):
        """The step size to use to find a valid number during cloning.

        Returns
        -------
        int
            the step size
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

    def _append_hook(self, obj, initial_load=False):
        """A hook that is called every time append is called."""
        if initial_load:
            return
        if self._problem and not hasattr(obj, "_not_parsed"):
            obj._add_children_objs(self._problem)

    def _delete_hook(self, obj, **kwargs):
        """A hook that is called every time delete is called."""
        pass

    def __internal_append(self, obj, **kwargs):
        """The internal append method.

        This should always be called rather than manually added.

        Parameters
        ----------
        obj
            the obj to append
        **kwargs
            keyword arguments passed through to the append_hook
        """
        if not isinstance(obj, self._obj_class):
            raise TypeError(
                f"Object must be of type: {self._obj_class.__name__}. {obj} given."
            )
        if obj.number < 0:
            raise ValueError(f"The number must be non-negative. {obj.number} given.")
        if obj.number in self.__num_cache:
            try:
                if obj is self[obj.number]:
                    return
            # if cache is bad and it's not actually in use ignore it
            except KeyError as e:
                pass
            else:
                raise NumberConflictError(
                    f"Number {obj.number} is already in use for the collection: {type(self).__name__} by {self[obj.number]}"
                )
        self.__num_cache[obj.number] = obj
        self._objects.append(obj)
        self._append_hook(obj, **kwargs)
        if self._problem:
            obj.link_to_problem(self._problem)

    def __internal_delete(self, obj, **kwargs):
        """The internal delete method.

        This should always be called rather than manually added.
        """
        self.__num_cache.pop(obj.number, None)
        self._objects.remove(obj)
        self._delete_hook(obj, **kwargs)

    def add(self, obj: Numbered_MCNP_Object):
        """Add the given object to this collection.

        Parameters
        ----------
        obj : Numbered_MCNP_Object
            The object to add.

        Raises
        ------
        TypeError
            if the object is of the wrong type.
        NumberConflictError
            if this object's number is already in use in the collection.
        """
        self.__internal_append(obj)

    def update(self, *objs: typing.Self):
        """Add the given objects to this collection.

        Notes
        -----

        This is not a thread-safe method.


        .. versionchanged:: 1.0.0

            Changed to be more set like. Accepts multiple arguments. If there is a number conflict,
            the current object will be kept.

        Parameters
        ----------
        *objs : list[Numbered_MCNP_Object]
            The objects to add.

        Raises
        ------
        TypeError
            if the object is of the wrong type.
        NumberConflictError
            if this object's number is already in use in the collection.
        """
        try:
            iter(objs)
        except TypeError:
            raise TypeError(f"Objs must be an iterable. {objs} given.")
        others = []
        for obj in objs:
            if isinstance(obj, list):
                others.append(type(self)(obj))
            else:
                others.append(obj)
        if len(others) == 1:
            self |= others[0]
        else:
            other = others[0].union(*others[1:])
            self |= others

    def append(self, obj, **kwargs):
        """Appends the given object to the end of this collection.

        Parameters
        ----------
        obj : Numbered_MCNP_Object
            the object to add.
        **kwargs
            extra arguments that are used internally.

        Raises
        ------
        NumberConflictError
            if this object has a number that is already in use.
        """
        if not isinstance(obj, self._obj_class):
            raise TypeError(f"object being appended must be of type: {self._obj_class}")
        self.__internal_append(obj, **kwargs)

    @args_checked
    def append_renumber(self, obj, step: ty.PositiveInt = 1):
        """Appends the object, but will renumber the object if collision occurs.

        This behaves like append, except if there is a number collision the object will
        be renumbered to an available number. The number will be incremented by step
        until an available number is found.

        Parameters
        ----------
        obj : Numbered_MCNP_Object
            The MCNP object being added to the collection.
        step : int
            the incrementing step to use to find a new number.

        Returns
        -------
        int
            the number for the object.
        """
        if not isinstance(obj, self._obj_class):
            raise TypeError(f"object being appended must be of type: {self._obj_class}")
        number = obj.number if obj.number > 0 else 1
        if self._problem:
            obj.link_to_problem(self._problem)
        try:
            self.append(obj)
        except (NumberConflictError, ValueError) as e:
            number = self.request_number(number, step)
            obj.number = number
            self.append(obj)

        return number

    @args_checked
    def request_number(
        self, start_num: ty.PositiveInt = None, step: ty.PositiveInt = None
    ):
        """Requests a new available number.

        This method does not "reserve" this number. Objects
        should be immediately added to avoid possible collisions
        caused by shifting numbers of other objects in the collection.

        Notes
        -----
        If starting_number, or step are not specified :func:`starting_number`,
        and :func:`step` are used as default values.

        .. versionchanged:: 0.5.0
            In 0.5.0 the default values were changed to reference :func:`starting_number` and :func:`step`.

        .. versionchanged:: 1.2.0
            start_num is now only a suggestion for the starting point. The returned number is not guaranteed to be start_num, but will be the next available number after start_num (or after the last assigned number).

        Parameters
        ----------
        start_num : int
            Suggested starting number to check. Not guaranteed to be the returned value.
        step : int
            the increment to jump by to find new numbers.

        Returns
        -------
        int
            an available number
        """
        if start_num is None:
            start_num = self.starting_number
        if step is None:
            step = self.step
        try:
            self.check_number(start_num)
            return start_num
        except NumberConflictError:
            pass
        # Increment to next available number. If not set use start_num as is
        last_assigned = getattr(self, "_last_assigned_number", start_num - step) + step
        number = max(start_num, last_assigned)
        while True:
            try:
                self.check_number(number)
                break
            except NumberConflictError:
                number += step
        self._last_assigned_number = number
        return number

    @args_checked
    def next_number(self, step: ty.PositiveInt = 1):
        """Get the next available number, based on the maximum number.

        This works by finding the current maximum number, and then adding the
        stepsize to it.

        Parameters
        ----------
        step : int
            how much to increase the last number by
        """
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

        Returns
        -------
        NumberedObjectCollection
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

    @args_checked
    def __getitem__(self, i: slice | ty.Integral):
        if isinstance(i, slice):
            return self.__get_slice(i)
        ret = self.get(i)
        if ret is None:
            raise KeyError(f"Object with number {i} not found in {type(self)}")
        return ret

    @args_checked
    def __delitem__(self, idx: ty.Integral):
        obj = self[idx]
        self.__internal_delete(obj)

    @args_checked
    def __setitem__(self, key: ty.Integral, newvalue):
        self.append(newvalue)

    def __len__(self):
        return len(self._objects)

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __contains__(self, other):
        if not isinstance(other, self._obj_class):
            return False
        # if cache can be trusted from #563
        if self._problem:
            try:
                if other is self[other.number]:
                    return True
                return False
            except KeyError:
                return False
        return other in self._objects

    def __set_logic(self, other, operator):
        """Takes another collection, and apply the operator to it, and returns a new instance.

        Operator must be a callable that accepts a set of the numbers of self,
        and another set for other's numbers.
        """
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Other side must be of the type {type(self).__name__}. {other} given."
            )
        self_nums = set(self.keys())
        other_nums = set(other.keys())
        new_nums = operator(self_nums, other_nums)
        new_objs = {}
        # give preference to self
        for obj in it.chain(other, self):
            if obj.number in new_nums:
                new_objs[obj.number] = obj
        return type(self)(list(new_objs.values()))

    def __and__(self, other):
        return self.__set_logic(other, lambda a, b: a & b)

    def __iand__(self, other):
        new_vals = self & other
        self.__num_cache.clear()
        self._objects.clear()
        self.update(new_vals)
        return self

    def __or__(self, other):
        return self.__set_logic(other, lambda a, b: a | b)

    def __ior__(self, other):
        new_vals = other - self
        self.extend(new_vals)
        return self

    def __sub__(self, other):
        return self.__set_logic(other, lambda a, b: a - b)

    def __isub__(self, other):
        excess_values = self & other
        for excess in excess_values:
            del self[excess.number]
        return self

    def __xor__(self, other):
        return self.__set_logic(other, lambda a, b: a ^ b)

    def __ixor__(self, other):
        new_values = self ^ other
        self._objects.clear()
        self.__num_cache.clear()
        self.update(new_values)
        return self

    def __set_logic_test(self, other, operator):
        """Takes another collection, and apply the operator to it, testing the logic of it.

        Operator must be a callable that accepts a set of the numbers of self,
        and another set for other's numbers.
        """
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Other side must be of the type {type(self).__name__}. {other} given."
            )
        self_nums = set(self.keys())
        other_nums = set(other.keys())
        return operator(self_nums, other_nums)

    def __le__(self, other):
        return self.__set_logic_test(other, lambda a, b: a <= b)

    def __lt__(self, other):
        return self.__set_logic_test(other, lambda a, b: a < b)

    def __ge__(self, other):
        return self.__set_logic_test(other, lambda a, b: a >= b)

    def __gt__(self, other):
        return self.__set_logic_test(other, lambda a, b: a > b)

    def issubset(self, other: typing.Self):
        """Test whether every element in the collection is in other.

        ``collection <= other``

        .. versionadded:: 1.0.0

        Parameters
        ----------
        other : Self
            the set to compare to.

        Returns
        -------
        bool
        """
        return self.__set_logic_test(other, lambda a, b: a.issubset(b))

    def isdisjoint(self, other: typing.Self):
        """Test if there are no elements in common between the collection, and other.

        Collections are disjoint if and only if their intersection
        is the empty set.

        .. versionadded:: 1.0.0

        Parameters
        ----------
        other : Self
            the set to compare to.

        Returns
        -------
        bool
        """
        return self.__set_logic_test(other, lambda a, b: a.isdisjoint(b))

    def issuperset(self, other: typing.Self):
        """Test whether every element in other is in the collection.

        ``collection >= other``

        .. versionadded:: 1.0.0

        Parameters
        ----------
        other : Self
            the set to compare to.

        Returns
        -------
        bool
        """
        return self.__set_logic_test(other, lambda a, b: a.issuperset(b))

    def __set_logic_multi(self, others, operator):
        for other in others:
            if not isinstance(other, type(self)):
                raise TypeError(
                    f"Other argument must be of type {type(self).__name__}. {other} given."
                )
        self_nums = set(self.keys())
        other_sets = []
        for other in others:
            other_sets.append(set(other.keys()))
        valid_nums = operator(self_nums, *other_sets)
        objs = {}
        for obj in it.chain(*others, self):
            if obj.number in valid_nums:
                objs[obj.number] = obj
        return type(self)(list(objs.values()))

    def intersection(self, *others: typing.Self):
        """Return a new collection with all elements in common in collection, and all others.

        ``collection & other & ...``

        .. versionadded:: 1.0.0

        Parameters
        ----------
        *others : Self
            the other collections to compare to.

        Returns
        -------
        typing.Self
        """
        return self.__set_logic_multi(others, lambda a, *b: a.intersection(*b))

    def intersection_update(self, *others: typing.Self):
        """Update the collection keeping all elements in common in collection, and all others.

        ``collection &= other & ...``

        .. versionadded:: 1.0.0

        Parameters
        ----------
        *others : Self
            the other collections to compare to.
        """
        if len(others) == 1:
            self &= others[0]
        else:
            other = others[0].intersection(*others[1:])
            self &= other

    def union(self, *others: typing.Self):
        """Return a new collection with all elements from collection, and all others.

        ``collection | other | ...``

        .. versionadded:: 1.0.0

        Parameters
        ----------
        *others : Self
            the other collections to compare to.

        Returns
        -------
        typing.Self
        """
        return self.__set_logic_multi(others, lambda a, *b: a.union(*b))

    def difference(self, *others: typing.Self):
        """Return a new collection with elements from collection, that are not in the others.

        ``collection - other - ...``

        .. versionadded:: 1.0.0

        Parameters
        ----------
        *others : Self
            the other collections to compare to.

        Returns
        -------
        typing.Self
        """
        return self.__set_logic_multi(others, lambda a, *b: a.difference(*b))

    def difference_update(self, *others: typing.Self):
        """Update the new collection removing all elements from others.

        ``collection -= other | ...``

        .. versionadded:: 1.0.0

        Parameters
        ----------
        *others : Self
            the other collections to compare to.
        """
        new_vals = self.difference(*others)
        self.clear()
        self.update(new_vals)
        return self

    def symmetric_difference(self, other: typing.Self):
        """Return a new collection with elements in either the collection or the other, but not both.

        ``collection ^ other``

        .. versionadded:: 1.0.0

        Parameters
        ----------
        others : Self
            the other collections to compare to.

        Returns
        -------
        typing.Self
        """
        return self ^ other

    def symmetric_difference_update(self, other: typing.Self):
        """Update the collection, keeping only elements found in either collection, but not in both.

        ``collection ^= other``

        .. versionadded:: 1.0.0

        Parameters
        ----------
        others : Self
            the other collections to compare to.
        """
        self ^= other
        return self

    def discard(self, obj: montepy.numbered_mcnp_object.Numbered_MCNP_Object):
        """Remove the object from the collection if it is present.

        .. versionadded:: 1.0.0

        Parameters
        ----------
        obj : Numbered_MCNP_Object
            the object to remove.
        """
        try:
            self.remove(obj)
        except (TypeError, KeyError) as e:
            pass

    def get(self, i: int, default=None) -> (Numbered_MCNP_Object, None):
        """Get ``i`` if possible, or else return ``default``.

        Parameters
        ----------
        i : int
            number of the object to get, not it's location in the
            internal list
        default : object
            value to return if not found

        Returns
        -------
        Numbered_MCNP_Object
        """
        try:
            ret = self.__num_cache[i]
            if ret.number == i:
                return ret
        except KeyError:
            pass
        for obj in self._objects:
            self.__num_cache[obj.number] = obj
            if obj.number == i:
                self.__num_cache[i] = obj
                return obj
        return default

    def keys(self) -> typing.Generator[int, None, None]:
        """Get iterator of the collection's numbers.

        Returns
        -------
        int
        """
        if len(self) == 0:
            yield from []
        for o in self._objects:
            self.__num_cache[o.number] = o
            yield o.number

    def values(self) -> typing.Generator[Numbered_MCNP_Object, None, None]:
        """Get iterator of the collection's objects.

        Returns
        -------
        Numbered_MCNP_Object
        """
        for o in self._objects:
            self.__num_cache[o.number] = o
            yield o

    def items(
        self,
    ) -> typing.Generator[typing.Tuple[int, Numbered_MCNP_Object], None, None]:
        """Get iterator of the collections (number, object) pairs.

        Returns
        -------
        tuple(int, MCNP_Object)
        """
        for o in self._objects:
            yield o.number, o

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Can only compare {type(self).__name__} to each other. {other} was given."
            )
        if len(self) != len(other):
            return False
        keys = sorted(self.keys())
        for key in keys:
            try:
                if self[key] != other[key]:
                    return False
            except KeyError:
                return False
        return True


class NumberedDataObjectCollection(NumberedObjectCollection):
    """
    This is a an abstract collection for numbered objects that are also Data Inputs.

    This collection can be sliced to get a subset of the numberedDataObjectCollection.
    Slicing is done based on the numberedDataObjectCollection numbers, not their order in the input.
    For example, ``problem.numberedDataObjectCollection[1:3]`` will return a new `numberedDataObjectCollection`
    containing numberedDataObjectCollection with numbers from 1 to 3, inclusive.

    See also
    --------
    :class:`~montepy.numbered_object_collection.NumberedObjectCollection`
    """

    def __init__(self, obj_class, objects=None, problem=None):
        self._last_index = None
        if problem and objects:
            try:
                self._last_index = problem.data_inputs.index(objects[-1])
            except ValueError:
                pass
        super().__init__(obj_class, objects, problem)

    @args_checked
    def _append_hook(self, obj, insert_in_data: bool = True):
        """Appends the given object to the end of this collection.

        Parameters
        ----------
        obj : Numbered_MCNP_Object
            the object to add.
        insert_in_data : bool
            Whether to add the object to the linked problem's
            data_inputs.

        Raises
        ------
        NumberConflictError
            if this object has a number that is already in use.
        """
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

    def _get_leading_comment(self, obj):
        """ """
        raise NotImplementedError(f"Should search through data_inputs directly.")

    def _delete_hook(self, obj):
        if self._problem:
            self._problem.data_inputs.remove(obj)

    def clear(self):
        """Removes all objects from this collection."""
        if self._problem:
            for obj in self._objects:
                self._problem.data_inputs.remove(obj)
        self._last_index = None
        super().clear()
