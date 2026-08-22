# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import warnings

import montepy
from montepy.exceptions import MalformedInputError, MalformedInputWarning
from montepy.numbered_object_collection import NumberedDataObjectCollection
from montepy.utilities import *


class Tallies(NumberedDataObjectCollection):
    """
    A container of multiple :class:`~montepy.data_inputs.tally.Tally` instances.

    :param objects: the list of tallies to start with if needed
    :type objects: list

    .. versionadded:: 1.6.0b2
    """

    def __init__(self, objects=None, problem=None):
        super().__init__(montepy.data_inputs.tally.Tally, objects, problem)
        self._fm_queue = {}
        self._multipliers = []

    @property
    def multipliers(self):
        """The :class:`~montepy.data_inputs.tally_multiplier.TallyMultiplier` instances
        held by this collection.

        Unlike the :class:`~montepy.data_inputs.tally.Tally` instances in this
        collection, these are not stored in a
        :class:`~montepy.numbered_object_collection.NumberedObjectCollection`,
        as a ``TallyMultiplier``'s number is not an independent identity: it
        always matches its parent tally's number, and two ``FM`` cards can
        transiently share a number before one is linked.

        Returns
        -------
        list
            the tally multipliers ("FM" cards) in this problem.
        """
        return list(self._multipliers)

    @args_checked
    def append(
        self,
        obj: "montepy.data_inputs.tally.Tally | montepy.data_inputs.tally_multiplier.TallyMultiplier",
        insert_in_data: bool = True,
        **kwargs,
    ):
        if isinstance(obj, montepy.data_inputs.tally.Tally):
            if obj.number in self._fm_queue:
                fm = self._fm_queue.pop(obj.number)
                fm._link_to_parent(obj)
                obj._multiplier = fm
            super().append(obj, insert_in_data=insert_in_data, **kwargs)
        elif isinstance(obj, montepy.data_inputs.tally_multiplier.TallyMultiplier):
            if obj not in self._multipliers:
                self._multipliers.append(obj)
            try:
                tally = self[obj._old_number.value]
                obj._link_to_parent(tally)
                tally._multiplier = obj
            except KeyError:
                self._fm_queue[obj._old_number.value] = obj
            if (
                insert_in_data
                and self._problem is not None
                and obj not in self._problem.data_inputs
            ):
                self._problem.data_inputs.append(obj)

    def _delete_hook(self, obj, **kwargs):
        fm = getattr(obj, "_multiplier", None)
        if fm is not None:
            if fm in self._multipliers:
                self._multipliers.remove(fm)
            if self._problem is not None and fm in self._problem.data_inputs:
                self._problem.data_inputs.remove(fm)
            fm._parent_tally = None
            warnings.warn(
                f"Tally multiplier (FM) card for tally {obj.number} was removed "
                "because its parent tally was deleted.",
                MalformedInputWarning,
            )
        super()._delete_hook(obj, **kwargs)

    def finalize_init(self, jit_parse: bool = False):
        # Raise error for unflushed connection
        for num, fm in self._fm_queue.items():
            raise MalformedInputError(
                fm._input,
                f'Tally multiplier "FM" input has no parent tally with number: {num}',
            )
