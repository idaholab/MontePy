# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import argparse
import glob
import montepy
from pathlib import Path
import sys

"""
Module to make module executable from CLI.

.. note::
    `__name__ == "__main__"` is unnecessary because this file is not
    run on import.
"""


def define_args(args=None):
    """
    Sets and parses the command line arguments.

    :returns: the arguments that were parsed
    :rtype: argparse.NameSpace
    """
    parser = argparse.ArgumentParser(
        prog="montepy",
        description="Tool for editing and working with MCNP input files.",
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
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="Print the version number",
    )
    args = parser.parse_args(args)
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
        problem = montepy.MCNP_Problem(file)
        problem.parse_input(True)


def main():  # pragma: no cover
    """
    The main function
    """
    args = define_args()
    if args.check:
        check_inputs(args.check)
    if args.version:
        print(montepy.__version__)


if __name__ == "__main__":  # pragma: no cover
    main()
