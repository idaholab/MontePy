from mcnpy import mcnp_problem


def read_input(input_file):
    """
    Reads the specified MCNP Input file.

    :param input_file: the path to the input file to read.
    :type input_file: str
    :returns: The MCNP_Problem instance representing this file.
    :rtype: MCNP_Problem
    """
    problem = mcnp_problem.MCNP_Problem(input_file)
    problem.parse_input()
    return problem
