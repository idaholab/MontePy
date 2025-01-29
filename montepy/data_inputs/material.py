# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import copy
from montepy.data_inputs import data_input, thermal_scattering
from montepy.data_inputs.isotope import Isotope
from montepy.data_inputs.material_component import MaterialComponent
from montepy.input_parser import syntax_node
from montepy.input_parser.material_parser import MaterialParser
from montepy import mcnp_object
from montepy.numbered_mcnp_object import Numbered_MCNP_Object
from montepy.errors import *
from montepy.utilities import *
import itertools
import re

import warnings


class Material(data_input.DataInputAbstract, Numbered_MCNP_Object):
    """
    A class to represent an MCNP material.

    .. note::

        There is a known bug (:issue:`182`) that valid MCNP material definitions cannot be parsed.


    :param input: the input card that contains the data
    :type input: Input
    """

    _parser = MaterialParser()

    def __init__(self, input=None):
        self._material_components = {}
        self._thermal_scattering = None
        self._is_atom_fraction = True
        self._number = self._generate_default_node(int, -1)
        super().__init__(input)
        if input:
            num = self._input_number
            self._old_number = copy.deepcopy(num)
            self._number = num
            set_atom_frac = False
            isotope_fractions = self._tree["data"]
            if isinstance(isotope_fractions, syntax_node.IsotopesNode):
                iterator = iter(isotope_fractions)
            else:  # pragma: no cover
                # this is a fall through error, that should never be raised,
                # but is here just in case
                raise MalformedInputError(
                    input,
                    f"Material definitions for material: {self.number} is not valid.",
                )
            for isotope_node, fraction in iterator:
                isotope = Isotope(node=isotope_node, suppress_warning=True)
                fraction.is_negatable_float = True
                if not set_atom_frac:
                    set_atom_frac = True
                    if not fraction.is_negative:
                        self._is_atom_fraction = True
                    else:
                        self._is_atom_fraction = False
                else:
                    # if switching fraction formatting
                    if (not fraction.is_negative and not self._is_atom_fraction) or (
                        fraction.is_negative and self._is_atom_fraction
                    ):
                        raise MalformedInputError(
                            input,
                            f"Material definitions for material: {self.number} cannot use atom and mass fraction at the same time",
                        )

                self._material_components[isotope] = MaterialComponent(
                    isotope, fraction, suppress_warning=True
                )

    @make_prop_val_node("_old_number")
    def old_number(self):
        """
        The material number that was used in the read file

        :rtype: int
        """
        pass

    @property
    def is_atom_fraction(self):
        """
        If true this constituent is in atom fraction, not weight fraction.

        :rtype: bool
        """
        return self._is_atom_fraction

    @property
    def material_components(self):
        """
            The internal dictionary containing all the components of this material.

        .. deprecated:: 0.4.1
            MaterialComponent has been deprecated as part of a redesign for the material
            interface due to a critical bug in how MontePy handles duplicate nuclides.
            See :ref:`migrate 0 1`.

            The keys are :class:`~montepy.data_inputs.isotope.Isotope` instances, and the values are
            :class:`~montepy.data_inputs.material_component.MaterialComponent` instances.

            :rtype: dict
        """
        warnings.warn(
            f"""material_components is deprecated, and will be removed in MontePy 1.0.0.
See <https://www.montepy.org/migrations/migrate0_1.html> for more information """,
            DeprecationWarning,
        )
        return self._material_components

    @make_prop_pointer("_thermal_scattering", thermal_scattering.ThermalScatteringLaw)
    def thermal_scattering(self):
        """
        The thermal scattering law for this material

        :rtype: ThermalScatteringLaw
        """
        return self._thermal_scattering

    @property
    def cells(self):
        """A generator of the cells that use this material.

        :returns: an iterator of the Cell objects which use this.
        :rtype: generator
        """
        if self._problem:
            for cell in self._problem.cells:
                if cell.material == self:
                    yield cell

    def format_for_mcnp_input(self, mcnp_version):
        """
        Creates a string representation of this MCNP_Object that can be
        written to file.

        :param mcnp_version: The tuple for the MCNP version that must be exported to.
        :type mcnp_version: tuple
        :return: a list of strings for the lines that this input will occupy.
        :rtype: list
        """
        lines = super().format_for_mcnp_input(mcnp_version)
        if self.thermal_scattering is not None:
            lines += self.thermal_scattering.format_for_mcnp_input(mcnp_version)
        return lines

    def _update_values(self):
        new_list = syntax_node.IsotopesNode("new isotope list")
        for idx, (isotope, component) in enumerate(self._material_components.items()):
            isotope._tree.value = isotope.mcnp_str()
            node = component._tree
            node.is_negatable_float = True
            node.is_negative = not self.is_atom_fraction
            if idx < len(self._material_components) - 1 and not node.padding:
                node.padding = syntax_node.PaddingNode(" ")
            new_list.append(("_", isotope._tree, component._tree))
        self._tree.nodes["data"] = new_list

    def add_thermal_scattering(self, law):
        """
        Adds thermal scattering law to the material

        :param law: the law that is mcnp formatted
        :type law: str
        """
        if not isinstance(law, str):
            raise TypeError(
                f"Thermal Scattering law for material {self.number} must be a string"
            )
        self._thermal_scattering = thermal_scattering.ThermalScatteringLaw(
            material=self
        )
        self._thermal_scattering.add_scattering_law(law)

    def update_pointers(self, data_inputs):
        """
        Updates pointer to the thermal scattering data

        :param data_inputs: a list of the data inputs in the problem
        :type data_inputs: list
        """
        pass

    @staticmethod
    def _class_prefix():
        return "m"

    @staticmethod
    def _has_number():
        return True

    @staticmethod
    def _has_classifier():
        return 0

    def __repr__(self):
        ret = f"MATERIAL: {self.number} fractions: "
        if self.is_atom_fraction:
            ret += "atom\n"
        else:
            ret += "mass\n"

        for component in self._material_components:
            ret += repr(self._material_components[component]) + "\n"
        if self.thermal_scattering:
            ret += f"Thermal Scattering: {self.thermal_scattering}"

        return ret

    def __str__(self):
        elements = self._get_material_elements()
        return f"MATERIAL: {self.number}, {elements}"

    def _get_material_elements(self):
        sortable_components = [
            (iso, component.fraction)
            for iso, component in self._material_components.items()
        ]
        sorted_comps = sorted(sortable_components)
        elements_set = set()
        elements = []
        for isotope, _ in sorted_comps:
            if isotope.element not in elements_set:
                elements_set.add(isotope.element)
                elements.append(isotope.element.name)
        return elements

    def validate(self):
        if len(self._material_components) == 0:
            raise IllegalState(
                f"Material: {self.number} does not have any components defined."
            )

    def __hash__(self):
        """WARNING: this is a temporary solution to make sets remove duplicate materials.

        This should be fixed in the future to avoid issues with object mutation:
            <https://eng.lyft.com/hashing-and-equality-in-python-2ea8c738fb9d>

        """
        temp_hash = ""
        sorted_isotopes = sorted(list(self._material_components.keys()))
        for isotope in sorted_isotopes:
            temp_hash = hash(
                (temp_hash, str(isotope), self._material_components[isotope].fraction)
            )

        return hash((temp_hash, self.number))

    def __eq__(self, other):
        return hash(self) == hash(other)
