# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.numbered_object_collection import NumberedObjectCollection
from montepy.universe import Universe


class Universes(NumberedObjectCollection):
    """
    A container of multiple :class:`~montepy.universe.Universe` instances.
    """

    def __init__(self, objects=None, problem=None):
        super().__init__(Universe, objects, problem)
