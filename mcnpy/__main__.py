import argparse
import glob
import mcnpy
from pathlib import Path

"""
Module to make module executable from CLI.

.. note::
    `__name__ == "__main__"` is unnecessary because this file is not
    run on import.
"""


def define_args():
    """
    Sets and parses the command line arguments.

    :returns: the arguments that were parsed
    :rtype: argparse.NameSpace
    """
    parser = argparse.ArgumentParser(
        prog="mcnpy", description="Tool for editing and working with MCNP input files."
    )
    parser.add_argument(
        "-c",
        "--check",
        action="store",
        nargs="*",
        type=str,
        help="Check the given input file(s) for errors. Accepts globs, and multiple arguments.",
        metavar="input_file",
    )
    args = parser.parse_args()
    return args


def check_inputs(files):
    """
    Checks input files for syntax errors.

    :param files: a list of paths to check and show warnings for errors.
    :type files: list
    """
    for file in files:
        if not Path(file).is_file():
            raise FileNotFoundError(f"File: {file} not found.")
    for file in files:
        print(f"\n********** Checking: {file} *********\n")
        problem = mcnpy.mcnp_problem.MCNP_Problem(file)
        problem.parse_input(True)


def main():
    """
    The main function
    """
    args = define_args()
    if "check" in args:
        check_inputs(args.check)


main()
