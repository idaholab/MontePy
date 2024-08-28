# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.data_inputs.data_input import DataInputAbstract
from montepy.input_parser.thermal_parser import ThermalParser
from montepy import mcnp_object
from montepy.errors import *
from montepy.utilities import *
import montepy


class ThermalScatteringLaw(DataInputAbstract):
    """
    Class to hold MT Inputs

    This is designed to be called two ways.
    The first is with a read input file using input_card, comment
    The second is after a read with a material and a comment (using named inputs)

    :param input: the Input object representing this data input
    :type input: Input
    :param material: the parent Material object that owns this
    :type material: Material
    """

    _parser = ThermalParser()

    def __init__(self, input="", material=None):
        self._old_number = self._generate_default_node(int, -1)
        self._parent_material = None
        self._scattering_laws = []
        super().__init__(input)
        if input:
            self._old_number = self._input_number
            self._scattering_laws = self._tree["data"].nodes
        else:
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

    @make_prop_val_node("_old_number")
    def old_number(self):
        """
        The material number from the file

        :rtype: int
        """
        pass

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
        ret = []
        for law in self._scattering_laws:
            ret.append(law.value)
        return ret

    @thermal_scattering_laws.setter
    def thermal_scattering_laws(self, laws):
        if not isinstance(laws, list):
            raise TypeError("thermal_scattering_laws must be a list")
        for law in laws:
            if not isinstance(law, str):
                raise TypeError(
                    f"element {law} in thermal_scattering_laws must be a string"
                )
        self._scattering_laws.clear()
        for law in laws:
            self._scattering_laws.append(self._generate_default_node(str, law))

    def add_scattering_law(self, law):
        """
        Adds the requested scattering law to this material

        :param law: the thermal scattering law to add.
        :type law: str
        """
        self._scattering_laws.append(self._generate_default_node(str, law))

    def validate(self):
        if len(self._scattering_laws) == 0:
            if self.parent_material:
                message = f"No thermal scattering laws given for MT{self.parent_material.number}."
            else:
                message = f"No thermal scattering laws given for thermal scattering {hex(id(self))}"
            raise IllegalState(message)

    def _update_values(self):
        if self.parent_material:
            self._tree["classifier"].number.value = self.parent_material.number
        else:
            raise MalformedInputError(
                self._input,
                f"MT{self.old_number} input is detached from a parent material",
            )

    def update_pointers(self, data_inputs):
        """
        Updates pointer to the thermal scattering data

        :param data_inputs: a list of the data inputs in the problem
        :type data_inputs: list
        :returns: True iff this input should be removed from ``problem.data_inputs``
        :rtype: bool
        """
        # use caching first
        if self._problem:
            try:
                mat = self._problem.materials[self.old_number]
            except KeyError:
                raise MalformedInputError(
                    self._input, "MT input is detached from a parent material"
                )
        # brute force it
        found = False
        for data_input in data_inputs:
            if isinstance(data_input, montepy.data_inputs.material.Material):
                if data_input.number == self.old_number:
                    mat = data_input
                    found = True
                    break
        # actually update things
        if not found:
            raise MalformedInputError(
                self._input, "MT input is detached from a parent material"
            )

        if mat.thermal_scattering:
            raise MalformedInputError(
                self,
                f"Multiple MT inputs were specified for this material: {self.old_number}.",
            )
        mat.thermal_scattering = self
        self._parent_material = mat
        return True

    def __str__(self):
        return f"THERMAL SCATTER: {self.thermal_scattering_laws}"

    def __repr__(self):
        return f"THERMAL SCATTER: material: {self.parent_material}, old_num: {self.old_number}, scatter: {self.thermal_scattering_laws}"
