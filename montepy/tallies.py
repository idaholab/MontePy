# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import montepy
from montepy.exceptions import MalformedInputError
from montepy.numbered_object_collection import NumberedDataObjectCollection
from montepy.utilities import *


class Tallies(NumberedDataObjectCollection):
    """
    A container of multiple :class:`~montepy.data_inputs.tally.Tally` instances.

    :param objects: the list of tallies to start with if needed
    :type objects: list
    """

    def __init__(self, objects=None, problem=None):
        super().__init__(montepy.data_inputs.tally.Tally, objects, problem)
        self._fm_queue = {}

    @args_checked
    def append(
        self,
        obj: "montepy.data_inputs.tally.Tally | montepy.data_inputs.tally_multiplier.TallyMultiplier",
        **kwargs,
    ):
        if isinstance(obj, montepy.data_inputs.tally.Tally):
            if obj.number in self._fm_queue:
                fm = self._fm_queue.pop(obj.number)
                fm._link_to_parent(obj)
                obj._multiplier = fm
            super().append(obj, **kwargs)
        elif isinstance(obj, montepy.data_inputs.tally_multiplier.TallyMultiplier):
            try:
                tally = self[obj._old_number.value]
                obj._link_to_parent(tally)
                tally._multiplier = obj
            except KeyError:
                self._fm_queue[obj._old_number.value] = obj

    def finalize_init(self, jit_parse: bool = False):
        # Raise error for unflushed connection
        for num, fm in self._fm_queue.items():
            raise MalformedInputError(
                fm._input,
                f'Tally multiplier "FM" input has no parent tally with number: {num}',
            )
