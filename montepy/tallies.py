# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import montepy
from montepy.numbered_object_collection import NumberedObjectCollection


class Tallies(NumberedObjectCollection):
    """
    A container of multiple :class:`~montepy.data_inputs.tally.Tally` instances.

    :param objects: the list of tallies to start with if needed
    :type objects: list
    """

    def __init__(self, objects=None, problem=None):
        super().__init__(montepy.data_inputs.tally.Tally, objects, problem)
