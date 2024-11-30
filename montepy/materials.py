# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.

from __future__ import annotations
from typing import Generator, Union

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

    def get_containing(
        self,
        nuclide: Union[
            montepy.data_inputs.nuclide.Nuclide,
            montepy.data_inputs.nuclide.Nucleus,
            montepy.Element,
            str,
            int,
        ],
        *args: Union[
            montepy.data_inputs.nuclide.Nuclide,
            montepy.data_inputs.nuclide.Nucleus,
            montepy.Element,
            str,
            int,
        ],
        threshold: float = 0.0,
    ) -> Generator[Material]:
        """
        Get all materials that contain these nuclides.

        This uses :func:`~montepy.data_inputs.material.Material.contains` under the hood.
        See that documentation for more guidance.

        Examples
        ^^^^^^^^

        One example would to be find all water bearing materials:

        .. testcode::

            import montepy
            problem = montepy.read_input("foo.imcnp")
            for mat in problem.materials.get_containing("H-1", "O-16", threshold = 0.3):
                print(mat)

        .. testoutput::

            MATERIAL: 1, ['hydrogen', 'oxygen']

        .. versionadded:: 1.0.0

        :param nuclide: the first nuclide to check for.
        :type nuclide: Union[Nuclide, Nucleus, Element, str, int]
        :param args: a plurality of other nuclides to check for.
        :type args: Union[Nuclide, Nucleus, Element, str, int]
        :param threshold: the minimum concentration of a nuclide to be considered. The material components are not
            first normalized.
        :type threshold: float

        :return: A generator of all matching materials
        :rtype: Generator[Material]

        :raises TypeError: if any argument is of the wrong type.
        :raises ValueError: if the fraction is not positive or zero, or if nuclide cannot be interpreted as a Nuclide.
        """
        nuclides = []
        for nuclide in [nuclide] + list(args):
            if not isinstance(
                nuclide,
                (
                    str,
                    int,
                    montepy.Element,
                    montepy.data_inputs.nuclide.Nucleus,
                    montepy.Nuclide,
                ),
            ):
                raise TypeError(
                    f"nuclide must be of type str, int, Element, Nucleus, or Nuclide. "
                    f"{nuclide} of type {type(nuclide)} given."
                )
            if isinstance(nuclide, (str, int)):
                nuclide = montepy.Nuclide(nuclide)
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
            if material.contains(*nuclides, threshold=threshold):
                # maybe? Maybe not?
                # should Materials act like a set?
                yield material

    @property
    def default_libraries(self) -> dict[montepy.LibraryType, montepy.Library]:
        """
        The default libraries for this problem defined by ``M0``.


        Examples
        ^^^^^^^^

        To set the default libraries for a problem you need to set this dictionary
        to a Library or string.

        .. testcode:: python

            import montepy
            problem = montepy.read_input("foo.imcnp")

            # set neutron default to ENDF/B-VIII.0
            problem.materials.default_libraries["nlib"] = "00c"
            # set photo-atomic
            problem.materials.default_libraries[montepy.LibraryType.PHOTO_ATOMIC] = montepy.Library("80p")

        .. versionadded:: 1.0.0

        :returns: the default libraries in use
        :rtype: dict[LibraryType, Library]
        """
        try:
            return self[0].default_libraries
        except KeyError:
            default = Material()
            default.number = 0
            self.append(default)
            return self.default_libraries
