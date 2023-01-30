from mcnpy.data_inputs.data_input import DataInputAbstract
from mcnpy import mcnp_object
from mcnpy.errors import *
import mcnpy


class ThermalScatteringLaw(DataInputAbstract):
    """
    Class to hold MT Inputs

    This is designed to be called two ways.
    The first is with a read input file using input_card, comment
    The second is after a read with a material and a comment (using named inputs)

    :param input: the Input object representing this data input
    :type input: Input
    :param comments: The Comments that may proceed this
    :type comments: list
    :param material: the parent Material object that owns this
    :type material: Material
    """

    def __init__(self, input="", comment=None, material=None):
        self._old_material_number = None
        self._parent_material = None
        self._scattering_laws = []
        if input:
            super().__init__(input, comment)
            words = self.words
            self._old_material_number = self._input_number
            self._scattering_laws = self.words[1:]
        else:
            if comments:
                self._comment = comments
            if material:
                self._parent_material = material

    @staticmethod
    def _class_prefix():
        return "mt"

    @staticmethod
    def _has_number():
        return True

    @staticmethod
    def _has_classifier():
        return 0

    @property
    def old_number(self):
        """
        The material number from the file

        :rtype: int
        """
        return self._old_material_number

    @property
    def parent_material(self):
        """
        The Material object this is tied to.

        :rtype: Material
        """
        return self._parent_material

    @property
    def thermal_scattering_laws(self):
        """
        The thermal scattering laws to use for this material as strings.

        :rtype: list
        """
        return self._scattering_laws

    @thermal_scattering_laws.setter
    def thermal_scattering_laws(self, laws):
        if not isinstance(laws, list):
            raise TypeError("thermal_scattering_laws must be a list")
        for law in laws:
            if not isinstance(law, str):
                raise TypeError(
                    f"element {law} in thermal_scattering_laws must be a string"
                )
        self._mutated = True
        self._scattering_laws = laws

    def add_scattering_law(self, law):
        """
        Adds the requested scattering law to this material

        :param law: the thermal scattering law to add.
        :type law: str
        """
        self._scattering_laws.append(law)

    def validate(self):
        if len(self._scattering_laws) == 0:
            if self.parent_material:
                message = f"No thermal scattering laws given for MT{self.parent_material.number}."
            else:
                message = f"No thermal scattering laws given for thermal scattering {hex(id(self))}"
            raise IllegalState(message)

    def format_for_mcnp_input(self, mcnp_version):
        self.validate()
        ret = mcnp_object.MCNP_Object.format_for_mcnp_input(self, mcnp_version)
        mutated = self.mutated
        if not self.parent_material:
            raise MalformedInputError(
                self, "MT input is detached from a parent material"
            )
        if not mutated:
            mutated = self.parent_material.mutated
        if mutated:
            buff_list = [f"MT{self.parent_material.number}"]
            buff_list += self._scattering_laws
            ret += ThermalScatteringLaw.wrap_words_for_mcnp(
                buff_list, mcnp_version, True
            )
        else:
            ret = self._format_for_mcnp_unmutated(mcnp_version)
        return ret

    def update_pointers(self, data_inputs):
        """
        Updates pointer to the thermal scattering data

        :param data_inputs: a list of the data inputs in the problem
        :type data_inputs: list
        """
        found = False
        for input in data_inputs:
            if isinstance(input, mcnpy.data_inputs.material.Material):
                if input.number == self.old_number:
                    found = True

        if not found:
            raise MalformedInputError(
                self, "MT input is detached from a parent material"
            )

    def __str__(self):
        return f"THERMAL SCATTER: {self.thermal_scattering_laws}"

    def __repr__(self):
        return f"THERMAL SCATTER: material: {self.parent_material}, old_num: {self.old_number}, scatter: {self.thermal_scattering_laws}"
