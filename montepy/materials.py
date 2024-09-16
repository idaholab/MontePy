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


def __create_mat_generator(element):
    """ """

    def closure(obj):
        for material in obj:
            if element in material:
                yield material

    return closure


def __setup_element_generators():
    elements = [
        montepy.data_inputs.element.Element(z)
        for z in range(1, montepy.data_inputs.element.MAX_Z_NUM + 1)
    ]
    for element in elements:
        doc = f"Generator for all material containing element: {element.name}"
        getter = property(__create_mat_generator(element), doc=doc)
        setattr(Materials, element.symbol, getter)


__setup_element_generators()
