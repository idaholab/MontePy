# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import montepy
from montepy.numbered_object_collection import NumberedObjectCollection

Material = montepy.data_inputs.material.Material


class Materials(NumberedObjectCollection):
    """
    A container of multiple :class:`~montepy.data_inputs.material.Material` instances.

    :param objects: the list of materials to start with if needed
    :type objects: list
    """

    def __init__(self, objects=None, problem=None):
        super().__init__(Material, objects, problem)
