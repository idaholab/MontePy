# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import montepy
from montepy.numbered_object_collection import NumberedDataObjectCollection

Material = montepy.data_inputs.material.Material


class Materials(NumberedDataObjectCollection):
    """
    A container of multiple :class:`~montepy.data_inputs.material.Material` instances.

    .. note::
        When items are added to this (and this object is linked to a problem),
        they will also be added to :func:`montepy.mcnp_problem.MCNP_Problem.data_inputs`.

    :param objects: the list of materials to start with if needed
    :type objects: list
    """

    def __init__(self, objects=None, problem=None):
        super().__init__(Material, objects, problem)
