# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import copy
import itertools

from montepy.data_inputs import data_input, thermal_scattering
from montepy.data_inputs.nuclide import Nuclide
from montepy.data_inputs.element import Element
from montepy.data_inputs.material_component import MaterialComponent
from montepy.input_parser import syntax_node
from montepy.input_parser.material_parser import MaterialParser
from montepy import mcnp_object
from montepy.numbered_mcnp_object import Numbered_MCNP_Object
from montepy.errors import *
from montepy.utilities import *

import re
import warnings

# TODO implement default library for problem and material
# TODO implement change all libraries


def _number_validator(self, number):
    if number <= 0:
        raise ValueError("number must be > 0")
    if self._problem:
        self._problem.materials.check_number(number)


class Material(data_input.DataInputAbstract, Numbered_MCNP_Object):
    """
    A class to represent an MCNP material.

    :param input: the input card that contains the data
    :type input: Input
    """

    _parser = MaterialParser()

    def __init__(self, input=None):
        self._components = []
        self._thermal_scattering = None
        self._is_atom_fraction = False
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
                isotope = Nuclide(node=isotope_node)
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
                self._components.append((isotope, fraction))

    @make_prop_val_node("_old_number")
    def old_number(self):
        """
        The material number that was used in the read file

        :rtype: int
        """
        pass

    @make_prop_val_node("_number", int, validator=_number_validator)
    def number(self):
        """
        The number to use to identify the material by

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

        :raises DeprecationWarning: This has been fully deprecated and cannot be used.
        """
        raise DeprecationWarning(
            f"""material_components is deprecated, and has been removed in MontePy 1.0.0.
See <https://www.montepy.org/migrations/migrate0_1.html> for more information """
        )

    def __getitem__(self, idx):
        """ """
        if not isinstance(idx, (int, slice)):
            raise TypeError(f"Not a valid index. {idx} given.")
        return self._components[idx]

    def __iter__(self):
        return iter(self._components)

    def __setitem__(self, key, newvalue):
        """ """
        if not isinstance(idx, (int, slice)):
            raise TypeError(f"Not a valid index. {idx} given.")
        self._check_valid_comp(newvalue)
        self._components[idx] = newvalue

    def _check_valid_comp(self, newvalue):
        if not isinstance(newvalue, tuple):
            raise TypeError(
                f"Invalid component given. Must be tuple of Nuclide, fraction. {newvalue} given."
            )
        if len(newvalue) != 2:
            raise ValueError(
                f"Invalid component given. Must be tuple of Nuclide, fraction. {newvalue} given."
            )
        if not isinstance(newvalue[0], Nuclide):
            raise TypeError(f"First element must be an Nuclide. {newvalue[0]} given.")
        if not isinstance(newvalue[1], (float, int)):
            raise TypeError(
                f"Second element must be a fraction greater than 0. {newvalue[1]} given."
            )
        if newvalue[1] < 0.0:
            raise TypeError(
                f"Second element must be a fraction greater than 0. {newvalue[1]} given."
            )

    def __delitem__(self, idx):
        if not isinstance(idx, (int, slice)):
            raise TypeError(f"Not a valid index. {idx} given.")
        del self._components[idx]

    def append(self, obj):
        self._check_valid_comp(obj)
        self._components.append(obj)

    def __prep_filter(filter_obj):
        if callable(filter_obj):
            return filter_obj

        elif isinstance(filter_obj, slice):

            def slicer(val):
                if filter_obj.start:
                    start = filter_obj.start
                    if val < filter_obj.start:
                        return False
                else:
                    start = 0
                if filter_obj.stop:
                    if val >= filter_obj.stop:
                        return False
                if filter_obj.step:
                    if (val - start) % filter_obj.step != 0:
                        return False
                return True

            return slicer

        else:
            return lambda val: val == filter_obj

    def find(
        self, fancy_name=None, element=None, A=None, meta_isomer=None, library=None
    ):
        """ """
        filters = []
        for component in self._components:
            for filt in filters:
                found = filt(component[0])
                if not found:
                    break
            if found:
                yield component

    def find_vals(
        self, fancy_name=None, element=None, A=None, meta_isomer=None, library=None
    ):
        """ """
        pass

    def __bool__(self):
        return bool(self._components)

    def __get_pointer_iso(self, key):
        base_isotope = Nuclide.get_from_fancy_name(key)
        element = self._pointers[base_isotope.element]
        try:
            isotope_pointer = element[(base_isotope.A, base_isotope.meta_state)]
            # only one library, and it's ambiguous
            if len(isotope_pointer) == 1 and base_isotope.library == "":
                pointer = next(isotope_pointer)
            else:
                pointer = isotope_pointer[base_isotope.library]
            return pointer
        except KeyError as e:
            # TODO
            raise e

    def __get_slice(self, key):
        # pad to full key if necessary
        if len(key) < 4:
            key = list(key)
            for _ in range(4 - len(key)):
                key.append(slice(None))
            key = tuple(key)
        # detect if can do optimized search through pointers
        is_slice = [isinstance(s, slice) for s in key]
        num_slices = is_slice.count(True)
        # test if all tuples at end
        if all(is_slice[-num_slices:]):
            return self.__get_optimal_slice(key, num_slices)
        return self.__get_brute_slice(key)

    _LIB_PARSER = re.compile(r"\.?(?P<num>\d{2,})(?P<type>[a-z]+)", re.I)

    @classmethod
    def _match_library_slice(cls, keys, slicer):
        if all((a is None for a in (slicer.start, slicer.stop, slicer.step))):
            return [True for _ in keys]
        # TODO handle non-matches
        matches = [cls._LIB_PARSER.match(k).groupdict() for k in keys]
        if slicer.start:
            start_match = cls._LIB_PARSER.match(slicer.start).groupdict()
        else:
            start_match = None
        if slicer.stop:
            stop_match = cls._LIB_PARSER.match(slicer.stop).groupdict()
        else:
            stop_match = None
        # TODO this feels janky and verbose
        if start_match and stop_match:
            # TODO
            assert start_match["type"] == stop_match["type"]
        if start_match:
            lib_type = start_match["type"].lower()
        elif stop_match:
            lib_type = stop_match["type"].lower()
        assert start_match or stop_match
        ret = [m["type"].lower() == lib_type for m in matches]
        start_num = int(start_match["num"]) if start_match else None
        stop_num = int(stop_match["num"]) if stop_match else None
        num_match = cls._match_slice(
            [int(m["num"]) for m in matches], slice(start_num, stop_num, slicer.step)
        )
        return [old and num for old, num in zip(ret, num_match)]

    @staticmethod
    def _match_slice(keys, slicer):
        if all((a is None for a in (slicer.start, slicer.stop, slicer.step))):
            return [True for _ in keys]
        if slicer.start:
            ret = [key >= slicer.start for key in keys]
        else:
            ret = [True for _ in keys]
        if slicer.step not in {None, 1}:
            if slicer.start:
                start = slicer.start
            else:
                start = 0
            ret = [
                old and ((key - start) % slicer.step == 0)
                for old, key in zip(ret, keys)
            ]
        if slicer.stop in {None, -1}:
            return ret
        if slicer.stop > 0:
            end = slicer.stop
        else:
            end = keys[slicer.end]
        return [old and key < end for key, old in zip(keys, ret)]

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
        new_list = syntax_node.NuclidesNode("new isotope list")
        for isotope, component in self._material_components.items():
            isotope._tree.value = isotope.mcnp_str()
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

    def __eq__(self, other):
        return hash(self) == hash(other)
