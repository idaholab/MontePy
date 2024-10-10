# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.numbered_object_collection import NumberedDataObjectCollection
from montepy.data_inputs.transform import Transform


class Transforms(NumberedDataObjectCollection):
    """
    A container of multiple :class:`~montepy.data_inputs.transform.Transform` instances.
    """

    def __init__(self, objects=None, problem=None):
        super().__init__(Transform, objects, problem)
