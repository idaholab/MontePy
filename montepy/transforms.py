# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
import montepy
from montepy.utilities import *
from montepy.data_inputs.transform import Transform
from montepy.numbered_object_collection import NumberedDataObjectCollection
import montepy.types as ty


class Transforms(NumberedDataObjectCollection):
    """A container of multiple :class:`~montepy.data_inputs.transform.Transform` instances.

    This collection can be sliced to get a subset of the Transforms.
    Slicing is done based on the Transform numbers, not their order in the input.
    For example, ``problem.transforms[1:3]`` will return a new `Transforms` collection
    containing Transforms with numbers from 1 to 3, inclusive.

    See also
    --------
    :class:`~montepy.numbered_object_collection.NumberedObjectCollection`

    Notes
    -----

    For examples see the ``NumberedObjectCollection`` :ref:`collect ex`.
    """

    def __init__(
        self,
        objects: ty.Iterable[Transform] = None,
        problem: montepy.MCNP_Problem = None,
    ):
        super().__init__(Transform, objects, problem)
