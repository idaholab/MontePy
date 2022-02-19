from mcnpy.data_cards import data_card, thermal_scattering
from mcnpy.data_cards.isotope import Isotope
from mcnpy.data_cards.material_component import MaterialComponent
from mcnpy import mcnp_card
from mcnpy.errors import *
from mcnpy.utilities import *
import itertools
import re


class Material(data_card.DataCard):
    """
    A class to represent an MCNP material.
    """

    def __init__(self, input_card, comment):
        """
        :param input_card: the input card that contains the data
        :type input_card: Card
        :param comment: The comment card that preceded this card if any.
        :type comment: Comment
        """
        super().__init__(input_card, comment)
        self._material_components = {}
        self._thermal_scattering = None
        words = self.words
        num = words[0].upper().strip("M")
        # material numbers
        try:
            num = int(num)
            assert num > 0
            self._old_material_number = num
            self._material_number = num
        except (ValueError, AssertionError) as e:
            raise MalformedInputError(
                input_card, f"{words[0]} could not be parsed as a material number"
            )
        words_iter = iter(words[1:])
        set_atom_frac = False
        has_parameters = False
        for isotope_str in words_iter:
            try:
                isotope = Isotope(isotope_str)
                fraction = next(words_iter)
                fraction = fortran_float(fraction)
            except MalformedInputError:
                has_parameters = True
                break
            except ValueError:
                raise MalformedInputError(
                    input_card, f"{fraction} could not be parsed as a material fraction"
                )
            if not set_atom_frac:
                set_atom_frac = True
                if fraction > 0:
                    self._is_atom_fraction = True
                else:
                    self._is_atom_fraction = False
            else:
                # if switching fraction formatting
                if (fraction > 0 and not self._is_atom_fraction) or (
                    fraction < 0 and self._is_atom_fraction
                ):
                    raise MalformedInputError(
                        input_card,
                        "Material definitons cannot use atom and mass fraction at the same time",
                    )
            self._material_components[isotope] = MaterialComponent(
                isotope, abs(fraction)
            )
        param_str = ""
        if has_parameters:
            for string in itertools.chain([isotope_str], words_iter):
                param_str += string + " "
            self._parameter_string = param_str

    @property
    def old_material_number(self):
        """
        The material number that was used in the read file

        :rtype: int
        """
        return self._old_material_number

    @property
    def material_number(self):
        """
        The number to use to identify the material by

        :rtype: int
        """
        return self._material_number

    @material_number.setter
    def material_number(self, number):
        assert isinstance(number, int)
        assert number > 0
        self._material_number = number

    @property
    def is_atom_fraction(self):
        """
        If true this constituent is in atom fraction, not weight fraction.
        """
        return self._is_atom_fraction

    @property
    def material_components(self):
        """
        The internal dictionary containing all the components of this material.

        :rtype: dict
        """
        return self._material_components

    @property
    def parameter_string(self):
        """
        String containing the key value pairs specified if any

        :rtype: str
        """
        return self._parameter_string

    @property
    def thermal_scattering(self):
        """
        The thermal scattering law for this material
        """
        return self._thermal_scattering

    def add_thermal_scattering(self, law):
        """
        Adds thermal scattering law to the material

        :param law: the law that is mcnp formatted
        :type law: str
        """
        self._thermal_scattering = thermal_scattering.ThermalScatteringLaw(
            material=self
        )
        self._thermal_scattering.add_scattering_law(law)

    def update_pointers(self, data_cards):
        """
        Updates pointer to the thermal scattering data

        :param data_cards: a list of the data cards in the problem
        :type data_cards: list
        """
        for card in data_cards:
            if isinstance(card, thermal_scattering.ThermalScatteringLaw):
                if card.old_material_number == self.material_number:
                    self._thermal_scattering = card
                    card._ThermalScatteringLaw__parent_material = self

    def __str__(self):
        ret = f"MATERIAL: {self.material_number} fractions: "
        if self.is_atom_fraction:
            ret += "atom\n"
        else:
            ret += "mass\n"

        for component in self.material_components:
            ret += str(self.material_components[component]) + "\n"

        return ret

    def __repr__(self):
        return self.__str__()

    def __lt__(self, other):
        return self.material_number < other.material_number

    def format_for_mcnp_input(self, mcnp_version):
        ret = mcnp_card.MCNP_Card.format_for_mcnp_input(self, mcnp_version)
        sorted_isotopes = sorted(list(self.material_components.keys()))
        first_component = self.material_components[sorted_isotopes[0]]

        ret.append(
            f"m{self.material_number:<9}{str(first_component.isotope):>8}{first_component.fraction:>12.4g}"
        )
        for isotope in sorted_isotopes[1:]:  # skips the first
            component = self.material_components[isotope]
            ret.append(f"{str(component.isotope):>19}{component.fraction:>12.4g}")
        return ret
