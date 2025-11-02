# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
from abc import abstractmethod
import copy
import itertools

from montepy.mcnp_object import MCNP_Object, InitInput
import montepy
import montepy.types as ty
from montepy.utilities import *


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
        collection._update_number(self.number, number, self)


class Numbered_MCNP_Object(MCNP_Object):
    """An abstract class to represent an mcnp object that has a number.

    .. versionchanged:: 1.0.0

        Added number parameter

    Parameters
    ----------
    input : Input | str
        The Input syntax object this will wrap and parse.
    parser : MCNP_Parser
        The parser object to parse the input with.
    number : int
        The number to set for this object.
    jit_parse: bool
    """

    def __init__(
        self, input: InitInput, number: int = None, *, jit_parse: bool = True, **kwargs
    ):
        if not input:
            self._number = self._generate_default_node(int, -1)
        super().__init__(input, parser)
        self._load_init_num(number)

    @args_checked
    def _load_init_num(self, number: ty.NonNegativeInt = None):
        if number is not None:
            self.number = number

    _CHILD_OBJ_MAP = {}
    """"""

    @make_prop_val_node("_number", ty.Integral, validator=_number_validator)
    def number(self):
        """The current number of the object that will be written out to a new input.

        Returns
        -------
        int
        """
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

    @args_checked
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
