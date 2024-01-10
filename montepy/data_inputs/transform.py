# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import copy
from montepy import mcnp_object
from montepy.data_inputs import data_input
from montepy.errors import *
from montepy.numbered_mcnp_object import Numbered_MCNP_Object
from montepy.utilities import *
import numpy as np
import re


def _enforce_number(self, val):
    if val <= 0:
        raise ValueError(f"Transform number must be > 0. {val} given.")


class Transform(data_input.DataInputAbstract, Numbered_MCNP_Object):
    """
    Input to represent a transform input (TR).

    :param input: The Input syntax object this will wrap and parse.
    :type input: Input
    """

    def __init__(self, input=None, pass_through=False):
        self._pass_through = pass_through
        self._number = self._generate_default_node(int, -1)
        self._old_number = self._generate_default_node(int, -1)
        self._displacement_vector = np.array([])
        self._rotation_matrix = np.array([])
        self._is_in_degrees = False
        self._is_main_to_aux = True
        super().__init__(input)
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
            values = []
            for j, word in enumerate(words):
                values.append(word.value)
                i += 1
                if j >= 2:
                    break
            self._displacement_vector = np.array(values)

            # parse rotation
            values = []
            for j, word in enumerate(words.nodes[i:]):
                values.append(word.value)
                i += 1
                if j >= 8:
                    break
            self._rotation_matrix = np.array(values)

            self._is_main_to_aux = True
            if len(values) == 9:
                try:
                    word = words[i]
                    word.is_negatable_identifier = True
                    if word.value != 1:
                        raise MalformedInputError(
                            input, f"{word} can't be parsed as 1 or -1"
                        )
                    # negative means not main_to_aux
                    self._is_main_to_aux = not word.is_negative
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

    @make_prop_pointer("_is_in_degrees", bool)
    def is_in_degrees(self):
        """
        The rotation matrix is in degrees and not in cosines

        :rtype: bool
        """
        pass

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
        self._rotation_matrix = matrix

    @make_prop_pointer("_is_main_to_aux", bool)
    def is_main_to_aux(self):
        """
        Whether or not the displacement vector points from the main origin to auxilary
        origin, or vice versa.

        :rtype: bool
        """
        return self._is_main_to_aux

    def __str__(self):
        return f"TRANSFORM: {self.number}"

    def __repr__(self):
        ret = f"TRANSFORM: {self.number}\n"
        ret += f"DISPLACE: {self.displacement_vector}\n"
        ret += f"ROTATE: {self.rotation_matrix}\n"
        ret += f"MAIN_TO_AUX: {self.is_main_to_aux}\n"
        return ret

    def _update_values(self):
        # update in degrees
        if self._classifier.modifier is None:
            self._classifier.modifier = self._generate_default_node(
                str, "", padding=None
            )
        if self.is_in_degrees:
            self._classifier.modifier.value = "*"
        else:
            self._classifier.modifier.value = ""
        # update displacement vector
        new_values = []
        list_iter = iter(self.data)
        length = len(self.data)
        for value, node in zip(self.displacement_vector, list_iter):
            node.value = value
            new_values.append(node)
        # update the rotation matrix
        # test if the rotation matrix has info, or was specified or main_to_aux is needed
        needs_rotation = (
            np.any(self.rotation_matrix)
            or len(self.data) >= 8
            or not self.is_main_to_aux
        )
        if needs_rotation:
            flat_pack = self.rotation_matrix
            i = -1
            for i, (value, node) in enumerate(zip(flat_pack, list_iter)):
                node.value = value
                new_values.append(node)
            if i < len(flat_pack) - 1:
                for value in flat_pack[i + 1 :]:
                    node = self._generate_default_node(float, value)
                    self.data.append(node)
                    new_values.append(node)
            # if main to aux specified or is needed
            if len(self.data) == 13 or not self.is_main_to_aux:
                if len(self.data) == 13:
                    node = self.data[-1]
                else:
                    node = self._generate_default_node(int, 1)
                    node.is_negatable_identifier = True
                    self.data.append(node)
                node.is_negative = not self.is_main_to_aux
                new_values.append(node)
        # Trigger shortcut recompression
        self.data.update_with_new_values(new_values)

    def validate(self):
        if self.displacement_vector is None or len(self.displacement_vector) != 3:
            raise IllegalState(
                f"Transform: {self.number} does not have a valid displacement Vector"
            )

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
