# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.

from __future__ import annotations
import copy
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

    .. note::

        For examples see the ``NumberedObjectCollection`` :ref:`collect ex`.


    :param objects: the list of materials to start with if needed
    :type objects: list
    """

    def __init__(self, objects=None, problem=None):
        super().__init__(Material, objects, problem)

    def get_containing(
        self,
        *nuclides: Union[
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

        :param nuclides: a plurality of other nuclides to check for.
        :type nuclides: Union[Nuclide, Nucleus, Element, str, int]
        :param threshold: the minimum concentration of a nuclide to be considered. The material components are not
            first normalized.
        :type threshold: float

        :return: A generator of all matching materials
        :rtype: Generator[Material]

        :raises TypeError: if any argument is of the wrong type.
        :raises ValueError: if the fraction is not positive or zero, or if nuclide cannot be interpreted as a Nuclide.
        """
        # TODO collision here
        # TODO other type enforcement
        nuclides = []
        for nuclide in nuclides:
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

    def mix(
        self,
        materials: list[Material],
        fractions: list[float],
        starting_number=None,
        step=None,
    ) -> Material:
        """
        Mix the given materials in the provided fractions to create a new material.

        All materials must use the same fraction type, either atom fraction or mass fraction.
        The fractions given to this method are interpreted in that way as well.

        This new material will automatically be added to this collection.

        Examples
        --------

        An example way to mix materials is to first create the materials to mix:

        .. testcode::

            import montepy
            mats = montepy.Materials()
            h2o = montepy.Material()
            h2o.number = 1
            h2o.add_nuclide("1001.80c", 2.0)
            h2o.add_nuclide("8016.80c", 1.0)

            boric_acid = montepy.Material()
            boric_acid.number = 2
            for nuclide, fraction in {
                "1001.80c": 3.0,
                "B-10.80c": 1.0 * 0.189,
                "B-11.80c": 1.0 * 0.796,
                "O-16.80c": 3.0
            }.items():
                boric_acid.add_nuclide(nuclide, fraction)

        Then to make the material mixture you just need to specify the fractions:

        .. testcode::

            boron_ppm = 10
            boric_conc = boron_ppm * 1e-6
            borated_water = mats.mix([h2o, boric_acid], [1 - boric_conc, boric_conc])


        :param materials: the materials to mix.
        :type materials: list[Material]
        :param fractions: the corresponding fractions for each material in either atom or mass fractions, depending on
            the materials fraction type.
        :param starting_number: the starting number to assign this new material.
        :type starting_number: Union[int, None]
        :param step: the step size to take when finding a new number.
        :type step: Union[int, None]
        :returns: a new material with the mixed components of the given materials
        :rtype: Material
        :raises TypeError: if invalid objects are given.
        :raises ValueError: if the number of elements in the two lists mismatch, or if not all the materials are of the
            same fraction type, or if a negative starting_number or step are given.
        """
        if not isinstance(materials, list):
            raise TypeError(f"materials must be a list. {materials} given.")
        if len(materials) == 0:
            raise ValueError(f"materials must be non-empty. {materials} given.")
        for mat in materials:
            if not isinstance(mat, Material):
                raise TypeError(
                    f"material in materials is not of type Material. {mat} given."
                )
            if mat.is_atom_fraction != materials[0].is_atom_fraction:
                raise ValueError(
                    f"All materials must have the same is_atom_fraction value. {mat} is the odd one out."
                )
        if not isinstance(fractions, list):
            raise TypeError(f"fractions must be a list. {fractions} given.")
        for frac in fractions:
            if not isinstance(frac, float):
                raise TypeError(f"fraction in fractions must be a float. {frac} given.")
            if frac < 0.0:
                raise ValueError(f"Fraction cannot be negative. {frac} given.")
        if len(fractions) != len(materials):
            raise ValueError(
                f"Length of materials and fractions don't match. The lengths are, materials: {len(materials)}, fractions: {len(fractions)}"
            )
        if not isinstance(starting_number, (int, type(None))):
            raise TypeError(
                f"starting_number must be an int. {starting_number} of type {type(starting_number)} given."
            )
        if starting_number is not None and starting_number <= 0:
            raise ValueError(
                f"starting_number must be positive. {starting_number} given."
            )
        if not isinstance(step, (int, type(None))):
            raise TypeError(f"step must be an int. {step} of type {type(step)} given.")
        if step is not None and step <= 0:
            raise ValueError(f"step must be positive. {step} given.")
        ret = Material()
        if starting_number is None:
            starting_number = self.starting_number
        if step is None:
            step = self.step
        ret.number = self.request_number(starting_number, step)
        ret.is_atom_fraction = materials[0].is_atom_fraction
        new_mats = copy.deepcopy(materials)
        for mat, fraction in zip(new_mats, fractions):
            mat.normalize()
            for nuclide, frac in mat._components:
                frac = copy.deepcopy(frac)
                frac.value *= fraction
                ret._components.append((nuclide, frac))
        return ret
