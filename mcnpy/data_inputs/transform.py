import copy
from mcnpy import mcnp_object
from mcnpy.data_inputs import data_input
from mcnpy.errors import *
from mcnpy.numbered_mcnp_object import Numbered_MCNP_Object
from mcnpy.utilities import *
import numpy as np
import re


def _enforce_number(self, val):
    if val <= 0:
        raise ValueError(f"Transform number must be > 0. {val} given.")


class Transform(data_input.DataInputAbstract, Numbered_MCNP_Object):
    """
    Card to represent a transform card (TR)

    :param input: The Input syntax object this will wrap and parse.
    :type input: Input
    :param comments: The Comments that proceeded this card or were inside of this if any
    :type Comments: list
    """

    def __init__(self, input=None, comments=None, pass_through=False):
        self._pass_through = pass_through
        self._number = self._generate_default_node(int, -1)
        self._old_number = self._generate_default_node(int, -1)
        self._displacement_vector = np.array([])
        self._rotation_matrix = np.array([])
        self._is_in_degrees = False
        self._is_main_to_aux = True
        super().__init__(input, comments)
        if input:
            words = self._tree["data"]
            i = 0
            if len(words) < 3:
                raise MalformedInputError(input, f"Not enough entries were provided")
            modifier = self._classifier.modifier
            if modifier and "*" in modifier.value:
                self._is_in_degrees = True
            else:
                self._is_in_degrees = False
            self._number = self._input_number
            self._old_number = copy.deepcopy(self._number)

            # parse displacement
            try:
                values = []
                for j, word in enumerate(words):
                    values.append(word.value)
                    i += 1
                    if j >= 2:
                        break
                self._displacement_vector = np.array(values)

            except ValueError:
                raise MalformedInputError(
                    input,
                    f"{word} can't be parsed as a displacement vector component",
                )

            # parse rotation
            try:
                values = []
                for j, word in enumerate(words.nodes[i:]):
                    values.append(word.value)
                    i += 1
                    if j >= 8:
                        break
                self._rotation_matrix = np.array(values)
            except ValueError:
                raise MalformedInputError(
                    input, f"{word} can't be parsed as a rotation matrix component"
                )

            self._is_main_to_aux = True
            if len(values) == 9:
                try:
                    word = words[i]
                    # if 1 it's the default value
                    if int(word.value) == 1:
                        pass
                    elif int(word.value) == -1:
                        self._is_main_to_aux = False
                    else:
                        raise MalformedInputError(
                            input, f"{word} can't be parsed as 1 or -1"
                        )
                # if no more words remain don't worry
                except IndexError:
                    pass

    @staticmethod
    def _class_prefix():
        return "tr"

    @staticmethod
    def _has_number():
        return True

    @staticmethod
    def _has_classifier():
        return 0

    @property
    def hidden_transform(self):
        """
        Whether or not this transform is "hidden" i.e., has no number.

        If True this transform was created from a fill card, and has no number.

        :rtype: bool
        """
        return self._pass_through

    @property
    def is_in_degrees(self):
        """
        The rotation matrix is in degrees and not in cosines

        :rtype: bool
        """
        return self._is_in_degrees

    @is_in_degrees.setter
    def is_in_degrees(self, in_deg):
        """
        Does not currently correct the rotation matrix for you
        """
        if not isinstance(in_deg, bool):
            raise TypeError("in_deg must be a bool")
        self._mutated = True
        self._is_in_degrees = in_deg

    @make_prop_val_node("_number", (int, float), int, _enforce_number)
    def number(self):
        """
        The transform number for this transform

        :rtype: int

        """
        pass

    @make_prop_val_node("_old_number")
    def old_number(self):
        """
        The transform number used in the original file

        :rtype: int
        """
        pass

    @property
    def displacement_vector(self):
        """
        The transform displacement vector

        :rtype: numpy.array
        """
        return self._displacement_vector

    @displacement_vector.setter
    def displacement_vector(self, vector):
        if not isinstance(vector, np.ndarray):
            raise TypeError("displacement_vector must be a numpy array")
        if len(vector) != 3:
            raise ValueError("displacement_vector must have three components")
        self._mutated = True
        self._displacement_vector = vector

    @property
    def rotation_matrix(self):
        """
        The rotation matrix

        :rtype: np.array
        """
        return self._rotation_matrix

    @rotation_matrix.setter
    def rotation_matrix(self, matrix):
        if not isinstance(matrix, np.ndarray):
            raise TypeError("rotation_matrix must be a numpy array")
        if len(matrix) < 5 or len(matrix) > 9:
            raise ValueError("rotation_matrix must have between 5 and 9 components.")
        self._mutated = True
        self._rotation_matrix = matrix

    @property
    def is_main_to_aux(self):
        """
        Whether or not the displacement vector points from the main origin to auxilary
        origin, or vice versa.

        :rtype: bool
        """
        return self._is_main_to_aux

    @is_main_to_aux.setter
    def is_main_to_aux(self, flag):
        if not isinstance(flag, bool):
            raise TypeError("is_main_to_aux must be a bool")
        self._mutated = True
        self._is_main_to_aux = flag

    def __str__(self):
        return f"TRANSFORM: {self.number}"

    def __repr__(self):
        ret = f"TRANSFORM: {self.number}\n"
        ret += f"DISPLACE: {self.displacement_vector}\n"
        ret += f"ROTATE: {self.rotation_matrix}\n"
        ret += f"MAIN_TO_AUX: {self.is_main_to_aux}\n"
        return ret

    def _generate_inputs(self, mcnp_version, first_line=True, is_pass_through=False):
        """
        Generates appropriately formatted input for this transform.

        :param mcnp_version: see format_for_mcnp_input
        :type mcnp_version: tuple
        :param first_line: If true this is the first line of input
        :type first_line: bool
        :param is_pass_through: If True the transform number will be supressed
        :type is_pass_through: bool
        :returns: a tuple of (bool: true if this needs an *, list of str of the input)
        :rtype: tuple
        """
        # TODO
        ret = []
        in_degs = False
        buff_list = []
        if not is_pass_through:
            if self.is_in_degrees:
                buff_list.append(f"*TR{self.number}")
            else:
                buff_list.append(f"TR{self.number}")
        else:
            in_degs = self.is_in_degrees
        for value in self.displacement_vector:
            buff_list.append(f"{value}")

        ret += Transform.wrap_words_for_mcnp(buff_list, mcnp_version, first_line)
        buff_list = []
        i = 0
        for i, value in enumerate(self.rotation_matrix):
            buff_list.append(f"{value}")
            if (i + 1) % 3 == 0:
                ret += Transform.wrap_words_for_mcnp(buff_list, mcnp_version, False)
                buff_list = []
        if i == 8 and not self.is_main_to_aux:
            ret += Transform.wrap_string_for_mcnp("-1", mcnp_version, False)
        return (in_degs, ret)

    def validate(self):
        if self.displacement_vector is None or len(self.displacement_vector) != 3:
            raise IllegalState(
                f"Transform: {self.number} does not have a valid displacement Vector"
            )

    def _update_values(self):
        # TODO
        pass

    def equivalent(self, other, tolerance):
        """Determines if this is effectively equivalent to another transformation

        :param other: The transform to compare self again.
        :type other: Transform
        :param tolerance: the allowable difference in any attribute to still be considered equivalent.
        :type tolerance: float

        :returns: True iff all transform elements in both are within the tolerance of each other.
        :rtype: bool
        """

        if self.is_in_degrees != other.is_in_degrees:
            return False

        if self.is_main_to_aux != other.is_main_to_aux:
            return False

        for i, component in enumerate(self.displacement_vector):
            if abs(component - other.displacement_vector[i]) >= tolerance:
                return False

        if len(self.rotation_matrix) > 0:
            if len(other.rotation_matrix) == 0:
                return False
            for i, component in enumerate(self.rotation_matrix):
                if abs(component - other.rotation_matrix[i]) >= tolerance:
                    return False
        return True
