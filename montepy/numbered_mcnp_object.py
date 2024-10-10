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

    def clone(self, starting_number=None, step=None):
        """
        Create a new independent instance of this object with a new number.

        This relies mostly on ``copy.deepcopy``.

        .. note ::
            If starting_number, or step are not specified
            :func:`~montepy.numbered_object_collection.NumberedObjectCollection.starting_number`,
            and :func:`~montepy.numbered_object_collection.NumberedObjectCollection.step` are used as default values,
            if this object is tied to a problem.
            For instance a ``Material`` will use ``problem.materials`` default information.
            Otherwise ``1`` will be used as default values

        .. versionadded:: 0.5.0

        :param starting_number: The starting number to request for a new object number.
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
        ret = copy.deepcopy(self)
        if self._problem:
            ret.link_to_problem(self._problem)
            collection_type = montepy.MCNP_Problem._NUMBERED_OBJ_MAP[type(self)]
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
