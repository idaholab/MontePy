# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from abc import abstractmethod
import copy
import itertools
from montepy.errors import NumberConflictError
from montepy.mcnp_object import MCNP_Object


class Numbered_MCNP_Object(MCNP_Object):
    @property
    @abstractmethod
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
        """ """
        ret = copy.deepcopy(self)
        for number in itertools.count(starting_number, step=1):
            try:
                ret.number = number
                return ret
            except NumberConflictError:
                pass
