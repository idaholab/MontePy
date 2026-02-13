# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
from abc import abstractmethod
import copy
import itertools
import weakref

from montepy.mcnp_object import MCNP_Object, InitInput
import montepy
import montepy.types as ty
from montepy.utilities import *


def _number_validator(self, number):
    if number < 0:
        raise ValueError("number must be >= 0")

    # Only validate against collection if linked to a collection
    if self._collection is not None:
        collection = self._collection
        collection.check_number(number)
        collection._update_number(self.number, number, self)


class Numbered_MCNP_Object(MCNP_Object):
    """An abstract class to represent an mcnp object that has a number.

    .. versionchanged:: 1.0.0

        Added number parameter

    Parameters
    ----------
    input : Input | str
        The Input syntax object this will wrap and parse.
    number : int
        The number to set for this object.
    jit_parse: bool
    """

    def __init__(
        self, input: InitInput, number: int = None, *, jit_parse: bool = True, **kwargs
    ):
        if not input:
            self._number = self._generate_default_node(int, -1)
        super().__init__(input, jit_parse=jit_parse, **kwargs)
        self._collection_ref = None
        self._load_init_num(number)

    @args_checked
    def _load_init_num(self, number: ty.NonNegativeInt = None):
        if number is not None:
            self.number = number

    _CHILD_OBJ_MAP = {}
    """"""

    @property
    def number(self):
        """The current number of the object that will be written out to a new input.

        Returns
        -------
        int
        """
        return self._number.value

    @number.setter
    @needs_full_cst
    @args_checked
    def number(self, value: ty.NonNegativeInt):
        self._number_validator(value)
        self._number.value = value

    def _number_validator(self, number):
        if number < 0:
            raise ValueError("number must be >= 0")
        if self._problem:
            obj_map = montepy.MCNP_Problem._NUMBERED_OBJ_MAP
            try:
                collection_type = obj_map[type(self)]
            except KeyError as e:
                found = False
                for obj_class in obj_map:
                    if isinstance(self, obj_class):
                        collection_type = obj_map[obj_class]
                        found = True
                        break
                if not found:
                    raise e
            collection = getattr(self._problem, collection_type.__name__.lower())
            collection.check_number(number)
            self._find_impacted_parents(number)
            collection._update_number(self.number, number, self)

    def _find_impacted_parents(self, new_number):
        if self.number == new_number:
            return
        if not self._problem:
            return
        for collection_name, parent_prop, is_container in self._parent_collections():
            collection = getattr(self._problem, collection_name)
            collection.search_parent_objs_by_child(self, parent_prop, is_container)

    @staticmethod
    @abstractmethod
    def _parent_collections():
        pass

    @property
    @abstractmethod
    def old_number(self):
        """The original number of the object provided in the input file

        Returns
        -------
        int
        """
        pass

    def _add_children_objs(self, problem):
        """Adds all children objects from self to the given problem.

        This is called from an :func:`~montepy.numbered_object_collection.NumberedObjectCollection._append_hook`.
        """
        # skip lambda transforms
        filters = {montepy.Transform: lambda transform: not transform.hidden_transform}
        prob_attr_map = montepy.MCNP_Problem._NUMBERED_OBJ_MAP
        for attr_name, obj_class in self._CHILD_OBJ_MAP.items():
            child_collect = getattr(self, attr_name)
            # allow skipping certain items
            if (
                obj_class in filters
                and child_collect
                and not filters[obj_class](child_collect)
            ):
                continue
            if child_collect:
                prob_collect_name = prob_attr_map[obj_class].__name__.lower()
                prob_collect = getattr(problem, prob_collect_name)
                try:
                    # check if iterable
                    iter(child_collect)
                    assert not isinstance(child_collect, MCNP_Object)
                    # ensure isn't a material or something
                    prob_collect.update(child_collect)
                except (TypeError, AssertionError):
                    prob_collect.append(child_collect)

    @property
    def _collection(self):
        """Returns the parent collection this object belongs to, if any."""
        if self._collection_ref is not None:
            return self._collection_ref()
        return None

    def _link_to_collection(self, collection):
        """Links this object to the given collection via a weakref.

        Parameters
        ----------
        collection : NumberedObjectCollection
            The collection to link this object to.
        """
        self._collection_ref = weakref.ref(collection)

    def _unlink_from_collection(self):
        """Unlinks this object from its collection."""
        self._collection_ref = None

    def __getstate__(self):
        state = super().__getstate__()
        # Remove _collection_ref weakref as it can't be pickled
        state.pop("_collection_ref", None)
        return state

    def __setstate__(self, crunchy_data):
        crunchy_data["_collection_ref"] = None
        super().__setstate__(crunchy_data)

    @args_checked
    @needs_full_cst
    def clone(
        self, starting_number: ty.PositiveInt = None, step: ty.PositiveInt = None
    ):
        """Create a new independent instance of this object with a new number.

        This relies mostly on ``copy.deepcopy``.

        Notes
        -----
        If starting_number, or step are not specified
        :func:`~montepy.numbered_object_collection.NumberedObjectCollection.starting_number`,
        and :func:`~montepy.numbered_object_collection.NumberedObjectCollection.step` are used as default values,
        if this object is tied to a problem.
        For instance a ``Material`` will use ``problem.materials`` default information.
        Otherwise ``1`` will be used as default values


        .. versionadded:: 0.5.0

        Parameters
        ----------
        starting_number : int
            The starting number to request for a new object number.
        step : int
            the step size to use to find a new valid number.

        Returns
        -------
        type(self)
            a cloned copy of this object.
        """
        ret = copy.deepcopy(self)
        if self._problem:
            ret.link_to_problem(self._problem)
            test_class = type(self)
            while test_class != object:
                try:
                    collection_type = montepy.MCNP_Problem._NUMBERED_OBJ_MAP[test_class]
                except KeyError:
                    test_class = test_class.__base__
                else:
                    break
            else:  # pragma: no cover
                raise TypeError(
                    f"Could not find collection type for this object, {self}."
                )

            collection = getattr(self._problem, collection_type.__name__.lower())
            if starting_number is None:
                starting_number = collection.starting_number
            if step is None:
                step = collection.step
            ret.number = collection.request_number(starting_number, step)
            collection.append(ret)
            return ret
        if starting_number is None:
            starting_number = 1
        if step is None:
            step = 1
        for number in itertools.count(starting_number, step):
            # only reached if not tied to a problem
            ret.number = number
            if number != self.number:
                return ret

    def __str__(self):
        return f"{type(self).__name__}: {self.number}"

    def _repr_args(self):
        return [f"number={self.number}"]
