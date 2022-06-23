from mcnpy import mcnp_problem
from mcnpy.input_parser.constants import DEFAULT_VERSION


def read_input(input_file, mcnp_version=DEFAULT_VERSION):
    """
    Reads the specified MCNP Input file.

    The MCNP version must be a three component tuple e.g., (6, 2, 0) and (5, 1, 60).

    :param input_file: the path to the input file to read.
    :type input_file: str
    :param mcnp_version: The version of MCNP that the input is intended for.
    :type mcnp_version: tuple
    :returns: The MCNP_Problem instance representing this file.
    :rtype: MCNP_Problem
    """
    problem = mcnp_problem.MCNP_Problem(input_file)
    problem.mcnp_version = mcnp_version
    problem.parse_input()
    return problem
