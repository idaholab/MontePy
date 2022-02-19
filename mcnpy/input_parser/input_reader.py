from mcnpy import mcnp_problem


def read_input(input_file):
    problem = mcnp_problem.MCNP_Problem(input_file)
    problem.parse_input()
    return problem
