# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from abc import abstractmethod
import copy
import itertools
from montepy.errors import NumberConflictError
from montepy.mcnp_object import MCNP_Object
import montepy
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

    @make_prop_val_node("_number", int, validator=_number_validator)
    def number(self):
        """
        The current number of the object that will be written out to a new input.

        :rtype: int
        """
        pass

    @property
    @abstractmethod
    def old_number(self):
        """
        The original number of the object provided in the input file

        :rtype: int
        """
        pass

    def clone(self, starting_number=1, step=1):
        """
        Create a new independent instance of this object with a new number.

        This relies mostly on ``copy.deepcopy``.

        :param starting_number: The starting number to request for a new object number.
        :type starting_number: int
        :param step: the step size to use to find a new valid number.
        :type step: int
        :returns: a cloned copy of this object.
        :rtype: type(self)

        """
        if not isinstance(starting_number, int):
            raise TypeError(f"Starting_number must be an int. {starting_number} given.")
        if not isinstance(step, int):
            raise TypeError(f"step must be an int. {step} given.")
        if starting_number <= 0:
            raise ValueError(f"starting_number must be >= 1. {starting_number} given.")
        if step <= 0:
            raise ValueError(f"step must be >= 1. {step} given.")
        ret = copy.deepcopy(self)
        if self._problem:
            ret.link_to_problem(self._problem)
            collection_type = montepy.MCNP_Problem._NUMBERED_OBJ_MAP[type(self)]
            collection = getattr(self._problem, collection_type.__name__.lower())
            ret.number = collection.request_number(starting_number, step)
            collection.append(ret)
        for number in itertools.count(starting_number, step=1):
            try:
                ret.number = number
                return ret
            except NumberConflictError:
                pass
