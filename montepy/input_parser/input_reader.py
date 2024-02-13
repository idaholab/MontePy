# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy import mcnp_problem
from montepy.constants import DEFAULT_VERSION


def read_input(input_file, mcnp_version=DEFAULT_VERSION, replace=True):
    """
    Reads the specified MCNP Input file.

    The MCNP version must be a three component tuple e.g., (6, 2, 0) and (5, 1, 60).


    :param input_file: the path to the input file to read.
    :type input_file: str
    :param mcnp_version: The version of MCNP that the input is intended for.
    :type mcnp_version: tuple
    :returns: The MCNP_Problem instance representing this file.
    :param replace: replace all non-ASCII characters with a space (0x20)
    :type replace: bool
    :rtype: MCNP_Problem
    :raises UnsupportedFeature: If an input format is used that MontePy does not support.
    :raises MalformedInputError: If an input has a broken syntax.
    :raises NumberConflictError: If two objects use the same number in the input file.
    :raises BrokenObjectLinkError: If a reference is made to an object that is not in the input file.
    :raises UnknownElement: If an isotope is specified for an unknown element.
    """
    problem = mcnp_problem.MCNP_Problem(input_file)
    problem.mcnp_version = mcnp_version
    problem.parse_input(replace=replace)
    return problem
