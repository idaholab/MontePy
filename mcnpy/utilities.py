import re

"""
A package for helper universal utility functions
"""


def fortran_float(number_string):
    """
    Attempts to convert a FORTRAN formatted float string to a float.

    :param number_string: the string that will be converted to a float
    :type number_string: str
    :raises ValueError: If the string can not be parsed as a float.
    :return: the parsed float of the this string
    :rtype: float
    """
    try:
        return float(number_string)

    except ValueError as e:
        update_number = re.sub(r"(\d)([-+])", r"\1E\2", number_string)
        try:
            return float(update_number)
        except ValueError:
            raise ValueError from e
