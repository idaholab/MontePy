# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
import montepy
from montepy.numbered_object_collection import NumberedDataObjectCollection
from montepy.data_inputs.transform import Transform


class Transforms(NumberedDataObjectCollection):
    """A container of multiple :class:`~montepy.data_inputs.transform.Transform` instances.

    Notes
    -----

    For examples see the ``NumberedObjectCollection`` :ref:`collect ex`.
    """

    def __init__(self, objects: list = None, problem: montepy.MCNP_Problem = None):
        super().__init__(Transform, objects, problem)
