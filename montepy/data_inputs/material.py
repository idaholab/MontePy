# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import copy
import collections as co
import itertools
import math

from montepy.data_inputs import data_input, thermal_scattering
from montepy.data_inputs.nuclide import Library, Nucleus, Nuclide
from montepy.data_inputs.element import Element
from montepy.data_inputs.material_component import MaterialComponent
from montepy.input_parser import syntax_node
from montepy.input_parser.material_parser import MaterialParser
from montepy import mcnp_object
from montepy.numbered_mcnp_object import Numbered_MCNP_Object
from montepy.errors import *
from montepy.utilities import *
from montepy.particle import LibraryType

import re
import warnings


MAX_PRINT_ELEMENTS = 5


def _number_validator(self, number):
    if number <= 0:
        raise ValueError("number must be > 0")
    if self._problem:
        self._problem.materials.check_number(number)


class _DefaultLibraries:

    __slots__ = "_libraries"

    def __init__(self):
        self._libraries = {}

    def __getitem__(self, key):
        key = self._validate_key(key)
        return self._libraries[key]

    def __setitem__(self, key, value):
        key = self._validate_key(key)
        if not isinstance(value, Library):
            raise TypeError("")
        self._libraries[key] = value

    def __delitem__(self, key):
        key = self._validate_key(key)
        del self._libraries[key]

    def __str__(self):
        return str(self._libraries)

    @staticmethod
    def _validate_key(key):
        if not isinstance(key, LibraryType):
            raise TypeError("")
        return key


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
        self._elements = set()
        self._nuclei = set()
        self._default_libs = _DefaultLibraries()
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
                self._elements.add(isotope.element)
                self._nuclei.add(isotope.nucleus)
                self._components.append((isotope, fraction))
            self._grab_defaults()

    def _grab_defaults(self):
        if "parameters" not in self._tree:
            return
        params = self._tree["parameters"]
        for param, value in params.nodes.items():
            try:
                lib_type = LibraryType(param.upper())
                self._default_libs[lib_type] = Library(value["data"].value)
            # skip extra parameters
            except ValueError:
                pass
        # TODO update in update_values for default_libraries

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

    @make_prop_pointer("_default_libs")
    def default_libraries(self):
        """
        TODO
        """
        pass

    def __getitem__(self, idx):
        """ """
        if not isinstance(idx, (int, slice)):
            raise TypeError(f"Not a valid index. {idx} given.")
        return self._components[idx]

    def __iter__(self):
        def gen_wrapper():
            for comp in self._components:
                yield (comp[0], comp[1].value)

        return gen_wrapper()

    def __setitem__(self, idx, newvalue):
        """ """
        if not isinstance(idx, (int, slice)):
            raise TypeError(f"Not a valid index. {idx} given.")
        self._check_valid_comp(newvalue)
        self._components[idx] = newvalue

    def __len__(self):
        return len(self._components)

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
        element = self[idx][0].element
        nucleus = self[idx][0].nucleus
        found_el = False
        found_nuc = False
        for i, (nuclide, _) in enumerate(self):
            if i == idx:
                continue
            if nuclide.element == element:
                found_el = True
            if nuclide.nucleus == nucleus:
                found_nuc = True
            if found_el and found_nuc:
                break
        if not found_el:
            self._elements.remove(element)
        if not found_nuc:
            self._nuclei.remove(nucleus)
        del self._components[idx]

    def __contains__(self, nuclide):
        # TODO support fancy stuff?
        if not isinstance(nuclide, (Nuclide, Nucleus, Element)):
            raise TypeError("")
        if isinstance(nuclide, (Nucleus, Nuclide)):
            # shortcut with hashes first
            if nuclide not in self._nuclei:
                return False
            # do it slowly with search
            if isinstance(nuclide, Nucleus):
                for self_nuc, _ in self:
                    if self_nuc == nuclide:
                        return True
                return False
            # fall through for only Nucleus
            return True
        if isinstance(nuclide, Element):
            element = nuclide
            return element in self._elements
        return False

    def append(self, obj):
        self._check_valid_comp(obj)
        self._elements.add(obj[0].element)
        self._nuclei.add(obj[0].nucleus)
        self._components.append(obj)

    def change_libraries(self, new_library):
        """ """
        if not isinstance(new_library, (Library, str)):
            raise TypeError(
                f"new_library must be a Library or str. {new_library} given."
            )
        for nuclide, _ in self:
            nuclide.library = new_library

    def add_nuclide(self, nuclide, fraction):
        """

        :param nuclide: The nuclide to add, which can be a string indentifier.
        :type nuclide: Nuclide, str, int
        """
        if not isinstance(nuclide, (Nuclide, str, int)):
            raise TypeError("")
        if not isinstance(fraction, (float, int)):
            raise TypeError("")
        if isinstance(nuclide, (str, int)):
            nuclide = Nuclide.get_from_fancy_name(nuclide)
        self.append((nuclide, fraction))

    def contains(self, nuclide, *args, threshold):
        nuclides = []
        for nuclide in [nuclide] + args:
            if not isinstance(nuclide, (str, int, Element, Nucleus, Nuclide)):
                raise TypeError("")  # foo
            if isinstance(nuclide, (str, int)):
                nuclide = montepy.Nuclide.get_from_fancy_name(nuclide)
            nuclides.append(nuclide)

        # fail fast
        for nuclide in nuclides:
            if isinstance(nuclide, (Nucleus, Element)):
                if nuclide not in self:
                    return False

        # do exhaustive search
        nuclides_search = {str(nuclide): False for nuclide in nuclides}

        for nuclide, fraction in self:
            if str(nuclide) in nuclides_search:
                if fraction >= threshold:
                    nuclides_search[str(nuclide)] = True
        return all(nuclide_search)

    def __prep_element_filter(self, filter_obj):
        if isinstance(filter_obj, "str"):
            filter_obj = Element.get_by_symbol(filter_obj).Z
        if isinstance(filter_obj, Element):
            filter_obj = filter_obj.Z
        wrapped_filter = self.__prep_filter(filter_obj, "Z")
        return wrapped_filter

    def __prep_filter(self, filter_obj, attr=None):
        if callable(filter_obj):
            return filter_obj

        elif isinstance(filter_obj, slice):

            def slicer(val):
                if attr is not None:
                    val = getattr(val, attr)
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
        """
        Finds all components that meet the given criteria.

        The criteria are additive, and a component must match all criteria.

        ... Examples

        :param fancy_name: TODO
        :type fancy_name: str
        :param element: the element to filter by, slices must be slices of integers.
        :type element: Element, str, int, slice
        :param A: the filter for the nuclide A number.
        :type A: int, slice
        :param meta_isomer: the metastable isomer filter.
        :type meta_isomer: int, slice
        :param library: the libraries to limit the search to.
        :type library: str, slice
        """
        # TODO type enforcement
        # TODO allow broad fancy name "U"
        filters = [
            self.__prep_filter(Nuclide.get_from_fancy_name(fancy_name)),
            self.__prep_element_filter(element),
            self.__prep_filter(A, "A"),
            self.__prep_filter(meta_isomer, "meta_state"),
            self.__prep_filter(library, "library"),
        ]
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
        new_list = syntax_node.IsotopesNode("new isotope list")
        for isotope, component in self._components:
            isotope._tree.value = isotope.mcnp_str()
            new_list.append(("_", isotope._tree, component))
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

        # TODO fix
        for component in self._components:
            ret += f"{component[0]} {component[1].value}\n"
        if self.thermal_scattering:
            ret += f"Thermal Scattering: {self.thermal_scattering}"

        return ret

    def __str__(self):
        elements = self.get_material_elements()
        print_el = []
        if len(elements) > MAX_PRINT_ELEMENTS:
            print_elements = elements[0:MAX_PRINT_ELEMENTS]
            print_elements.append("...")
            print_elements.append(elements[-1])
        else:
            print_elements = elements
        print_elements = [
            element.name if isinstance(element, Element) else element
            for element in print_elements
        ]
        return f"MATERIAL: {self.number}, {print_elements}"

    def get_material_elements(self):
        """

        :returns: a sorted list of elements by total fraction
        :rtype: list
        """
        element_frac = co.Counter()
        for nuclide, fraction in self:
            element_frac[nuclide.element] += fraction
        element_sort = sorted(element_frac.items(), key=lambda p: p[1], reverse=True)
        elements = [p[0] for p in element_sort]
        return elements

    def validate(self):
        if len(self._components) == 0:
            raise IllegalState(
                f"Material: {self.number} does not have any components defined."
            )

    def __eq__(self, other):
        if not isinstance(other, Material):
            return False
        if len(self) != len(other):
            return False
        my_comp = sorted(self, key=lambda c: c[0])
        other_comp = sorted(other, key=lambda c: c[0])
        for mine, yours in zip(my_comp, other_comp):
            if mine[0] != yours[0]:
                return False
            if not math.isclose(mine[1], yours[1]):
                return False
        return True
