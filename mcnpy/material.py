from .errors import *
from .isotope import Isotope
import itertools
from .material_component import MaterialComponent
from .mcnp_card import MCNP_Card
import re


class Material(MCNP_Card):
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
        super().__init__(comment)
        self.__material_components = {}
        words = input_card.words
        num = words[0].upper().strip("M")
        # material numbers
        try:
            num = int(num)
            assert num > 0
            self.__old_material_number = num
            self.__material_number = num
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
                fraction = float(fraction)
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
                    self.__is_atom_fraction = True
                else:
                    self.__is_atom_fraction = False
            else:
                # if switching fraction formatting
                if (fraction > 0 and not self.__is_atom_fraction) or (
                    fraction < 0 and self.__is_atom_fraction
                ):
                    raise MalformedInputError(
                        input_card,
                        "Material definitons cannot use atom and mass fraction at the same time",
                    )
            self.__material_components[isotope] = MaterialComponent(isotope, fraction)
        param_str = ""
        if has_parameters:
            for string in itertools.chain([isotope_str], words_iter):
                param_str += string + " "
            self.__parameter_string = param_str

    @property
    def old_material_number(self):
        """
        The material number that was used in the read file

        :rtype: int
        """
        return self.__old_material_number

    @property
    def material_number(self):
        """
        The number to use to identify the material by

        :rtype: int
        """
        return self.__material_number

    @material_number.setter
    def material_number(self, number):
        assert isinstance(number, int)
        assert number > 0
        self.__material_number = number

    @property
    def is_atom_fraction(self):
        """
        If true this constituent is in atom fraction, not weight fraction.
        """
        return self.__is_atom_fraction

    @property
    def material_components(self):
        """
        The internal dictionary containing all the components of this material.

        :rtype: dict
        """
        return self.__material_components

    @property
    def parameter_string(self):
        """
        String containing the key value pairs specified if any

        :rtype: str
        """
        if hasattribute(self, "__parameter_string"):
            return self.__parameter_string

    def format_for_mcnp_input(self):
        pass
