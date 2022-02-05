from mcnpy import mcnp_card
from mcnpy.data_cards import data_card
from mcnpy.errors import *
from mcnpy.utilities import *
import numpy as np
import re


class Transform(data_card.DataCard):
    """
    Card to represent a transform card (TR)
    """

    def __init__(self, input_card=None, comment=None):
        if input_card is None:
            self.__transform_number = -1
            self.__old_transform_number = -1
            self.__displacement_vector = np.array([])
            self.__rotation_matrix = np.array([])
            self.__is_in_degrees = False
            self.__is_main_to_aux = True
        else:
            super().__init__(input_card, comment)
            words = self.words
            i = 0
            assert re.match("\*?tr\d+", words[i].lower())
            assert len(words) >= 3
            try:
                if "*" in words[i]:
                    self.__is_in_degrees = True
                else:
                    self.__is_in_degrees = False
                num = words[i].lower().strip("*tr")
                self.__transform_number = int(num)
                self.__old_transform_number = self.__transform_number
                i += 1

            except ValueError:
                raise MalformedInputError(
                    input_card, f"{words[0]} can't be parsed as transform number"
                )
            # parse displacement
            try:
                values = []
                for j, word in enumerate(words[i:]):
                    values.append(fortran_float(word))
                    i += 1
                    if j >= 2:
                        break
                self.__displacement_vector = np.array(values)

            except ValueError:
                raise MalformedInputError(
                    input_card, f"{word} can't be parsed as a displacement vector component"
                )

            # parse rotation
            try:
                values = []
                for j, word in enumerate(words[i:]):
                    values.append(fortran_float(word))
                    i += 1
                    if j >= 8:
                        break
                self.__rotation_matrix = np.array(values)
            except ValueError:
                raise MalformedInputError(
                    input_card, f"{word} can't be parsed as a rotation matrix component"
                )

            self.__is_main_to_aux = True
            if len(values) == 9:
                try:
                    word = words[i]
                    # if 1 it's the default value
                    if word == "1":
                        pass
                    elif word == "-1":
                        self.__is_main_to_aux = False
                    else:
                        raise MalformedInputError(
                            input_card, f"{word} can't be parsed as 1 or -1"
                        )

                # if no more words remain don't worry
                except IndexError:
                    pass

    @property
    def is_in_degrees(self):
        """
        The rotation matrix is in degrees and not in cosines

        :rtype: bool
        """
        return self.__is_in_degrees

    @is_in_degrees.setter
    def is_in_degrees(self, in_deg):
        """
        Does not currently correct the rotation matrix for you
        """
        assert isinstance(in_deg, bool)
        self.__is_in_degrees = in_deg

    @property
    def transform_number(self):
        """
        The transform number for this transform

        :rtype: int
        """
        return self.__transform_number

    @transform_number.setter
    def transform_number(self, num):
        assert isinstance(num, int)
        self.__transform_number = num

    @property
    def old_transform_number(self):
        """
        The transform number used in the original file
        """
        return self.__old_transform_number

    @property
    def displacement_vector(self):
        """
        The transform displacement vector

        :rtype: numpy.array
        """
        return self.__displacement_vector

    @displacement_vector.setter
    def displacement_vector(self, vector):
        assert isinstance(vector, np.ndarray)
        assert len(vector) == 3
        self.__displacement_vector = vector

    @property
    def rotation_matrix(self):
        """
        The rotation matrix

        :rtype:np.array
        """
        return self.__rotation_matrix

    @rotation_matrix.setter
    def rotation_matrix(self, matrix):
        assert isinstance(matrix, np.ndarray)
        assert len(matrix) >= 5
        self.__rotation_matrix = matrix

    @property
    def is_main_to_aux(self):
        """
        Whether or not the displacement vector points from the main origin to auxilary
        origin, or vice versa.

        :rtype: bool
        """
        return self.__is_main_to_aux

    @is_main_to_aux.setter
    def is_main_to_aux(self, flag):
        assert isinstance(flag, bool)
        self.__is_main_to_aux = flag

    def __str__(self):
        ret = f"TRANSFORM: {self.transform_number}\n"
        ret += f"DISPLACE: {self.displacement_vector}\n"
        ret += f"ROTATE: {self.rotation_matrix}\n"
        ret += f"MAIN_TO_AUX: {self.is_main_to_aux}\n"
        return ret

    def format_for_mcnp_input(self, mcnp_version):
        ret = mcnp_card.MCNP_Card.format_for_mcnp_input(self, mcnp_version)
        buff_list = []
        if self.is_in_degrees:
            buff_list.append(f"*TR{self.transform_number}")
        else:
            buff_list.append(f"TR{self.transform_number}")
        for value in self.displacement_vector:
            buff_list.append(f"{value}")

        ret += Transform.wrap_words_for_mcnp(buff_list, mcnp_version, True)
        buff_list = []
        i = 0
        for i, value in enumerate(self.rotation_matrix):
            buff_list.append(f"{value}")
            if (i + 1) % 3 == 0:
                ret += Transform.wrap_words_for_mcnp(buff_list, mcnp_version, False)
                buff_list = []
        if i == 8 and not self.is_main_to_aux:
            ret += Transform.wrap_string_for_mcnp("-1", mcnp_version, False)
        return ret

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
