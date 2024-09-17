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

    def get_containing(self, nuclide, *args, threshold=0.0):
        """ """
        nuclides = []
        for nuclide in [nuclide] + args:
            if not isinstance(nuclide, (str, int, Element, Nucleus, Nuclide)):
                raise TypeError("")  # foo
            if isinstance(nuclide, (str, int)):
                nuclide = montepy.Nuclide.get_from_fancy_name(nuclide)
            nuclides.append(nuclide)

        def sort_by_type(nuclide):
            type_map = {
                montepy.data_inputs.element.Element: 0,
                montepy.data_inputs.nuclide.Nucleus: 1,
                montepy.data_inputs.nuclide.Nuclide: 2,
            }
            return type_map[type(nuclide)]

        # optimize by most hashable and fail fast
        nuclides = sorted(nuclides, key=sort_by_type)
        for material in self:
            if material.contains(*nuclides, threshold):
                # maybe? Maybe not?
                # should Materials act like a set?
                yield material
